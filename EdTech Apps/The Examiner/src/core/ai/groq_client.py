# Remove requests import if no longer needed elsewhere in this file
# import requests
import logging
import json
from typing import Dict, Optional, Any
import re # Import regex for parsing

# Import the official Groq SDK
from groq import Groq, GroqError # Import GroqError for specific exception handling

# Import the function to get the key
from src.config.secrets import get_groq_api_key

logger = logging.getLogger(__name__)

# Constants
# GROQ_API_URL is not needed when using the SDK client
TARGET_MODEL = "deepseek-r1-distill-llama-70b" # As requested

class GroqClient:
    def __init__(self):
        try:
            self.api_key = get_groq_api_key()
            if not self.api_key:
                logger.error("Groq API Key not found or configured correctly!")
                # Raise error immediately if key is missing
                raise ValueError("Groq API Key is missing.")
            # Instantiate the Groq client using the SDK
            self.client = Groq(api_key=self.api_key)
            logger.info("Groq SDK client initialized.")
        except Exception as e:
            logger.error(f"Failed to initialize GroqClient: {e}", exc_info=True)
            # Propagate the error to signal initialization failure
            raise ValueError(f"GroqClient initialization failed: {e}") from e

    def _parse_groq_text_response(self, response_text: str) -> Dict[str, Any]:
        """Parses the expected plain text output (Grade, Rationale, Study Topics)."""
        parsed_data = {
            "grade": "N/A (Parse Failed)",
            "rationale": "N/A (Parse Failed)",
            "study_topics": {"raw": response_text} # Default to raw text on failure
        }
        if not response_text:
            return parsed_data

        try:
            # Use regex similar to marker.py but adapt for potential variations
            # Simple line-based extraction
            grade_match = re.search(r"^\s*Grade:\s*(.*)$", response_text, re.MULTILINE | re.IGNORECASE)
            rationale_match = re.search(r"^\s*Rationale:\s*(.*?)(\n\s*(Study Topics:|Grade:)|$)", response_text, re.DOTALL | re.MULTILINE | re.IGNORECASE)
            study_topics_match = re.search(r"^\s*Study Topics:\s*(.*?)(\n\s*(Grade:|Rationale:)|$)", response_text, re.DOTALL | re.MULTILINE | re.IGNORECASE)

            if grade_match:
                parsed_data["grade"] = grade_match.group(1).strip()
                logger.debug("Groq Response Parse: Found Grade.")
            else:
                 logger.warning("Groq Response Parse: Grade not found.")

            if rationale_match:
                parsed_data["rationale"] = rationale_match.group(1).strip()
                logger.debug("Groq Response Parse: Found Rationale.")
            else:
                 logger.warning("Groq Response Parse: Rationale not found.")


            if study_topics_match:
                study_topics_text = study_topics_match.group(1).strip()
                logger.debug("Groq Response Parse: Found Study Topics text.")
                # Attempt basic structuring (can be enhanced)
                structured_topics = {"raw": study_topics_text}
                # Example: Split by lines if applicable
                lines = [line.strip() for line in study_topics_text.split('\n') if line.strip()]
                if lines:
                    structured_topics["lines"] = lines
                # Add more sophisticated parsing here if needed based on observed output
                parsed_data["study_topics"] = structured_topics
            else:
                logger.warning("Groq Response Parse: Study Topics not found.")
                # Keep the default raw response text if topics section isn't found
                parsed_data["study_topics"] = {"raw": "Study topics section not explicitly found in response."}


        except Exception as parse_err:
            logger.error(f"Error parsing Groq text response: {parse_err}", exc_info=True)
            # Return dictionary indicating parse failure but include raw text
            return {
                "error": "Failed to parse Groq text response",
                "grade": "N/A (Parse Error)",
                "rationale": "N/A (Parse Error)",
                "study_topics": {"raw": response_text}
            }

        return parsed_data

    def generate_report_from_prompt(self, prompt_string: str) -> Optional[Dict[str, Any]]:
        """Calls the Groq API using the SDK (expecting text, parsing after)."""
        if not prompt_string: # Basic checks
             return {"error": "Prompt string is empty"}
        if not self.client:
             return {"error": "Groq client not initialized"}

        # Use a simple system prompt as we expect text output based on user prompt
        system_prompt = "You are an AI assistant. Process the user's request carefully."
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt_string}
        ]

        try:
            logger.info(f"Sending request to Groq API via SDK. Model: {TARGET_MODEL}. Expecting TEXT response.")
            content_snippet = prompt_string[:100] + "..." + prompt_string[-100:] if len(prompt_string) > 200 else prompt_string
            logger.debug(f"Groq User Prompt Content Snippet: {content_snippet}")

            # --- SDK call WITHOUT response_format ---
            chat_completion = self.client.chat.completions.create(
                messages=messages,
                model=TARGET_MODEL,
                temperature=0.2,
                max_tokens=2048,
                # NO response_format parameter
            )
            # --- End SDK Call ---

            logger.info("Received successful response from Groq API via SDK.")
            # logger.info(f"Full Groq chat_completion object (type: {type(chat_completion)}): {chat_completion}") # Keep if needed

            ai_content_str = None
            if chat_completion.choices and chat_completion.choices[0].message:
                 ai_content_str = chat_completion.choices[0].message.content
            # logger.info(f"Extracted ai_content_str (type: {type(ai_content_str)}): '{ai_content_str}'") # Keep if needed


            if ai_content_str:
                logger.debug("Attempting to parse received Groq text response...")
                # --- Call the new parsing function ---
                parsed_report = self._parse_groq_text_response(ai_content_str)
                if "error" in parsed_report: # Check if parsing itself indicated an error
                     logger.error(f"Parsing Groq text response failed: {parsed_report.get('error')}")
                     # Return the error dict, which includes raw content
                     return parsed_report
                else:
                     logger.info("Successfully parsed Groq text response into structured dict.")
                     return parsed_report # Return the dictionary we constructed
                # ------------------------------------
            else:
                logger.error("No content found in Groq API response choice.")
                return {"error": "No content in Groq response"}

        except GroqError as e:
            status_code = getattr(e, 'status_code', None)
            body = getattr(e, 'body', None)
            logger.error(f"Groq API Error: Status={status_code}, Body={body}", exc_info=True)
            return {"error": f"Groq API Error (Status={status_code}): {e}"}
        except Exception as e:
            logger.error(f"Error during Groq API call via SDK: {e}", exc_info=True)
            return {"error": f"General error during SDK call: {e}"}
