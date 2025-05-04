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
# Increase tokens slightly to allow for CoT + final summary without grammar constraint
GENERATION_MAX_TOKENS = 768 # Reverted to a higher value
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

# --- Helper: Generation Function (No Grammar) ---
# Simplified helper function name
def _generate_step(
    llm: Llama,
    step_prompt: str,
    # grammar parameter removed
    max_tokens: int,
    stop_sequences: List[str]
) -> Optional[str]:
    """Helper to run a single generation step without grammar."""
    try:
        logger.debug(f"Generating step (No Grammar), max_tokens={max_tokens}, stop={stop_sequences}, repeat_penalty={REPEAT_PENALTY}")
        logger.debug(f"Step Prompt Snippet:\n{step_prompt[:300]}...\n...{step_prompt[-300:]}")

        # <<< --- Call LLM without grammar parameter --- >>>
        output = llm(
            step_prompt,
            max_tokens=max_tokens,
            stop=stop_sequences,
            temperature=0.1,
            repeat_penalty=REPEAT_PENALTY,
            # grammar=None, # Ensure it's not passed
            echo=False
        )
        # <<< --- End LLM Call --- >>>

        response_text = output.get("choices", [{}])[0].get("text")
        if response_text:
             logger.debug(f"Step Raw Response (from LLM, No Grammar):\n{response_text}")
             return response_text # Return the raw text
        else:
             logger.warning("Step generation produced no text.")
             logger.debug(f"Full output dict: {output}")
             return None
    except Exception as e:
        logger.error(f"Error during generation step: {e}", exc_info=True)
        return None

