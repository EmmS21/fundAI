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

Return ONLY a JSON object with exactly these fields:
- "title": Clear, specific task title describing what will be built
- "ticket_number": Format as "X out of Y" (e.g., "1 out of 8") 
- "description": Write as a single text string containing: What specific code to build, 3-4 exact prompts to paste into Cursor AI (start each with "Cursor prompt:"), engineering concepts explained simply, why these concepts matter for real software projects, specific things to research, technical questions about the implementation
- "story_points": Integer representing effort level (1-8 scale, where 1=30min, 8=full day)
- "test_commands": Array of 2-3 specific terminal commands to verify task completion

Output must be valid JSON only, no other text."""
