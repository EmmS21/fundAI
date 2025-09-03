"""
Project Generation Prompts for The Engineer AI Tutor
Prompts for generating contextual programming projects for young African learners
"""

def create_project_generation_prompt(user_scores, selected_language, user_data, project_theme=None):
    """
    Create a prompt for AI to generate a contextual project for young African learners
    
    Args:
        user_scores: Dict containing initial assessment and project scores
        selected_language: The programming language chosen by the user
        user_data: User profile information including age, location context
        project_theme: Optional theme to guide project generation for variety
    """
    
    # Extract scores safely
    initial_score = user_scores.get('overall_score', user_scores.get('initial_assessment_score', 0))
    section_scores = user_scores.get('section_scores', {})
    username = user_scores.get('username', 'Student')
    
    # Format section scores for the prompt (handle different data structures)
    score_breakdown = []
    try:
        if isinstance(section_scores, dict):
            for section, score_data in section_scores.items():
                if isinstance(score_data, dict) and 'correct' in score_data and 'total' in score_data:
                    # Handle format: {"section": {"correct": 2, "total": 4}}
                    percentage = (score_data['correct'] / score_data['total']) * 100 if score_data['total'] > 0 else 0
                    score_breakdown.append(f"- {section}: {percentage:.1f}%")
                elif isinstance(score_data, (int, float)):
                    # Handle format: {"section": 85.5}
                    score_breakdown.append(f"- {section}: {score_data:.1f}%")
    except (TypeError, KeyError, ZeroDivisionError):
        pass  # If parsing fails, just use default
    
    score_summary = "\n".join(score_breakdown) if score_breakdown else "No detailed scores available"
    
    # Ensure all variables are safe for f-string formatting
    safe_username = str(username) if username else "Student"
    safe_initial_score = float(initial_score) if isinstance(initial_score, (int, float)) else 0.0
    safe_selected_language = str(selected_language) if selected_language else "Python"
    safe_score_summary = str(score_summary) if score_summary else "No detailed scores available"
    
    prompt = f"""You are an AI Tutor creating a programming project for a young learner in Africa aged 12-18. 

STUDENT PROFILE:
- Name: {safe_username}
- Age Range: 12-18 years old
- Location Context: Africa (consider local challenges, opportunities, and cultural context)
- Overall Engineering Thinking Score: {safe_initial_score:.1f}%
- Detailed Assessment Scores:
{safe_score_summary}

SELECTED PROGRAMMING LANGUAGE: {safe_selected_language}

PROJECT REQUIREMENTS:
1. **Context-Specific**: The project must solve a real problem that young people in Africa can relate to and understand. Consider challenges like:
   - Access to education, healthcare, or clean water
   - Local business opportunities
   - Community communication needs
   - Agricultural or environmental challenges
   - Transportation or logistics issues
   - Local entrepreneurship opportunities

{"FOCUS THEME: Pay special attention to " + str(project_theme) + " when designing this project." if project_theme else ""}

2. **Technical Scope**: 
   - Frontend: Simple, clean user interface (no heavy frameworks)
   - Backend: Server-side logic and API endpoints
   - Database: Simple data storage and retrieval
   - Technology Stack: Recommend specific Python or JavaScript-based tools

3. **Skill Level**: Based on their assessment scores, create a project that:
   - Challenges them appropriately without being overwhelming
   - Builds on programming fundamentals they should already know
   - Introduces new concepts gradually
   - Focuses on practical problem-solving

4. **Learning Focus**: This is for practicing programming skills, not production deployment. Emphasize:
   - Clean, readable code
   - Understanding core concepts
   - Problem-solving approach
   - Real-world application

RECOMMENDED TECHNOLOGY STACKS:
For Python-focused projects:
- Frontend: HTML, CSS, JavaScript (vanilla or minimal libraries)
- Backend: Flask or FastAPI
- Database: SQLite or PostgreSQL

For JavaScript-focused projects:
- Frontend: HTML, CSS, JavaScript (vanilla or minimal libraries like Alpine.js)
- Backend: Node.js with Express
- Database: SQLite or MongoDB

OUTPUT FORMAT:
Please provide a detailed project description including:

1. **Project Title**: A clear, engaging name

2. **Problem Statement**: What real African context problem does this solve? (2-3 sentences)

3. **Project Description**: Detailed explanation of what the student will build (1 paragraph)

4. **Key Features**: List 4-6 specific features the application will have

5. **Recommended Technology Stack**: 
   - Frontend technologies
   - Backend framework and language
   - Database choice
   - Any additional tools needed

6. **Difficulty Assessment**: Based on their scores, explain why this project level is appropriate for them

IMPORTANT OUTPUT INSTRUCTIONS:
- Start your response IMMEDIATELY with "1. **Project Title**:" 
- Do NOT include any reasoning, thinking process, or explanatory text before the project description
- Do NOT say things like "I'll create a project..." or "Based on the assessment..." 
- Do NOT include any preamble or introduction
- Provide ONLY the structured project information in the exact format specified above

Generate a project that will genuinely excite and engage a young African learner while teaching them valuable programming skills through building something meaningful to their context."""

    return prompt

