#!/usr/bin/env python3
"""
Test script for experimenting with different prompts for engineering ticket generation
Uses Groq cloud AI for consistent, high-quality responses
"""

import sys
import os
sys.path.append('src')

from src.core.ai.project_prompts import extract_json_from_reasoning_response

def test_chain_of_thought():
    """Test simplified single-prompt approach for task generation using Groq cloud AI"""
    
    # Simulate project data from database
    project_description = '''1. **Project Title**: "Water Access and Health"

2. **Problem Statement**: Many African communities lack access to clean water, leading to poor health outcomes. This project aims to help users request water from a simulated well, display current levels, and provide recommendations based on proximity.

3. **Project Description**: The app will allow users to request water from a simulated well, display the current level, and offer recommendations for better access. It includes a map service to visualize water sources.

4. **Key Features**: 
   - Requesting water from a well
   - Displaying current water level (via visual indicator)  
   - Showing the closest source of water
   - Providing recommendations based on proximity
   - Adding a map to show where the water is available

5. **Recommended Technology Stack**: 
   - Frontend: JavaScript for simplicity and ease of use
   - Backend: No backend needed, using vanilla JavaScript
   - Database: SQLite for simplicity
   - Additional Tools: Map service (e.g., Google Maps API)

6. **Difficulty Assessment**: This project is challenging but suitable for a 12-18 year old as it introduces practical problem-solving and data visualization while teaching user recommendations.'''

    task_number = 1
    task_name = 'Set up development environment and project structure'

    # Initialize Groq cloud AI client
    try:
        sys.path.append('src')
        from src.core.ai.groq_client import GroqProgrammingClient
        from src.utils.network_utils import is_online, can_reach_groq
        
        if not is_online():
            print("❌ No internet connection available")
            return
            
        if not can_reach_groq():
            print("❌ Groq API not reachable")
            return
            
        groq_client = GroqProgrammingClient()
        if not groq_client.is_available():
            print("❌ Groq client not available - check API key configuration")
            return
            
        print("✅ Groq cloud AI client initialized successfully")
        
    except ImportError as e:
        print(f"❌ Failed to import Groq client: {e}")
        return
    except Exception as e:
        print(f"❌ Error initializing Groq client: {e}")
        return

        # Generate Cursor-ready system prompt + incremental step prompts (no context checklist)
    prior_tasks_completed = False
    prompt = f"""
 You are generating a Cursor system prompt and a set of incremental, pasteable prompts for a beginner (age 12–18). Do not output any code directly unless a step explicitly requires minimal code. Return ONLY JSON matching the schema below.

Foundational goals:
- Teach by building incrementally with Cursor (vibe coding).
- Never jump ahead; one step at a time.
- Each step must include acceptance criteria and a simple verification.
- Be beginner-friendly: explain simply and add comments when code is created.
- Use the existing project context if available; if scope is ambiguous, ask for clarification first.
- Keep each step small and focused (5–15 minutes).

Schema to return exactly:
{{
  "cursor_system_prompt": "string (paste this into Cursor as the system prompt at the start of the session)",
  "steps": [
    {{
      "title": "string",
      "intent": "string",
      "cursor_prompt": {{
        "system_role": "string (role directives: patient teacher for 12–18; return artifacts only; incremental; embed simple 'why' explanations; tailor installs to Recommended Technology Stack)",
        "prompt": "string (AI-to-AI output contract phrased as 'Return'/'Provide'; do not instruct the learner; include concise scope guardrails; use shell commands only for setup/installation when applicable; end with: 'Stop after meeting the acceptance criteria. Ask me for confirmation before proceeding to the next step.')",
        "acceptance_criteria": ["string", "..."]
      }}
    }}
  ]
}}

Follow these rules in helping you generate the cursor promtps:
- Assume the learner is already using Cursor; do not ask about choosing or installing a code editor.
- With the cursor prompts, understand we are generate prompts for cursor to generate the output for the student to use. We also to ensure the prompt will generate educational content for the user to understand what is built.
- Begin the cursor_system_prompt with a 1–3 sentence project summary (what we are building) derived from Project context below.
- Use the "Recommended Technology Stack" from the Project context to decide what to install and configure; do not invent extra tools.
- Adopt a patient teacher persona for a 12–18 learner: explain simply, define terms, add brief comments when code is created, and encourage the learner to think (do not dump full solutions).
- Enforce incremental delivery: implement only the current step; do not jump ahead; wait for confirmation before expanding scope or adding dependencies.
- Tailor deliverables to the current task phase. All step prompts must instruct Cursor to return artifacts (do not instruct the learner):
  - Setup/install (first task only, if no prior tasks): From the "Recommended Technology Stack" in the Project context, return a JSON array of objects for Linux Mint commands to install and verify the required tools (e.g., Node LTS via nvm, Python via apt/pip, databases), each with keys "cmd" and "why" (use real values only). Include version checks and include a top-level "acceptance_criteria" array in the same JSON; do not add tools not listed in the stack.
  - Architecture/skeleton: Return a single fenced markdown block containing PROJECT_STRUCTURE.md with one-sentence purpose per folder/file; no extra commentary; include a final "Acceptance Criteria" section in the document.
  - Coding/feature: Return only the minimal code or diffs necessary for this step, with brief beginner-friendly comments inline; avoid unrelated files; include a top-of-file comment block titled "ACCEPTANCE CRITERIA" summarizing what should pass.
  - Testing: Return test commands and expected outcomes.
- Prohibit second-person imperative to the learner (no "you", "let's", "run" phrasing). Use neutral verbs: "Return", "Provide", "Produce".
- Do not generate PROJECT_STRUCTURE.md unless the task phase is architecture/skeleton.
- Require acceptance_criteria for each step; avoid separate verification and follow-up sections.
- Also embed acceptance criteria inside the returned artifact as described above.
- Each steps[i].cursor_prompt must begin with a 'System role:' line, the role of this AI is to act as a patient teacher, teaching 12-18 years olds engineering by guiding them in building projects. This means, it must return not just code to build, but educational content, explaining the code back to the user. 
- Each steps[i].cursor_prompt must be a JSON object with keys: system_role, prompt, acceptance_criteria.
- The system_role must define the AI’s role as a patient teacher for 12–18, artifact-return only, incremental, with simple 'why' explanations, tailored to the Recommended Technology Stack.
- The prompt must be an AI-to-AI output contract using 'Return/Provide' language (no learner imperatives), include concise scope guardrails, and end with: "Stop after meeting the acceptance criteria. Ask me for confirmation before proceeding to the next step."
- Each step must be doable without assuming unstated prior code.
- Use shell commands only for environment setup/installation; otherwise prefer natural language that lets Cursor generate code from context.
- Keep all text concise and child-friendly.

Project context:
{project_description}

Current task phase:
"Step {task_number}: {task_name}"

Return ONLY the JSON.
"""

    print("\n🔧 Testing Cursor system+steps JSON prompt (no context checklist)")
    print("-" * 80)
    print("PROMPT:")
    print("-" * 80)
    print(prompt)
    print("-" * 80)

    try:
        print("🚀 Generating response with Groq cloud AI...")
        
        # Use Groq cloud AI with the same prompt
        full_response = groq_client.generate_response(prompt)
        
        if not full_response:
            print("❌ No response received from Groq API")
            return
            
        print("\n📥 GROQ CLOUD AI RESPONSE:")
        print("-" * 80)
        print(full_response)
        print("-" * 80)

        # Extract JSON
        json_only = extract_json_from_reasoning_response(full_response)
        print("\n📄 EXTRACTED JSON:")
        print("-" * 80)
        print(json_only)
        print("-" * 80)

    except Exception as e:
        print(f"❌ Error generating response with Groq: {e}")

