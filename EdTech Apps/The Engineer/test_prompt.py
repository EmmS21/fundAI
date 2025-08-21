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

    # Version 2: Example-Driven with Library Reference
    prompt = f"""You are a senior software engineer creating a development step for students aged 12-18 to build the water access app.

PROJECT: {project_description}

CURRENT STEP: {task_name} (Step #{task_number} of 7-10 total steps)

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

    print("\n🔧 Testing simplified task generation prompt with Groq cloud AI")
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