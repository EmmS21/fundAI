import logging
import os
import re # For parsing
import sys
from typing import Dict, Optional, Tuple, List, Any
from pathlib import Path # For handling home directory
from llama_cpp import Llama
import pprint # Ensure pprint is imported if not already

# --- Import the examples ---
# Make sure prompt_examples.py is in the same directory (core/ai)
# If it's elsewhere, adjust the import path accordingly.
try:
    from .prompt_examples import FEW_SHOT_EXAMPLES
except ImportError:
    logger.error("Could not import FEW_SHOT_EXAMPLES from .prompt_examples. Ensure the file exists.")
    FEW_SHOT_EXAMPLES = [] # Default to empty list if import fails

logger = logging.getLogger(__name__)

# --- Configuration ---
MODEL_FILENAME = "DeepSeek-R1-Distill-Qwen-1.5B-Q4_K_M.gguf"
BASE_LLAMA_DIR = Path.home() / "Documents" / "models" / "llama" # Base dir
CONTEXT_SIZE = 2048
MAX_TOKENS = 1024 # Max tokens for generation
GPU_LAYERS = -1 # Offload all possible layers to GPU (-1). Set to 0 to disable GPU.
REPEAT_PENALTY = 1.1 # Keep penalty low/moderate
# --- End Configuration ---

def find_model_path() -> Optional[str]:
    """
    Looks for the model file in the assumed fixed directory.

    Returns:
        The full path to the model if found, otherwise None.
    """
    model_path = BASE_LLAMA_DIR / MODEL_FILENAME
    logger.debug(f"Checking for model at fixed path: {model_path}")

    if not BASE_LLAMA_DIR.is_dir():
         logger.error(f"Assumed model directory does not exist: {BASE_LLAMA_DIR}")
         return None

    if model_path.is_file():
        logger.info(f"Found model at: {model_path}")
        return str(model_path)
    else:
        logger.error(f"Model '{MODEL_FILENAME}' not found in directory: {BASE_LLAMA_DIR}")
        return None

