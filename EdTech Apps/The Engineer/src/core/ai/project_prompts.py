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
    
    prompt = f"""You are a senior software engineer creating a development step for students aged 12-18 to build the project.

PROJECT: {project_description}

CURRENT STEP: {task_name} (Step #{task_number} of 7-10 total steps)

{completed_context}

EXAMPLES LIBRARY:
{open('prompt_examples_library.md', 'r').read()}

FOLLOW THE EXAMPLES ABOVE for:
- How to structure Cursor AI prompts
- The level of detail and educational content
- How to explain engineering concepts simply
- The format and style of instructions

REQUIREMENTS:
- Create buildable development steps where necessary
- Use the technology stack specified in the project
- Include 4-6 Cursor AI prompts following the examples above - add these to the description
- Explain engineering concepts simply for beginners
- Build on previously completed tasks when applicable

DESCRIPTION MUST CONTAIN:
1. What to build: [specific feature description]
2. Why it matters: [educational value and real-world connection]
3. Cursor prompts: [4-6 specific prompts starting with "Cursor prompt:"]
4. Engineering concepts: [simple explanations for beginners]
5. Real-world connection: [how this applies to actual software]
6. Research topics: [what students should explore next]

OUTPUT FORMAT - Return ONLY valid JSON:
{{
  "title": "Specific, actionable development step",
  "ticket_number": "{task_number} out of X",
  "description": "DESCRIPTION OUTPUT HERE",
  "story_points": 1-8,
  "test_commands": ["command1", "command2", "command3"]
}}

Use the examples above as your guide for quality and format."""

    return prompt 