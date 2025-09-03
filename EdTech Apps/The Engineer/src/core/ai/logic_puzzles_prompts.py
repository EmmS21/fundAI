"""
Logic Puzzles AI Prompts for The Engineer
Generates Python-based MCQ questions for young learners aged 12-18
"""

import json
from typing import Dict, List, Optional

def create_question_generation_prompt(
    category_name: str,
    category_description: str, 
    difficulty_level: int = 1,
    topics_focus: Optional[List[str]] = None,
    batch_size: int = 10
) -> str:
    """
    Create a prompt for generating Logic Puzzles MCQ questions
    
    Args:
        category_name: One of 6 categories (git_workflow, clean_code, etc.)
        category_description: Human-readable description of the category
        difficulty_level: 1-5 scale (1=beginner, 5=advanced)
        topics_focus: Optional list of specific topics to focus on
        batch_size: Number of questions to generate (default 10)
    """
    
    # Map category to specific Python concepts
    category_concepts = {
        'git_workflow': [
            'git commands basics', 'repository initialization', 'staging and commits',
            'branching concepts', 'merging basics', 'version control workflow',
            'git status interpretation', 'undoing changes', 'remote repositories'
        ],
        'clean_code': [
            'variable naming conventions', 'function structure', 'code comments',
            'indentation and formatting', 'meaningful variable names', 'function purpose',
            'code readability', 'avoiding code duplication', 'simple vs complex solutions'
        ],
        'database_design': [
            'database basics', 'tables and rows', 'primary keys', 'data types',
            'simple SQL queries', 'INSERT statements', 'SELECT basics',
            'database relationships', 'data organization'
        ],
        'api_development': [
            'what is an API', 'HTTP methods basics', 'GET vs POST', 'JSON format',
            'API endpoints', 'request/response cycle', 'status codes', 
            'simple API calls', 'data exchange'
        ],
        'testing': [
            'what is testing', 'debugging basics', 'print statements for debugging',
            'finding errors in code', 'test cases', 'expected vs actual results',
            'edge cases', 'code validation', 'error handling'
        ],
        'performance_optimization': [
            'code efficiency', 'loop optimization', 'avoiding unnecessary operations',
            'memory usage basics', 'time complexity basics', 'choosing right algorithms',
            'list vs set performance', 'string operations efficiency'
        ]
    }
    
    # Get concepts for this category
    concepts = category_concepts.get(category_name, [])
    
    # Focus topics if specified
    focus_instruction = ""
    if topics_focus:
        focus_instruction = f"\nFOCUS TOPICS: Pay special attention to these topics: {', '.join(topics_focus)}"
    
    # Difficulty level guidance
    difficulty_guidance = {
        1: "Very basic Python syntax, simple concepts, obvious code patterns",
        2: "Basic Python with simple logic, easy debugging, straightforward concepts", 
        3: "Intermediate Python, some complex logic, moderate debugging skills needed",
        4: "Advanced Python concepts, complex logic, challenging debugging scenarios",
        5: "Expert-level Python, very complex scenarios, advanced problem-solving required"
    }
    
    prompt = f"""You are an AI tutor creating Python-based multiple choice questions for young learners in Africa aged 12-18.

QUESTION CATEGORY: {category_description}
DIFFICULTY LEVEL: {difficulty_level}/5 - {difficulty_guidance.get(difficulty_level, 'Standard level')}
NUMBER OF QUESTIONS: {batch_size}
{focus_instruction}

PYTHON CONCEPTS FOR THIS CATEGORY:
{chr(10).join(f"- {concept}" for concept in concepts)}

QUESTION REQUIREMENTS:
1. **Educational Focus**: Each question should teach or test understanding of Python programming concepts related to {category_description.lower()}

2. **Age-Appropriate**: 
   - Use simple, clear language suitable for 12-18 year olds
   - Avoid overly complex technical jargon
   - Use relatable examples and scenarios

3. **Question Types**:
   - Code analysis: "What does this code do?"
   - Error identification: "What's wrong with this code?"
   - Syntax understanding: "Which is the correct way to...?"
   - Concept application: "How would you implement...?"
   - Best practices: "Which approach is better and why?"

4. **Code Examples**:
   - Keep code snippets short (1-10 lines maximum)
   - Use clear variable names
   - Include common beginner mistakes as wrong options
   - Show practical, real-world-ish examples when possible

5. **Multiple Choice Options**:
   - Exactly 4 options (A, B, C, D)
   - Make all options plausible but only one correct
   - Include common misconceptions as wrong answers
   - Avoid "All of the above" or "None of the above"

6. **Clue System**:
   - Provide exactly 3 progressive clues per question
   - Clue 1: Gentle hint about the concept involved
   - Clue 2: More specific guidance about the solution approach
   - Clue 3: Almost gives away the answer but requires final thinking

OUTPUT FORMAT:
Return ONLY a valid JSON array with exactly {batch_size} questions. Each question must have this exact structure:

```json
[
  {{
    "question_text": "Clear question asking about Python code or concept",
    "code_snippet": "# Python code example (if applicable)\nprint('Hello, World!')",
    "question_type": "mcq",
    "difficulty_level": {difficulty_level},
    "option_a": "First possible answer",
    "option_b": "Second possible answer", 
    "option_c": "Third possible answer",
    "option_d": "Fourth possible answer",
    "correct_answer": "A",
    "clue_1": "Gentle hint about the concept",
    "clue_2": "More specific guidance", 
    "clue_3": "Strong hint but still requires thinking",
    "category": "{category_name}",
    "topics": ["specific_topic_1", "specific_topic_2"]
  }}
]
```

IMPORTANT RULES:
- Return ONLY the JSON array, no other text
- Ensure all JSON is valid and properly escaped
- All questions must be unique and non-repetitive
- Code snippets should be syntactically correct Python
- Options should be similar in length and plausibility
- Test a variety of concepts within the category
- Make questions that help students learn, not trick them

Generate {batch_size} high-quality Python MCQ questions for {category_description} now:"""

    return prompt

