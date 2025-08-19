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

def create_task_detail_prompt(task_name, task_number, project_description, selected_language, completed_tasks_summary: str = ""):
    """
    Create a story-driven engineering ticket that teaches real software engineering concepts
    """
    
    # Build completed context
    completed_context = ""
    if completed_tasks_summary:
        completed_context = f"You've already completed: {completed_tasks_summary}\n"
    
    prompt = f"""You are a senior engineer, your role is to break down the project {project_description} into manageable tasks. For context, you are helping kids aged 12-18 to help them learn how to code, how to build software and understand software engineering concepts. You need to break the project down into Jira like tickets.

PROJECT CONTEXT:
{project_description}

Completed tasks:
{completed_context}

Next engineering challenge: Create ticket #{task_number} - {task_name}

CREATE ONE DETAILED JIRA-STYLE ENGINEERING TICKET:

**[ENGINEERING TICKET {task_number}] {task_name}**

**THE ENGINEERING CHALLENGE:**
The ticket should break down the project into a manageable task based on what has already completed and what is left to complete.

The ticket should contain prompts that the user will pass into Cursor AI to help them complete the task.

The prompts should; 
- build on the previous task
- not generate the full code solution, generate most of the code, but leave some for the user to complete 
- guide the user through the task to understand what they need to think about and do to complete the task
- the prompt should return information educating the user about everything they are doing. Concepts need to explained as simply as possible (explain like I'm 12 and then explain to an engineer)
- the prompt should return other things the user should research and study to develop a deeper understanding of each concept covered
- the prompt should explain why this concept is important in engineering and software development and how it fits into the bigger picture of the project
- the prompt should ensure we follow best practices and industry patterns, explaining this to the end user
- the prompt should also return questions for the user to answer to ensure they understand the concepts and are able to complete the task

Return ONLY the JSON object, no other text with:
1. the ticket title and ticket number (ie. 1 out of 10/12/20)
2. the ticket description
3. the number of story points the ticket is worth (and explaining how much work would be required to complete the task)
4. commands to run to test if the task is sufficiently complete
"""

    return prompt 