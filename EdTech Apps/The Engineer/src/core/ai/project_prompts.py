"""
Project Generation Prompts for The Engineer AI Tutor
Prompts for generating contextual programming projects for young African learners
"""

def create_project_generation_prompt(user_scores, selected_language, user_data):
    """
    Create a prompt for AI to generate a contextual project for young African learners
    
    Args:
        user_scores: Dict containing initial assessment and project scores
        selected_language: The programming language chosen by the user
        user_data: User profile information including age, location context
    """
    
    # Extract scores
    initial_score = user_scores.get('initial_assessment_score', 0)
    section_scores = user_scores.get('section_scores', {})
    username = user_scores.get('username', 'Student')
    
    # Format section scores for the prompt
    score_breakdown = []
    for section, score in section_scores.items():
        score_breakdown.append(f"- {section}: {score:.1f}%")
    
    score_summary = "\n".join(score_breakdown) if score_breakdown else "No detailed scores available"
    
    prompt = f"""You are an AI Tutor creating a programming project for a young learner in Africa aged 12-18. 

STUDENT PROFILE:
- Name: {username}
- Age Range: 12-18 years old
- Location Context: Africa (consider local challenges, opportunities, and cultural context)
- Overall Engineering Thinking Score: {initial_score:.1f}%
- Detailed Assessment Scores:
{score_summary}

SELECTED PROGRAMMING LANGUAGE: {selected_language}

PROJECT REQUIREMENTS:
1. **Context-Specific**: The project must solve a real problem that young people in Africa can relate to and understand. Consider challenges like:
   - Access to education, healthcare, or clean water
   - Local business opportunities
   - Community communication needs
   - Agricultural or environmental challenges
   - Transportation or logistics issues
   - Local entrepreneurship opportunities

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
    Create a simple prompt to generate just task titles as strict JSON
    """
    project_lines = project_description.split('\n')[:5]
    project_summary = '\n'.join(project_lines)
    
    prompt = f"""You must output ONLY valid JSON. No preamble, no explanations.
Return a JSON array with EXACTLY 4 UNIQUE short task titles (strings), derived from the project below.

PROJECT SUMMARY:
{project_summary}

CONSTRAINTS:
- Output only JSON (e.g., ["Title 1", "Title 2", "Title 3", "Title 4"]).
- Each title must be unique, context-specific, and actionable.
- No placeholders, no examples, no markdown, no extra text.
- Keep titles concise (max ~60 chars).
"""

    return prompt

def create_task_detail_prompt(task_name, task_number, project_description, selected_language, completed_tasks_summary: str = ""):
    """
    Create a prompt to generate detailed, educational content for kids learning programming
    """
    
    prompt = f"""AI Tutor for kids 12-18. Be direct, no thinking shown.

TASK: {task_name}
LANGUAGE: {selected_language}
STEP: {task_number}/4

Output format:
**What You'll Build:** Brief description
**Commands:**
```bash
sudo apt install python3 -y
```
**Test:** python3 --version"""

    return prompt 