def parse_ai_response(response_text: str) -> Dict[str, Optional[str]]:
    """
    Parses the AI response text flexibly by splitting and identifying markers.

    Args:
        response_text: The raw text output from the AI model.

    Returns:
        A dictionary where keys are the expected section names and values
        are the corresponding text content (or None if not found).
    """
    if not response_text:
        logger.warning("Attempted to parse an empty response text.")
        return {key: None for key in expected_headings}

    response_text = "\n" + response_text.strip() + "\n" # Add padding for regex
    logger.debug(f"Starting flexible parsing v3 for response:\n{response_text[:500]}...")

    expected_headings = [
        "Mark Awarded", "Feedback", "Understanding Gap", "Study Topics",
        "Self-Reflection Questions", "Correct Answer", "Understanding Rating"
    ]
    parsed_data = {key: None for key in expected_headings}

    markers = {
        "Mark Awarded": {"patterns": [r"##\s*Mark Awarded", r"\*\*Mark Awarded:\*\*", r"\bMark Awarded:", r"\bMark:"], "regex": r"(\d+\s*/\s*\d+)"},
        "Feedback": {"patterns": [r"##\s*Feedback", r"\*\*Feedback:\*\*", r"\bFeedback:"]},
        "Understanding Gap": {"patterns": [r"##\s*Understanding Gap", r"\*\*Understanding Gap:\*\*", r"\bUnderstanding Gap:"]},
        "Study Topics": {"patterns": [r"##\s*Study Topics", r"\*\*Study Topics:\*\*", r"\bStudy Topics:", r"\bReview:"]},
        "Self-Reflection Questions": {"patterns": [r"##\s*Self-Reflection Questions", r"\*\*Self-Reflection Questions:\*\*", r"\bSelf-Reflection Questions:", r"\bReflection Questions:"]},
        "Correct Answer": {"patterns": [r"##\s*Correct Answer", r"\*\*Correct Answer:\*\*", r"\bCorrect Answer:"]},
        "Understanding Rating": {"patterns": [r"##\s*Understanding Rating", r"\*\*Understanding Rating:\*\*", r"\bUnderstanding Rating:", r"\bRating:"], "regex": r"\b(Excellent|Good|Fair|Poor|Very Poor)\b", "flags": re.IGNORECASE}
    }

    # 1. Direct Regex Extraction (for specific items first)
    for heading, config in markers.items():
        if "regex" in config:
            flags = config.get("flags", 0)
            # Search the entire text for these specific patterns
            match = re.search(config["regex"], response_text, flags=flags)
            if match:
                extracted_value = match.group(1) if match.groups() else match.group(0)
                parsed_data[heading] = extracted_value.strip()
                logger.debug(f"Direct Regex extracted '{heading}': {parsed_data[heading]}")

    # 2. Split by Section Markers
    # Combine all non-regex patterns into one OR group for splitting
    all_patterns = []
    for heading, config in markers.items():
        all_patterns.extend(config.get("patterns", []))

    # Create a split regex that CAPTURES any of the patterns as delimiters
    # Ensure patterns are treated as raw strings if they contain special chars not intended for regex
    # We capture the delimiter itself `(` + `|`.join(...) + `)`
    # Include optional leading newline and match until newline
    split_regex = r"(\n?(?:" + "|".join(all_patterns) + r")[^\n]*\n?)"

    try:
        parts = re.split(split_regex, response_text, flags=re.IGNORECASE)
        logger.debug(f"Split into {len(parts)} parts using combined markers.")
    except re.error as e:
        logger.error(f"Regex error during split: {e}. Pattern: {split_regex}")
        return {key: "N/A (Regex Error)" for key in expected_headings}


    # 3. Assign Content based on Delimiters
    last_marker_heading = None
    for i, part in enumerate(parts):
        part = part.strip() if part else ""
        if not part:
            continue

        # Check if this part IS one of the markers we split by
        is_delimiter = False
        identified_heading = None
        for heading, config in markers.items():
            for pattern in config.get("patterns", []):
                # Use re.fullmatch for delimiters, ignoring surrounding whitespace from split
                if re.fullmatch(r"\s*" + pattern + r"[^\n]*", part, re.IGNORECASE):
                    is_delimiter = True
                    identified_heading = heading
                    break
            if is_delimiter:
                break

        if is_delimiter:
            # It's a marker, update the heading context for the *next* part
            last_marker_heading = identified_heading
            logger.debug(f"Identified marker for section: {last_marker_heading}")
        elif last_marker_heading:
            # It's content following a known marker
            logger.debug(f"Assigning content to '{last_marker_heading}': '{part[:100]}...'")
            # Append if section already has content (might happen with loose markers)
            # Only assign if not already filled by direct regex and content is substantial
            if parsed_data[last_marker_heading] is None or parsed_data[last_marker_heading].startswith("N/A"):
                 parsed_data[last_marker_heading] = part
            elif len(part) > 10: # Append if it looks like real content
                 parsed_data[last_marker_heading] += "\n" + part
        else:
             # Content before the first recognized marker
             logger.warning(f"Found unassigned content (before first marker?): '{part[:100]}...'")
             if parsed_data["Feedback"] is None: # Fallback assignment
                  parsed_data["Feedback"] = f"(Content before first marker?): {part}"

    # 4. Final check & Cleanup
    for heading in expected_headings:
        if parsed_data[heading] is None:
            parsed_data[heading] = "N/A (Not found in response)"
            logger.warning(f"Section '{heading}' could not be extracted.")

    return parsed_data