def create_task_headers_prompt(project_description, selected_language):
    """
    Create a prompt to generate engineering-focused task breakdown that teaches real software engineering
    """
    project_lines = project_description.split('\n')[:8]  # Get more context for better engineering breakdown
    project_summary = '\n'.join(project_lines)
    
    prompt = f"""You are a Senior Software Engineer breaking down a project for junior engineers (age 12-18) learning full-stack development.

PROJECT TO BREAK DOWN:
{project_summary}

LANGUAGE: {selected_language}

Your task: Create a logical engineering progression that teaches real software engineering practices. Determine how many tickets are needed based on project complexity (typically 4-8 tickets, but could be more for complex projects).

ENGINEERING PROGRESSION PRINCIPLES:
1. Start with foundational setup (environment, basic structure)
2. Build core functionality (business logic, data handling)  
3. Add user interaction (frontend, APIs)
4. Complete with testing and deployment concepts

OUTPUT REQUIREMENTS:
Return ONLY a JSON array of ticket objects that:
- Follow logical dependency order (each builds on previous)
- Teach core software engineering concepts
- Are specific and actionable for {selected_language}
- Connect to real-world engineering practices
- Break complex work into manageable 1-2 hour chunks

EXAMPLE FORMAT: [
  {{"title": "Set up development environment", "story_points": 2}},
  {{"title": "Build core data models", "story_points": 3}}, 
  {{"title": "Create user interface", "story_points": 5}}
]

Story points scale: 1=30min, 2=1hr, 3=2hrs, 5=4hrs, 8=full day

Output ONLY the JSON array, no other text."""

    return prompt



def extract_json_from_reasoning_response(response: str) -> str:
    """
    Extract JSON object from a response that may contain reasoning before the JSON.
    Returns only the JSON part for parsing.
    """
    if not response:
        return ""
    
    json_start = response.find('{"')
    if json_start == -1:
        return response
    
    # Extract from the JSON start to the end
    json_part = response[json_start:].strip()
    return json_part

def extract_task_json_from_response(response: str) -> str:
    """
    Extract JSON from AI task generation responses with robust brace matching.
    Specifically designed for task detail extraction.
    """
    if not response:
        return ""
    
    # Remove code block markers if present
    response = response.replace('```json', '').replace('```', '')
    
    # Find JSON start
    json_start = response.find('{')
    if json_start == -1:
        # Fallback to original function logic
        return extract_json_from_reasoning_response(response)
    
    # Count braces to find the matching closing brace
    brace_count = 0
    json_end = json_start
    
    for i in range(json_start, len(response)):
        if response[i] == '{':
            brace_count += 1
        elif response[i] == '}':
            brace_count -= 1
            if brace_count == 0:
                json_end = i + 1
                break
    
    # Extract the balanced JSON
    if brace_count == 0:  # Found matching closing brace
        json_part = response[json_start:json_end].strip()
        
        # Validate it's valid JSON by trying to parse
        try:
            import json
            json.loads(json_part)
            return json_part
        except json.JSONDecodeError:
            # If invalid, fall back to original logic
            pass
    
    # Fallback to original function logic
    return extract_json_from_reasoning_response(response)

def create_task_detail_prompt(task_name, task_number, project_description, selected_language, completed_tasks_summary: str = ""):
    """
    Create a story-driven engineering ticket that teaches real software engineering concepts
    """
    
    # Build completed context
    completed_context = ""
    if completed_tasks_summary:
        completed_context = f"You've already completed: {completed_tasks_summary}\n"
    
    # Determine if we should ask for total_project_tasks (only for first task)
    is_first_task = task_number == 1
    
    prompt = f"""
 You are generating a Cursor system prompt and a set of incremental, pasteable prompts for a beginner (age 12–18). Do not output any code directly unless a step explicitly requires minimal code. Return ONLY JSON matching the schema below.

Foundational goals:
- Teach by building incrementally with Cursor (vibe coding).
- Never jump ahead; one step at a time.
- Each step must include acceptance criteria and a simple verification.
- Be beginner-friendly: explain simply and add comments when code is created.
- Use the existing project context if available; if scope is ambiguous, ask for clarification first.
- Keep each step small and focused (5–15 minutes).

Examples library (follow tone, format, clarity):
{open('prompt_examples_library.md', 'r').read()}

Schema to return exactly:
{{
  "cursor_system_prompt": "string (paste this into Cursor as the system prompt at the start of the session)",{' "total_project_tasks": "integer (total number of tasks needed to complete this entire project - minimum 7, maximum 12)",' if is_first_task else ''}
  "current_task_number": "integer (which task this is in the sequence - e.g., 1, 2, 3, etc.)",
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

{'CRITICAL: Determine the total number of tasks needed for this complete project:' if is_first_task else 'TASK SEQUENCE:'}
{'''- Analyze the project complexity and scope from the Project context
- Break down the project into logical phases: setup, core features, advanced features, testing, deployment
- Ensure the project requires MINIMUM 7 tasks and MAXIMUM 12 tasks for completion
- Set "total_project_tasks" to this number and "current_task_number" to the current task position
- Each task should represent 1-3 hours of work for a beginner (age 12-18)''' if is_first_task else '''- This is task {task_number} in an existing project sequence
- Set "current_task_number" to {task_number}
- Do NOT include "total_project_tasks" in your response (already determined in Task 1)
- Focus on this specific task within the overall project flow'''}

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
{completed_context}
Current task phase:
"Step {task_number}: {task_name}"

Return ONLY the JSON.
"""

    return prompt 