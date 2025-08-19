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
Return ONLY a JSON array of engineering ticket titles that:
- Follow logical dependency order (each builds on previous)
- Teach core software engineering concepts
- Are specific and actionable for {selected_language}
- Connect to real-world engineering practices
- Break complex work into manageable 1-2 hour chunks

EXAMPLE FORMAT: ["Set up development environment and project structure", "Build core data models and business logic", "Create user interface and API endpoints", "Implement testing and deployment pipeline"]

Output ONLY the JSON array, no other text."""

    return prompt

def create_task_detail_prompt(task_name, task_number, project_description, selected_language, completed_tasks_summary: str = ""):
    """
    Create a story-driven engineering ticket that teaches real software engineering concepts
    """
    
    # Extract project context
    project_lines = project_description.split('\n')
    project_title = "this project"
    problem_statement = "solve a real-world problem"
    
    # Try to extract project title and problem from description
    for line in project_lines:
        if "Project Title" in line or "Title:" in line:
            project_title = line.split(':')[-1].strip() if ':' in line else line.strip()
        elif "Problem Statement" in line:
            problem_statement = line.split(':')[-1].strip() if ':' in line else line.strip()
    
    # Define engineering concepts for each ticket number
    engineering_concepts = {
        1: {
            "primary": "Development Environment Setup",
            "secondary": "Project Structure & Dependencies",
            "real_world": "Every software team starts projects the same way - setting up consistent environments so all developers can collaborate effectively.",
            "companies": "Google, Microsoft, Netflix"
        },
        2: {
            "primary": "Data Modeling & Business Logic", 
            "secondary": "API Design Patterns",
            "real_world": "The core of any application is how it handles and processes data - this is what makes software actually useful.",
            "companies": "Spotify, Instagram, WhatsApp"
        },
        3: {
            "primary": "User Interface & Experience",
            "secondary": "Frontend-Backend Integration", 
            "real_world": "Great software isn't just functional - it needs to be intuitive and enjoyable for real people to use.",
            "companies": "Apple, TikTok, Discord"
        },
        4: {
            "primary": "Testing & Quality Assurance",
            "secondary": "Deployment & DevOps Basics",
            "real_world": "Professional software must be reliable and easily deployable - this is what separates hobby code from production systems.",
            "companies": "Amazon, Uber, GitHub"
        }
    }
    
    concepts = engineering_concepts.get(task_number, engineering_concepts[1])
    
    # Build completed context
    completed_context = ""
    if completed_tasks_summary:
        completed_context = f"You've already completed: {completed_tasks_summary}\n"
    
    prompt = f"""You're helping a future software engineer (age 12-18) build real engineering skills through {project_title}.

ENGINEERING STORY ARC:
We're building {project_title} because {problem_statement}. 
{completed_context}
Next engineering challenge: Master {concepts['primary']} - a skill every professional software engineer needs.

REAL-WORLD CONNECTION:
Companies like {concepts['companies']} rely on {concepts['primary'].lower()} because {concepts['real_world']}

CREATE ONE DETAILED JIRA-STYLE ENGINEERING TICKET:

**[ENGINEERING TICKET {task_number}/4] {task_name}**

OUTPUT FORMAT: Return ONLY valid JSON in this exact structure:

{{
  "title": "{task_name}",
  "story_points": [1-8 based on complexity],
  "story_points_explanation": "Brief explanation of why this point value and what it represents for students",
  "prerequisites": [List of what should be completed before this ticket],
  "ticket_content": "**OBJECTIVE:**\\nWhat you'll build and why this is critical in professional software development.\\n\\n**ENGINEERING CONCEPTS:**\\n- {concepts['primary']}: [Why engineers use this approach]\\n- {concepts['secondary']}: [How this connects to industry best practices]\\n\\n**SETUP COMMANDS:**\\n```bash\\n# Purpose: [Why this setup is needed]\\n[specific command for {selected_language}]\\n```\\n\\n**IMPLEMENTATION STEPS:**\\n1. [Specific step with engineering explanation]\\n2. [Next step building on the first]\\n3. [Final step to complete the feature]\\n\\n**CURSOR AI PROMPTS:**\\n- \\"Help me understand [specific concept] and explain why engineers structure it this way\\"\\n- \\"Walk me through implementing [specific feature] with best practices for {selected_language}\\"\\n- \\"Review my code and suggest improvements following industry standards\\"\\n\\n**ACCEPTANCE CRITERIA:**\\n- [ ] Feature works correctly and handles edge cases\\n- [ ] Code follows {selected_language} best practices\\n- [ ] You can explain the engineering concepts to someone else\\n- [ ] Implementation follows industry patterns\\n\\n**REAL-WORLD CONNECTION:**\\nHow this connects to what professional engineers do at companies like {concepts['companies']}.\\n\\n**NEXT STEPS:**\\nBrief preview of what the next ticket will build on this foundation.",
  "builds_on": [List of previous ticket titles this depends on],
  "enables_next": [List of what future tickets this will enable]
}}

Return ONLY the JSON object, no other text."""

    return prompt 