# --- Orchestrator Function ---
def run_ai_evaluation(
    question_data: Dict,
    correct_answer_data: Dict,
    user_answer: Dict[str, str], # Expecting dict
    marks: Optional[int]
) -> Optional[Tuple[Dict[str, Optional[str]], Optional[str]]]:
    """
    Loads model once. Uses explicit CoT prompt to guide reasoning and asks
    for a specific 3-line output format, focusing on detailed Rationale and Study Topics. Parses the output using regex.
    """
    logger.info("Starting AI Evaluation (Explicit CoT + Enhanced Rationale/Study Topics).")
    model_path = find_model_path()
    if not model_path: logger.error("Cannot run evaluation: Model path not found."); return None

    llm = None
    results: Dict[str, Optional[str]] = { "Grade": None, "Rationale": None, "Study Topics": None }

    try:
        # --- Load Model ---
        logger.info(f"Loading model for evaluation: {model_path}...")
        llm = Llama( model_path=model_path, n_ctx=CONTEXT_SIZE, n_gpu_layers=GPU_LAYERS, verbose=False )
        logger.info("Model loaded.")

        # --- Prepare context ---
        question_text=question_data.get('question_text','') 
        sub_questions=question_data.get('sub_questions',[]) 

        # --- Format user answer dict (same as previous attempt) ---
        user_answer_str_parts = []
        if isinstance(user_answer, dict):
            if len(user_answer) == 1 and "main" in user_answer:
                 user_answer_str_parts.append(user_answer["main"])
            else:
                 for key, value in sorted(user_answer.items()): 
                      user_answer_str_parts.append(f"- Part {key}: {value}")
            user_answer_formatted = "\n".join(user_answer_str_parts) if user_answer_str_parts else "N/A"
        else:
             logger.warning("run_ai_evaluation received user_answer as string, expected dict. Using as is.")
             user_answer_formatted = user_answer or "N/A"
        # --------------------------------------------

        max_marks_str=str(marks) if marks is not None else '?'
        correct_answer_log_str='Marking scheme not available.'
        if isinstance(correct_answer_data,dict): # Extract scheme correctly
            answers_list=correct_answer_data.get('answers');
            if isinstance(answers_list,list) and len(answers_list)>0:
                first_answer=answers_list[0]; scheme_parts=[]
                if isinstance(first_answer,dict):
                    sub_answers=first_answer.get('sub_answers')
                    if isinstance(sub_answers,list):
                        for sub_answer in sub_answers:
                            if isinstance(sub_answer,dict):
                                part_num=sub_answer.get('sub_number','?');part_marks=sub_answer.get('marks','?');part_text=sub_answer.get('text','N/A');part_notes=sub_answer.get('marking_notes','')
                                scheme_parts.append(f" - Part {part_num} ({part_marks} marks): {part_text}")
                                if part_notes: scheme_parts.append(f"   Notes: {part_notes}")
                        if scheme_parts: correct_answer_log_str="\n".join(scheme_parts)
        # Logging inputs...
        logger.info("-----------------------------------------\nAI Input Data -> Question: %s\nAI Input Data -> Sub-Questions: %s\nAI Input Data -> Max Marks: %s\nAI Input Data -> Student Answer:\n%s\nAI Input Data -> Correct Answer/Scheme:\n%s\n-----------------------------------------", 
                    question_text, sub_questions, max_marks_str, user_answer_formatted, correct_answer_log_str)
        base_context = f"""
**Question:** {question_text}
**Sub-questions (if any):** {sub_questions}
**Maximum Marks:** {max_marks_str}
**Marking Scheme / Correct Answer Details:** {correct_answer_log_str}
**Student's Answer:** 
{user_answer_formatted}
"""
        # --- Define the Explicit CoT Prompt (Describe output format clearly) ---
        prompt1_parts = [
            f"**ROLE:** AI Examiner simulating a teacher's step-by-step marking.",
            f"**TASK:** Carefully evaluate the Student's Answer against the Marking Scheme below. Determine the mark by assessing demonstrated understanding for each part. Follow the reasoning steps internally, then provide ONLY the final output strictly following the REQUIRED OUTPUT FORMAT described below.",
            f"**Internal Reasoning Steps to Follow:**",
            f"  1. **Initialize Score:** Start score at 0 / {max_marks_str}.",
            f"  2. **Analyze Part-by-Part:** For each part:",
            f"     a. Compare the student's answer meaning/intent for this part to the scheme requirements.",
            f"     b. Assess understanding: Is it relevant? Is it correct?",
            f"     c. Award whole marks for this part based ONLY on alignment with the scheme. Award 0 if irrelevant/wrong.",
            f"     d. Add marks to the running total.",
            f"     e. **Identify Specific Gaps:** Note down the *specific concepts or details* from the marking scheme that the student missed or got wrong in this part.",
            f"  3. **Final Calculation:** Determine the `Final Calculated Mark: F / {max_marks_str}`.",
            f"  4. **Rationale:** Formulate a concise (1-3 sentences) explanation for the final mark. This explanation MUST explicitly mention the *key concepts or requirements from the Marking Scheme* (identified in Step 2d) that the student failed to demonstrate understanding of.",
            f"  5. **Detailed Study Plan:** Based *only* on the specific gaps identified in Step 2d, create a detailed study plan. Include these three components clearly labeled:",
            f"     a. **Specific Topics:** List the precise topics or sub-topics from the syllabus/scheme the student needs to revise (e.g., 'Structure of a nephron', 'Definition of selective re-uptake').",
            f"     b. **Guiding Questions:** Provide 2-3 specific questions the student should ask themselves *while studying* these topics to ensure deep understanding (e.g., 'What pressure drives ultrafiltration?', 'How does ADH affect the collecting duct?').",
            f"     c. **Google Search Terms:** Suggest 2-3 concrete terms or phrases the student can search for online to find relevant explanations or diagrams (e.g., 'glomerular filtration process animation', 'role of loop of Henle concentration gradient').",
            f"**REQUIRED OUTPUT FORMAT:**", # Still expecting 3 main lines, but content is enhanced
            f"  After performing the internal reasoning, your entire output MUST consist of ONLY the following three lines, starting *exactly* with these headings:",
            f"  Line 1: Start with 'Grade: ' followed by the Final Calculated Mark from Step 3 (e.g., Grade: 0 / {max_marks_str}).",
            f"  Line 2: `Rationale: [Detailed rationale sentence(s) from Step 4, mentioning specific missed concepts from the scheme]`",
            f"  Line 3: `Study Topics: [Detailed study plan from Step 5, including 'Specific Topics:', 'Guiding Questions:', and 'Google Search Terms:']`", # Content is enhanced here
            f"  Do NOT include your internal reasoning steps or any other text in the final output.",
            f"**INPUT DATA:**",
            base_context,
            f"**Output:**"
        ]
        # ----------------------------------------------------
        prompt = "\\n".join(prompt1_parts)
        logger.debug(f"Full Prompt for Generation (Enhanced Rationale/Study Topics):\\n{prompt}")

        # --- Generate Response WITHOUT Grammar ---
        raw_response_text = _generate_step(
            llm,
            prompt, # Pass the generated prompt
            max_tokens=GENERATION_MAX_TOKENS,
            stop_sequences=["<|endoftext|>"]
        )

        # Log the Raw Output
        logger.info(f"Raw FULL text from AI (Enhanced Rationale/Study Topics):\n---------------------\n{raw_response_text}\n---------------------")

        # --- Parsing Logic (Remains the same - relies on headings) ---
        if raw_response_text:
            # Use regex to find lines starting with the specific prefixes
            grade_match = re.search(r"^Grade:(.*)$", raw_response_text, re.MULTILINE)
            # Use the multiline extractor helper for Rationale and Study Topics
            # Define the helper function (or ensure it's defined elsewhere in the file)
            def extract_multiline_content(heading: str, text: str) -> Optional[str]:
                 start_match = re.search(f"^{heading}:(.*)$", text, re.MULTILINE | re.IGNORECASE)
                 if not start_match: return None
                 content_start_index = start_match.end()
                 next_heading_index = len(text)
                 headings = ["Grade:", "Rationale:", "Study Topics:"] # Only these 3 headings expected
                 for h in headings:
                      next_match = re.search(f"^{h}", text[content_start_index:], re.MULTILINE | re.IGNORECASE)
                      if next_match:
                           current_next_index = content_start_index + next_match.start()
                           next_heading_index = min(next_heading_index, current_next_index)
                 content = text[start_match.start(1):next_heading_index].strip()
                 # Replace escaped newlines if the model adds them literally
                 content = content.replace('\\n', '\n') 
                 return content if content else None

            results["Grade"] = grade_match.group(1).strip() if grade_match else "N/A (Not Found)"
            results["Rationale"] = extract_multiline_content("Rationale", raw_response_text) or "N/A (Not Found)"
            results["Study Topics"] = extract_multiline_content("Study Topics", raw_response_text) or "N/A (Not Found)"

            if grade_match and results["Rationale"] != "N/A (Not Found)" and results["Study Topics"] != "N/A (Not Found)":
                logger.info(f"Successfully parsed all 3 required output lines using Regex/Multiline Extraction.")
            else:
                logger.warning(f"Could not find all required lines using Regex/Multiline Extraction. Grade found: {bool(grade_match)}, Rationale found: {results['Rationale'] != 'N/A (Not Found)'}, Study Topics found: {results['Study Topics'] != 'N/A (Not Found)'}")
        else:
            logger.error("Generation failed to produce output.")
            results = {k: "N/A (Generation Error)" for k in results}
        # --- END Parsing Logic ---

        logger.info("AI evaluation completed.")

    except Exception as e:
        logger.error(f"Error during AI evaluation: {e}", exc_info=True)
        results = {k: f"N/A (Exception: {e})" for k in results}
        prompt = None # Ensure prompt is None on error
    finally:
        if llm is not None: 
            logger.info("Unloading AI model...")
            del llm
            logger.info("AI model unloaded.")

    logger.debug(f"Final evaluation results: {results}")
    # --- RETURN PROMPT ALONGSIDE RESULTS ---
    return results, prompt 