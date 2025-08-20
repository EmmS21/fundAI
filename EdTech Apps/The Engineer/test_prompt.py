#!/usr/bin/env python3
"""
Test script for experimenting with different prompts for engineering ticket generation
"""

import sys
import os
sys.path.append('src')

from llama_cpp import Llama
from core.ai.project_prompts import extract_json_from_reasoning_response

# Model configuration
MODEL_PATH = "/Users/emmanuelsibanda/Documents/models/llama/DeepSeek-R1-Distill-Qwen-1.5B-Q4_K_M.gguf"

def load_model():
    """Load the local AI model with EXACT same parameters as app"""
    try:
        model = Llama(
            model_path=MODEL_PATH,
            n_ctx=16384,  
            verbose=False,
            n_threads=4,
            n_gpu_layers=-1  
        )
        print("✅ Model loaded successfully")
        return model
    except Exception as e:
        print(f"❌ Error loading model: {e}")
        return None

def test_chain_of_thought():
    """Test 4-step chain-of-thought with concrete examples to guide AI output"""
    
    # Read the examples library
    with open('prompt_examples_library.md', 'r') as f:
        examples_library = f.read()
    
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

    completed_context = ''
    task_number = 1
    task_name = 'Set up development environment and project structure'

    model = load_model()
    if not model:
        return

    # STEP 1: Educational analysis from AI Tutor + Prompt Engineer perspective
    step1_prompt = f"""You are an AI Tutor, your role is to use your superior prompt engineering skills to breakdown this project {project_description} into a small singular ticket. You are doing this in order to guide users aged 12 - 18 to build software engineering projects while learning foundational software engineering and programming concepts.

Your role: Create a learning ticket for students to build: {task_name}

CRITICAL: You do NOT build code. You do NOT output code. You create PROMPTS that students will paste into Cursor AI to learn while building.

PROJECT CONTEXT:
{project_description}

Completed tasks:
{completed_context}

EDUCATIONAL ANALYSIS: What should a 12-18 year old learn from this task?
- What engineering concepts are involved (remember: they're beginners)
- Why these concepts matter for real software development
- What foundational knowledge they need
- How this connects to solving African community problems
- What should they research to understand deeper

EXAMPLE OF EDUCATIONAL ANALYSIS:
For a "Build Counter Button" task, analysis would focus on:
- Variables (storing information like counting water bottles needed daily)
- Functions (organizing code like organizing your room)
- User interaction (making apps that people actually want to use)
- Project structure (keeping files organized like school folders)

Remember: You are designing the LEARNING EXPERIENCE, not building the project."""

    print("\n🔧 STEP 1: Engineering analysis")
    print("-" * 50)
    step1_response = model(step1_prompt, max_tokens=800, temperature=0.6, top_p=0.9, repeat_penalty=1.1)['choices'][0]['text']
    print("Analysis:", step1_response.strip())

        # STEP 2: Installation Commands with Educational Explanations  
    step2_prompt = f"""You are creating installation commands with educational explanations for 12-18 year old African students.

Based on this educational analysis:
{step1_response.strip()}

Create 3-4 terminal commands for setting up the water access project.

EXAMPLES LIBRARY:
{examples_library}

The examples in the library above give you context of what type of information to return in the ticket and how the prompts should look like."""

    print("\n🔧 STEP 2: Installation commands")
    print("-" * 50)
    step2_response = model(step2_prompt, max_tokens=800, temperature=0.6, top_p=0.9, repeat_penalty=1.1)['choices'][0]['text']
    print("Commands:", step2_response.strip())

    # STEP 3: Cursor Prompt Engineering with Concrete Examples
    step3_prompt = f"""You are a PROMPT ENGINEERING EXPERT creating educational prompts for 12-18 year old African students.

Based on this educational analysis:
{step1_response.strip()}

Your job: Write 4-6 educational prompts that students will copy-paste into Cursor AI to build the project{project_description}. Focus purely on engineering tasks.

EXAMPLES LIBRARY:
{examples_library}

Follow the Cursor prompt examples from the library above."""

    print("\n🔧 STEP 3: Educational Cursor prompts")
    print("-" * 50)
    step3_response = model(step3_prompt, max_tokens=1200, temperature=0.6, top_p=0.9, repeat_penalty=1.1)['choices'][0]['text']
    print("Cursor prompts:", step3_response.strip())

    # STEP 4: Educational Ticket JSON Assembly
    step4_prompt = f"""You are an AI TUTOR finalizing an educational ticket for 12-18 year old students learning software engineering.

Combine these educational components into a Jira-style learning ticket:

EDUCATIONAL ANALYSIS: {step1_response.strip()}
INSTALLATION COMMANDS: {step2_response.strip()}
CURSOR PROMPTS FOR STUDENTS: {step3_response.strip()}

Create a JSON learning ticket with these fields:
- "title": Clear task title for what students will learn to build
- "ticket_number": Format as "X out of Y" (e.g., "1 out of 8") 
- "description": Single text containing: What students will build, installation commands with beginner explanations, the exact Cursor prompts students will paste, engineering concepts explained simply for teenagers, why these matter in real software development, what students should research, learning questions to test understanding
- "story_points": Integer (1-8 scale: 1=30min, 8=full day) 
- "test_commands": Array of terminal commands students run to verify their work

CRITICAL: This is a LEARNING TICKET, not a development task. Focus on education for African youth.

Return ONLY valid JSON, no other text."""

    print("\n🔧 STEP 4: JSON formatting")
    print("-" * 50)
    step4_response = model(step4_prompt, max_tokens=1000, temperature=0.6, top_p=0.9, repeat_penalty=1.1)['choices'][0]['text']
    print("Final JSON:", step4_response.strip())

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
        from core.ai.groq_client import GroqProgrammingClient
        from utils.network_utils import is_online, can_reach_groq
        
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
    
    # Fallback to local AI
    print("🏠 Using local AI")
    model = load_model()
    if not model:
        return

    try:
        print("🚀 Generating response...")
        # Use EXACT same parameters as the app
        response = model(
            prompt,
            max_tokens=16384,
            temperature=0.3,
            top_p=0.9,
            repeat_penalty=1.1,
            stop=["Human:", "Assistant:", "\n\n---"],
            echo=False,
            stream=False
        )
        
        full_response = response['choices'][0]['text']
        print("\n📥 LOCAL AI RESPONSE:")
        print("-" * 60)
        print(full_response)
        print("-" * 60)

        # Extract JSON
        json_only = extract_json_from_reasoning_response(full_response)
        print("\n📄 EXTRACTED JSON:")
        print("-" * 60)
        print(json_only)
        print("-" * 60)

    except Exception as e:
        print(f"❌ Error generating response: {e}")

if __name__ == "__main__":
    print("🧪 Engineering Ticket Prompt Testing")
    print("=" * 60)
    
    choice = input("Choose test:\n1. Chain-of-thought (3 steps)\n2. Test custom prompt\nEnter 1 or 2: ")
    
    if choice == "1":
        test_chain_of_thought()
    elif choice == "2":
        test_custom_prompt()
    else:
        print("Invalid choice") 