def test_custom_prompt():
    """Test a custom simplified prompt with cloud/local AI options"""
    
    prompt = """You are creating an engineering task for a student aged 12-18.

PROJECT: Water Access and Health app
TASK: Set up development environment and project structure

Create a JSON response with:
- "title": Specific task name
- "ticket_number": "1 out of 8" 
- "description": What to build + 3 Cursor prompts that start with "Tell Cursor:" + explanations
- "story_points": 1-8 difficulty
- "test_commands": ["command1", "command2"]

Output only valid JSON."""

    print("🔧 Testing simplified custom prompt")
    print("=" * 60)
    print("PROMPT:")
    print("-" * 60)
    print(prompt)
    print("=" * 60)

    # Check if we can use cloud AI
    try:
        sys.path.append('src')
        from src.core.ai.groq_client import GroqProgrammingClient
        from src.utils.network_utils import is_online, can_reach_groq
        
        if is_online() and can_reach_groq():
            print("🌐 Network available - trying cloud AI first")
            groq_client = GroqProgrammingClient()
            if groq_client.is_available():
                try:
                    response = groq_client.generate_response(prompt)
                    if response:
                        print("\n📥 CLOUD AI RESPONSE:")
                        print("-" * 60)
                        print(response)
                        print("-" * 60)
                        return
                except Exception as e:
                    print(f"☁️ Cloud AI failed: {e}, falling back to local")
    except ImportError:
        print("☁️ Cloud AI not available, using local")
    
    # If cloud AI is not available, exit gracefully
    print("❌ Groq cloud AI not available")
    print("Please ensure:")
    print("1. Internet connection is available")
    print("2. GROQ_API_KEY is set in environment variables")
    print("3. Groq API is reachable")
    return

if __name__ == "__main__":
    print("🧪 Engineering Ticket Prompt Testing (Groq Cloud AI)")
    print("=" * 60)
    
    choice = input("Choose test:\n1. Chain-of-thought (Groq cloud AI)\n2. Test custom prompt (Groq cloud AI)\nEnter 1 or 2: ")
    
    if choice == "1":
        test_chain_of_thought()
    elif choice == "2":
        test_custom_prompt()
    else:
        print("Invalid choice") 