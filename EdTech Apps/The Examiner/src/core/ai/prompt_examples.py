# src/core/ai/prompt_examples.py

# List containing few-shot examples for the AI feedback prompt.
# Each element is a dictionary with 'input' and 'output' keys.
# The 'output' MUST strictly follow the requested Markdown format.

FEW_SHOT_EXAMPLES = [
    # Example 1: Decent Answer, Partial Marks
    {
        "input": """
*   **Question:** Explain the process of osmosis in plant cells.
*   **Sub-questions (if any):** N/A
*   **Maximum Marks:** 3
*   **Marking Scheme / Correct Answer:** {'answer_details': {'points': ['Movement of water molecules (1 mark)', 'From a region of higher water potential to lower water potential (1 mark)', 'Across a partially permeable membrane (1 mark)']}}
*   **Student's Answer:** Osmosis is when water moves across a membrane in plants.
""",
        "output": """## Mark Awarded
1 / 3
## Feedback
**Strengths:** You correctly identified that osmosis involves water movement across a membrane.
**Weaknesses:** The definition is incomplete. It lacks the crucial concept of water potential gradient and incorrectly omits that the membrane must be partially permeable.
## Understanding Gap
The student has a basic idea but lacks understanding of the driving force (water potential difference) and the specific nature of the membrane involved in osmosis.
## Study Topics
*   Definition of Osmosis (including water potential).
*   Concept of Water Potential.
*   Properties of Partially Permeable Membranes.
*   Osmosis in Plant Cells (context).
## Self-Reflection Questions
*   Did my definition include the direction of water movement based on water potential?
*   Did I specify the type of membrane required for osmosis?
*   Have I confused osmosis with simple diffusion?
## Correct Answer
Osmosis is the movement of water molecules from a region of higher water potential to a region of lower water potential across a partially permeable membrane.
## Understanding Rating
Poor
"""
    },
    # Example 2: Irrelevant Answer, Zero Marks
    {
        "input": """
*   **Question:** State the function of red blood cells.
*   **Sub-questions (if any):** N/A
*   **Maximum Marks:** 2
*   **Marking Scheme / Correct Answer:** {'answer_details': {'points': ['Transport/carry oxygen (1 mark)', 'Contain hemoglobin (which binds to oxygen) (1 mark)']}}
*   **Student's Answer:** Red blood cells are important for fighting diseases in the body. They attack bacteria.
""",
        "output": """## Mark Awarded
0 / 2
## Feedback
**Strengths:** None.
**Weaknesses:** The answer provided describes the function of white blood cells (phagocytes/lymphocytes), not red blood cells. The information is entirely incorrect for the question asked.
## Understanding Gap
The student fundamentally misunderstands the role of red blood cells and appears to be confusing them with white blood cells.
## Study Topics
*   Components of Blood (specifically Red Blood Cells vs White Blood Cells).
*   Function of Red Blood Cells (Oxygen Transport).
*   Role of Hemoglobin.
## Self-Reflection Questions
*   Did I read the question carefully and identify the specific cell type asked about?
*   What is the main function associated with the red colour of blood?
*   Which blood cells are involved in the immune system?
## Correct Answer
The main function of red blood cells is to transport oxygen from the lungs to the body tissues. They contain hemoglobin, which binds to oxygen.
## Understanding Rating
Very Poor
"""
    }
]