def create_adaptive_question_prompt(
    user_stats: Dict,
    category_name: str,
    category_description: str,
    recent_performance: Dict,
    batch_size: int = 10
) -> str:
    """
    Create an adaptive prompt that generates questions based on user performance
    
    Args:
        user_stats: User's historical performance data
        category_name: Target category
        category_description: Human-readable category description  
        recent_performance: Recent session results
        batch_size: Number of questions to generate
    """
    
    # Analyze performance to adjust difficulty
    accuracy = user_stats.get('accuracy_percentage', 0)
    avg_time = user_stats.get('average_time_per_question', 0)
    current_difficulty = user_stats.get('current_difficulty_level', 1)
    
    # Determine next difficulty level
    if accuracy >= 80 and avg_time < 30:  # Fast and accurate
        suggested_difficulty = min(5, current_difficulty + 1)
        focus_note = "Increase difficulty - user is performing well"
    elif accuracy < 60:  # Struggling
        suggested_difficulty = max(1, current_difficulty - 1) 
        focus_note = "Reduce difficulty - user needs more practice with basics"
    else:
        suggested_difficulty = current_difficulty
        focus_note = "Maintain current difficulty level"
    
    # Identify weak areas from recent performance
    weak_topics = []
    strong_topics = []
    
    if 'topic_performance' in recent_performance:
        for topic, perf in recent_performance['topic_performance'].items():
            if perf < 60:
                weak_topics.append(topic)
            elif perf > 80:
                strong_topics.append(topic)
    
    adaptive_instruction = f"""
ADAPTIVE LEARNING CONTEXT:
- User's current accuracy: {accuracy:.1f}%
- Average time per question: {avg_time:.1f} seconds  
- Current difficulty level: {current_difficulty}
- Suggested difficulty: {suggested_difficulty}
- Focus: {focus_note}
"""
    
    if weak_topics:
        adaptive_instruction += f"\nWEAK TOPICS TO FOCUS ON: {', '.join(weak_topics)}"
    if strong_topics:
        adaptive_instruction += f"\nSTRONG TOPICS (can increase complexity): {', '.join(strong_topics)}"
    
    # Use base prompt with adaptive modifications
    base_prompt = create_question_generation_prompt(
        category_name=category_name,
        category_description=category_description,
        difficulty_level=suggested_difficulty,
        topics_focus=weak_topics if weak_topics else None,
        batch_size=batch_size
    )
    
    # Insert adaptive context after the category info
    lines = base_prompt.split('\n')
    insert_index = 4  # After the focus instruction line
    lines.insert(insert_index, adaptive_instruction)
    
    return '\n'.join(lines)

def validate_generated_questions(questions_json: str) -> tuple[bool, List[Dict], List[str]]:
    """
    Validate the generated questions JSON response
    
    Args:
        questions_json: Raw JSON string from AI response
        
    Returns:
        Tuple of (is_valid, parsed_questions, errors)
    """
    errors = []
    
    try:
        questions = json.loads(questions_json)
    except json.JSONDecodeError as e:
        return False, [], [f"Invalid JSON: {str(e)}"]
    
    if not isinstance(questions, list):
        return False, [], ["Response must be a JSON array"]
    
    required_fields = [
        'question_text', 'option_a', 'option_b', 'option_c', 'option_d',
        'correct_answer', 'clue_1', 'clue_2', 'clue_3', 'category', 'topics'
    ]
    
    valid_questions = []
    
    for i, question in enumerate(questions):
        question_errors = []
        
        # Check required fields
        for field in required_fields:
            if field not in question:
                question_errors.append(f"Question {i+1}: Missing field '{field}'")
            elif not question[field]:
                question_errors.append(f"Question {i+1}: Empty field '{field}'")
        
        # Validate correct_answer
        if 'correct_answer' in question:
            if question['correct_answer'] not in ['A', 'B', 'C', 'D']:
                question_errors.append(f"Question {i+1}: correct_answer must be A, B, C, or D")
        
        # Validate difficulty_level
        if 'difficulty_level' in question:
            if not isinstance(question['difficulty_level'], int) or question['difficulty_level'] < 1 or question['difficulty_level'] > 5:
                question_errors.append(f"Question {i+1}: difficulty_level must be integer 1-5")
        
        # Validate topics
        if 'topics' in question:
            if not isinstance(question['topics'], list):
                question_errors.append(f"Question {i+1}: topics must be an array")
        
        if not question_errors:
            valid_questions.append(question)
        else:
            errors.extend(question_errors)
    
    is_valid = len(errors) == 0 and len(valid_questions) > 0
    return is_valid, valid_questions, errors

# Example usage and testing
if __name__ == "__main__":
    # Test prompt generation
    prompt = create_question_generation_prompt(
        category_name="clean_code",
        category_description="Clean Code",
        difficulty_level=2,
        batch_size=5
    )
    print("Generated prompt:")
    print(prompt) 