def get_ai_feedback(
    question_data: Dict,
    correct_answer_data: Dict,
    user_answer: str,
    marks: Optional[int]
) -> Optional[Dict[str, Optional[str]]]: # Return type allows None values in dict
    """
    Finds model, loads it using llama-cpp-python, generates feedback,
    parses the response flexibly, and unloads the model.

    Args:
        question_data: The dictionary representing the question.
        correct_answer_data: The dictionary representing the correct answer/marking scheme.
        user_answer: The answer submitted by the user.
        marks: The total marks allocated for the question.

    Returns:
        A dictionary containing the parsed AI response sections (values can be None),
        or None if a critical error occurred before generation/parsing.
    """
    logger.info(f"Requesting AI feedback for question ID: {question_data.get('id')}")

    model_path = find_model_path()
    if not model_path:
        logger.error("Could not proceed without model path.")
        return None

    # --- 1. Construct the Few-Shot Prompt ---
    question_text = question_data.get('question_text', 'N/A')
    sub_questions = question_data.get('sub_questions', 'N/A')
    max_marks_str = str(marks) if marks is not None else 'N/A'
    correct_answer_details = correct_answer_data.get('answer_details', 'Marking scheme not available.')

    # Start building the prompt
    prompt_parts = [
        """**ROLE:** You are a strict AI Examiner following Cambridge International marking standards. You are fair but demand a high level of understanding and precision. Do not be overly lenient or unnecessarily pedantic. Your goal is to provide insightful, actionable feedback to help the student improve significantly.

**TASK:** Evaluate the student's answer below based *only* on the provided Question and Marking Scheme/Correct Answer details. Award a mark out of the maximum available, provide detailed feedback, identify knowledge gaps, suggest specific study topics, propose reflection questions, present the correct answer, and rate the student's understanding objectively.

**CRITICAL INSTRUCTIONS - FOLLOW EXACTLY:**
*   Your response MUST start *immediately* with the first heading (`## Mark Awarded`). Do NOT include any introduction or preamble.
*   You MUST use the following Markdown headings *exactly* as written, including the `##` and spacing. Do NOT invent new headings or omit any. Use the format shown in the examples below.

**FORMATTING HEADINGS:**
1.  `## Mark Awarded`
2.  `## Feedback`
3.  `## Understanding Gap`
4.  `## Study Topics`
5.  `## Self-Reflection Questions`
6.  `## Correct Answer`
7.  `## Understanding Rating`

--- EXAMPLES START ---
"""
    ]

    # Add the examples from the imported list
    for i, example in enumerate(FEW_SHOT_EXAMPLES):
        prompt_parts.append(f"--- Example {i+1} ---")
        prompt_parts.append("**INPUT DATA:**")
        prompt_parts.append(example["input"].strip())
        prompt_parts.append("**RESPONSE:**")
        prompt_parts.append(example["output"].strip())
        prompt_parts.append("--- End Example {i+1} ---\n")

    # Add the separator and the actual query
    prompt_parts.append("""--- EXAMPLES END ---

**NOW, EVALUATE THE FOLLOWING INPUT:**

**INPUT DATA:**
""")
    prompt_parts.append(f"""
*   **Question:** {question_text}
*   **Sub-questions (if any):** {sub_questions}
*   **Maximum Marks:** {max_marks_str}
*   **Marking Scheme / Correct Answer:** {correct_answer_details}
*   **Student's Answer:** {user_answer}
""")
    prompt_parts.append("**RESPONSE:**") # Signal for AI to start its response

    # Join all parts into the final prompt string
    prompt = "\n".join(prompt_parts)

    logger.debug(f"Generated Few-Shot AI Prompt (structure):\n{prompt[:200]}...\n...\n...{prompt[-200:]}") # Log start/end

    # --- 2. Load Model and Generate Response ---
    llm = None
    response_text = None
    try:
        logger.info(f"Loading model: {model_path}...")
        llm = Llama(
            model_path=model_path,
            n_ctx=CONTEXT_SIZE,
            n_gpu_layers=GPU_LAYERS,
            verbose=False # Set verbose=False for cleaner logs now
        )
        logger.info("Model loaded. Generating response...")

        output = llm(
            prompt,
            max_tokens=MAX_TOKENS,
            stop=["<|endoftext|>", "<|im_end|>"],
            temperature=0.2,
            echo=False
        )

        response_text = output.get("choices", [{}])[0].get("text")
        if response_text:
             logger.info("Received response from AI model.")
             logger.debug(f"AI Raw Response Text:\n{response_text}") # <-- UNCOMMENT THIS LINE
        else:
             logger.warning("AI response 'choices' or 'text' field is missing or empty.")
             logger.debug(f"Full AI output dict: {output}")
             return None

    except Exception as e:
        logger.error(f"Error during AI model load or generation: {e}", exc_info=True)
        return None # Indicate failure
    finally:
        if llm is not None:
            logger.info("Unloading AI model...")
            del llm
            logger.info("AI model unloaded.")


    # --- 3. Parse the Response ---
    if response_text:
        # --- ADDED: Log raw text BEFORE parsing ---
        logger.info(f"RAW AI Response Text to be Parsed:\n---------------------\n{response_text}\n---------------------")
        # --- END ADDED ---

        logger.info("Parsing AI response using flexible parser...")
        parsed_data = parse_ai_response(response_text) # Call the new parser
        if parsed_data:
             logger.info("Finished parsing AI response.")
             logger.debug(f"Parsed Data: {parsed_data}") # Log the final parsed structure
             return parsed_data
        else:
             # parse_ai_response now returns a dict even on failure, maybe log instead
             logger.error("Flexible parsing returned empty data, indicates major issue.")
             return {key: "N/A (Parsing Failed)" for key in expected_headings} # Use keys from parser
    else:
        logger.error("No response text available for parsing.")
        return None

# Example of how you might call the Deepseek API (replace with actual implementation)
# def call_deepseek_api(prompt: str) -> Optional[str]:
#     try:
#         # Assuming Deepseek runs on localhost:port with a /generate endpoint
#         api_url = "http://localhost:11434/api/generate" # Example Ollama endpoint
#         payload = {
#             "model": "deepseek-coder", # Or your specific Deepseek model name
#             "prompt": prompt,
#             "stream": False # Get the full response at once
#         }
#         response = requests.post(api_url, json=payload, timeout=60) # 60 second timeout
#         response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
#         
#         # Assuming the response JSON has a 'response' field with the text
#         # Adjust based on your actual API's response structure
#         return response.json().get("response")
#         
#     except requests.exceptions.RequestException as e:
#         logger.error(f"HTTP Request failed: {e}")
#         return None
#     except Exception as e:
#         logger.error(f"Error calling Deepseek API: {e}")
#         return None 

# --- Helper: Extract Section from Example Output ---
def _extract_example_section(full_output: str, start_heading: str, end_heading: Optional[str] = None) -> str:
    """Extracts text between start_heading and end_heading (or EOF) from example output."""
    # Find start (case-insensitive)
    start_pattern = r"##\s*" + re.escape(start_heading)
    start_match = re.search(start_pattern, full_output, re.IGNORECASE)
    if not start_match:
        return f"N/A ({start_heading} not found in example)"

    start_index = start_match.end() # Start after the heading match

    # Find end
    end_index = len(full_output) # Default to end of string
    if end_heading:
        end_pattern = r"##\s*" + re.escape(end_heading)
        end_match = re.search(end_pattern, full_output[start_index:], re.IGNORECASE)
        if end_match:
            # End *before* the next heading starts
            end_index = start_index + end_match.start()

    return full_output[start_index:end_index].strip()

# --- Helper: Generation Function (Simplified usage) ---
def _generate_step(llm: Llama, step_prompt: str, max_tokens: int, stop_sequences: List[str]) -> Optional[str]:
    """Helper to run a single generation step, including repeat_penalty."""
    try:
        logger.debug(f"Generating step with max_tokens={max_tokens}, stop={stop_sequences}, repeat_penalty={REPEAT_PENALTY}")
        logger.debug(f"Step Prompt Snippet:\n{step_prompt[:300]}...\n...{step_prompt[-300:]}")
        output = llm(
            step_prompt,
            max_tokens=max_tokens,
            stop=stop_sequences,
            temperature=0.1, # Keep temp very low for factual marking
            repeat_penalty=REPEAT_PENALTY,
            echo=False
        )
        response_text = output.get("choices", [{}])[0].get("text")
        if response_text:
             logger.debug(f"Step Raw Response (from LLM):\n{response_text}")
             return response_text.strip()
        else:
             logger.warning("Step generation produced no text.")
             logger.debug(f"Full output dict: {output}")
             return None
    except Exception as e:
        logger.error(f"Error during generation step: {e}", exc_info=True)
        return None

# --- Helper: Parser for Mark AND Justification ---
def _parse_mark_and_justification(text: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    """Extracts both the mark and justification from the text."""
    if not text: return None, None
    mark, justification = None, None
    lines = text.strip().split('\n', 1)
    if lines:
        mark_match = re.search(r"(\d+\s*/\s*\d+)", lines[0])
        if mark_match:
            mark = mark_match.group(1).strip()
        if len(lines) > 1:
            justification = lines[1].strip()
        elif not mark:
             justification = lines[0].strip()
    if not mark:
         mark_match_fallback = re.search(r"(\d+\s*/\s*\d+)", text)
         if mark_match_fallback:
              mark = mark_match_fallback.group(1).strip()
              if not justification:
                   justification = text[mark_match_fallback.end():].strip()
    if justification:
        justification = re.sub(r"^(Justification|Explanation|Reason)[:\s]*", "", justification, flags=re.IGNORECASE).strip()
        if len(justification) < 3:
             justification = None
    logger.debug(f"Parsed Mark='{mark}', Justification='{str(justification)[:100]}...' from text: '{text[:100]}...'")
    return mark, justification

# --- UPDATED Orchestrator Function ---
def run_ai_evaluation(
    question_data: Dict,
    correct_answer_data: Dict,
    user_answer: str,
    marks: Optional[int]
) -> Optional[Dict[str, Optional[str]]]: # Return dict with mark and justification
    """
    Loads model once. Gets the mark AND a brief justification. Unloads model.
    """
    logger.info("Starting AI Evaluation (Mark + Justification).")
    model_path = find_model_path()
    if not model_path:
        logger.error("Cannot run evaluation: Model path not found.")
        return None

    llm = None
    results: Dict[str, Optional[str]] = {
        "Mark Awarded": None,
        "Mark Justification": None
    }

    try:
        logger.info(f"Loading model for evaluation: {model_path}...")
        llm = Llama(
            model_path=model_path,
            n_ctx=CONTEXT_SIZE,
            n_gpu_layers=GPU_LAYERS,
            verbose=False
        )
        logger.info("Model loaded.")

        # --- Prepare shared context AND LOG INPUTS ---
        question_text = question_data.get('question_text', 'N/A')
        sub_questions = question_data.get('sub_questions', 'N/A')
        max_marks_str = str(marks) if marks is not None else '?'

        # <<< --- Existing logging for received correct_answer_data --- >>>
        # ... (debug/info logs showing received structure) ...

        # --- MODIFIED: Extract details from the ACTUAL structure ---
        correct_answer_log_str = 'Marking scheme not available.' # Default
        if isinstance(correct_answer_data, dict):
            answers_list = correct_answer_data.get('answers')
            if isinstance(answers_list, list) and len(answers_list) > 0:
                first_answer = answers_list[0]
                if isinstance(first_answer, dict):
                    sub_answers = first_answer.get('sub_answers')
                    if isinstance(sub_answers, list):
                        # Format the sub_answers into a string for the AI
                        scheme_parts = []
                        for sub_answer in sub_answers:
                             if isinstance(sub_answer, dict):
                                 part_num = sub_answer.get('sub_number', '?')
                                 part_marks = sub_answer.get('marks', '?')
                                 part_text = sub_answer.get('text', 'N/A')
                                 part_notes = sub_answer.get('marking_notes', '')
                                 scheme_parts.append(f" - Part {part_num} ({part_marks} marks): {part_text}")
                                 if part_notes:
                                     scheme_parts.append(f"   Notes: {part_notes}")
                        if scheme_parts:
                             correct_answer_log_str = "\n".join(scheme_parts)
                        else:
                             logger.warning("Could not format sub_answers into a string.")
                    else:
                         logger.warning("Key 'sub_answers' is not a list in the first answer.")
                else:
                     logger.warning("First item in 'answers' list is not a dictionary.")
            else:
                logger.warning("Key 'answers' is not a non-empty list.")
        # --- END MODIFIED ---

        # --- Existing Logging Input Data ---
        logger.info("-----------------------------------------")
        logger.info("AI Input Data -> Question: %s", question_text)
        logger.info("AI Input Data -> Sub-Questions: %s", sub_questions)
        logger.info("AI Input Data -> Max Marks: %s", max_marks_str)
        logger.info("AI Input Data -> Student Answer: %s", user_answer)
        # This log now reflects the extracted scheme or the default message
        logger.info("AI Input Data -> Correct Answer/Scheme: %s", correct_answer_log_str)
        logger.info("-----------------------------------------")
        # --- END Logging ---

        # --- Ensure base_context uses the potentially updated correct_answer_log_str ---
        base_context = f"""
**Question:** {question_text}
**Sub-questions (if any):** {sub_questions}
**Maximum Marks:** {max_marks_str}
**Marking Scheme / Correct Answer Details:** {correct_answer_log_str}
**Student's Answer:** {user_answer}
"""
        # --- Step 1: Get Mark AND Justification ---
        logger.info("Evaluation Step 1: Getting Mark and Justification...")
        prompt1_parts = [
            f"**ROLE:** Strict Cambridge Examiner AI.",
            f"**TASK:** Evaluate the Student's Answer strictly against the Marking Scheme.",
            f"**Marking Process:**",
            f"  - Compare the Student's Answer point-by-point to the Marking Scheme details.",
            f"  - Award marks ONLY for points explicitly stated or clearly implied in the Student's Answer that match the scheme.",
            f"  - Adhere strictly to the Maximum Marks ({max_marks_str}). Award 0 if no points match.",
            f"**OUTPUT FORMAT:**",
            f"  1. FIRST line: ONLY the final numerical mark awarded in the format 'X / {max_marks_str}'.",
            f"  2. SECOND line: ONLY a brief (1-sentence maximum) justification for the awarded mark, explaining the key reason based on the Marking Scheme comparison.",
            f"**INPUT DATA:**",
            base_context,
            f"**Output:**" # Signal for response
        ]
        prompt = "\n".join(prompt1_parts)
        logger.debug(f"Full Prompt for Step 1:\n{prompt}") # Log full prompt for debugging

        # Generate Mark & Justification
        mark_just_text = _generate_step(llm, prompt, max_tokens=80, stop_sequences=["<|endoftext|>"])

        # Log Raw Output
        logger.info(f"Raw text for Mark/Justification:\n---------------------\n{mark_just_text}\n---------------------")

        # Parse Mark & Justification
        parsed_mark, parsed_justification = _parse_mark_and_justification(mark_just_text)
        results["Mark Awarded"] = parsed_mark if parsed_mark else "N/A (Parsing Failed)"
        results["Mark Justification"] = parsed_justification
        logger.info(f"Evaluation Result: Mark='{results['Mark Awarded']}', Justification captured={bool(results['Mark Justification'])}")

        logger.info("AI evaluation completed.")

    except Exception as e:
        logger.error(f"Error during AI evaluation: {e}", exc_info=True)
        if results["Mark Awarded"] is None: results["Mark Awarded"] = "N/A (Error Occurred)"
        if results["Mark Justification"] is None: results["Mark Justification"] = "N/A (Error Occurred)"
        return results
    finally:
        if llm is not None:
            logger.info("Unloading AI model...")
            del llm
            logger.info("AI model unloaded.")

    # Ensure placeholders if parsing failed but no exception occurred
    if results["Mark Awarded"] is None:
        results["Mark Awarded"] = "N/A (Unknown Error)"
    if results["Mark Justification"] is None:
         if results["Mark Awarded"].startswith("N/A"):
             results["Mark Justification"] = "N/A (Generation/Parsing Failed)"

    logger.debug(f"Final evaluation results: {results}")
    return results 