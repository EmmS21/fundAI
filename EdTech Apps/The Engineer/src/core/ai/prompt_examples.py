"""
The Engineer AI Tutor - Programming Prompt Examples
Specialized prompts for programming and engineering evaluation
"""

from typing import Dict, Any, Optional

def get_programming_prompt(
    question_data: Dict[str, Any],
    correct_answer_data: Dict[str, Any], 
    user_answer: Dict[str, str],
    marks: Optional[int] = None
) -> str:
    """
    Build a comprehensive programming evaluation prompt
    
    Args:
        question_data: Programming question details
        correct_answer_data: Expected solution and test cases  
        user_answer: Student's code submission
        marks: Maximum marks for the question
        
    Returns:
        Formatted prompt string for AI evaluation
    """    
    problem = question_data.get('problem', 'Programming Problem')
    language = question_data.get('language', 'Python')
    difficulty = question_data.get('difficulty', 'Medium')
    topics = question_data.get('topics', [])
    constraints = question_data.get('constraints', '')
    
    expected_solution = correct_answer_data.get('solution', '')
    test_cases = correct_answer_data.get('test_cases', [])
    explanation = correct_answer_data.get('explanation', '')
    
    student_code = user_answer.get('code', '')
    student_approach = user_answer.get('approach', '')
    
    max_marks = marks or 10
    
    prompt = f"""
You are an expert programming tutor evaluating a {language} programming assignment.

## Problem Statement
{problem}

**Difficulty:** {difficulty}
**Topics:** {', '.join(topics) if topics else 'General Programming'}
**Language:** {language}

{f"**Constraints:** {constraints}" if constraints else ""}

## Expected Solution
```{language}
{expected_solution}
```

{f"**Explanation:** {explanation}" if explanation else ""}

## Test Cases
{format_test_cases(test_cases)}

## Student Submission
```{language}
{student_code}
```

{f"**Student's Approach:** {student_approach}" if student_approach else ""}

## Evaluation Instructions
Please evaluate this solution on a scale of 0-{max_marks} considering:

1. **Correctness**: Does the code solve the problem correctly?
2. **Code Quality**: Is the code well-structured, readable, and follows best practices?
3. **Efficiency**: Is the algorithm efficient in terms of time and space complexity?
4. **Edge Cases**: Does it handle edge cases appropriately?

Provide your evaluation in this exact format:

Grade: X/{max_marks}
Code Quality: [Poor/Fair/Good/Excellent]
Correctness: [Incorrect/Partially Correct/Correct]
Efficiency: [Poor/Fair/Good/Excellent]
Rationale: [Detailed explanation of strengths and weaknesses]
Study Topics: [Specific topics the student should review]
Suggested Improvements: [Actionable feedback for improvement]

</evaluation>
"""
    
    return prompt

def format_test_cases(test_cases: list) -> str:
    """Format test cases for the prompt"""
    if not test_cases:
        return "No test cases provided."
    
    formatted = ""
    for i, test_case in enumerate(test_cases, 1):
        input_data = test_case.get('input', '')
        expected_output = test_case.get('expected', '')
        description = test_case.get('description', f'Test case {i}')
        
        formatted += f"""
**Test Case {i}:** {description}
- Input: {input_data}
- Expected Output: {expected_output}
"""
    
    return formatted

def get_code_review_prompt(code: str, language: str, focus_areas: list = None) -> str:
    """
    Generate a prompt for general code review
    
    Args:
        code: Source code to review
        language: Programming language
        focus_areas: Specific areas to focus on (e.g., ['performance', 'security'])
        
    Returns:
        Formatted code review prompt
    """
    
    focus_text = ""
    if focus_areas:
        focus_text = f"Pay special attention to: {', '.join(focus_areas)}"
    
    prompt = f"""
You are a senior software engineer conducting a code review.

## Code to Review ({language})
```{language}
{code}
```

{focus_text}

Please provide a comprehensive code review covering:

1. **Code Quality**: Structure, readability, naming conventions
2. **Best Practices**: Language-specific best practices and patterns
3. **Performance**: Time/space complexity and optimization opportunities  
4. **Security**: Potential security vulnerabilities
5. **Maintainability**: How easy would this code be to maintain and extend?
6. **Testing**: Testability and potential test cases

Format your response as:

Complexity: [Low/Medium/High]
Readability: [Poor/Fair/Good/Excellent]
Best Practices: [List of practices followed/violated]
Potential Issues: [Any code smells or issues]
Security Concerns: [Any security-related issues]
Performance Notes: [Efficiency observations]
Suggestions: [Specific improvement recommendations]
"""
    
    return prompt

def get_algorithm_analysis_prompt(code: str, language: str, algorithm_type: str = None) -> str:
    """
    Generate a prompt for algorithm analysis
    
    Args:
        code: Algorithm implementation
        language: Programming language
        algorithm_type: Type of algorithm (e.g., 'sorting', 'graph', 'dynamic programming')
        
    Returns:
        Formatted algorithm analysis prompt
    """
    
    algorithm_text = f" ({algorithm_type})" if algorithm_type else ""
    
    prompt = f"""
You are an algorithms expert analyzing a{algorithm_text} implementation.

## Algorithm Implementation ({language})
```{language}
{code}
```

Please provide a detailed analysis covering:

1. **Algorithm Identification**: What algorithm is being implemented?
2. **Time Complexity**: Best, average, and worst-case time complexity
3. **Space Complexity**: Memory usage analysis
4. **Correctness**: Is the implementation correct?
5. **Optimizations**: Possible improvements or optimizations
6. **Alternative Approaches**: Other algorithms that could solve this problem

Format your response as:

Algorithm: [Name/type of algorithm]
Time Complexity: [Big O notation with explanation]
Space Complexity: [Big O notation with explanation]
Correctness: [Correct/Incorrect with reasoning]
Strengths: [What the implementation does well]
Weaknesses: [Areas for improvement]
Optimizations: [Specific optimization suggestions]
Alternatives: [Other algorithmic approaches]
"""
    
    return prompt

def get_debugging_prompt(code: str, language: str, error_message: str = None, expected_behavior: str = None) -> str:
    """
    Generate a prompt for debugging assistance
    
    Args:
        code: Code with potential bugs
        language: Programming language
        error_message: Any error messages received
        expected_behavior: What the code should do
        
    Returns:
        Formatted debugging prompt
    """
    
    error_text = f"\n**Error Message:**\n{error_message}" if error_message else ""
    behavior_text = f"\n**Expected Behavior:**\n{expected_behavior}" if expected_behavior else ""
    
    prompt = f"""
You are a debugging expert helping to identify and fix issues in code.

## Code with Issues ({language})
```{language}
{code}
```
{error_text}
{behavior_text}

Please help debug this code by:

1. **Identifying Issues**: What's wrong with the code?
2. **Root Cause**: Why is the issue occurring?
3. **Fix Suggestions**: How to fix the identified issues
4. **Prevention**: How to avoid similar issues in the future

Format your response as:

Issues Found: [List of identified problems]
Root Cause: [Why these issues are occurring]
Suggested Fixes: [Specific code changes needed]
Corrected Code: [If applicable, provide the fixed version]
Prevention Tips: [How to avoid similar issues]
Testing Strategy: [How to verify the fixes work]
"""
    
    return prompt

def get_performance_optimization_prompt(code: str, language: str, performance_requirements: str = None) -> str:
    """
    Generate a prompt for performance optimization analysis
    
    Args:
        code: Code to optimize
        language: Programming language
        performance_requirements: Specific performance goals
        
    Returns:
        Formatted optimization prompt
    """
    
    requirements_text = f"\n**Performance Requirements:**\n{performance_requirements}" if performance_requirements else ""
    
    prompt = f"""
You are a performance optimization specialist analyzing code for efficiency improvements.

## Code to Optimize ({language})
```{language}
{code}
```
{requirements_text}

Please analyze this code for performance optimization opportunities:

1. **Current Performance**: Time and space complexity analysis
2. **Bottlenecks**: Identify performance bottlenecks
3. **Optimization Opportunities**: Specific areas for improvement
4. **Optimized Implementation**: Provide optimized version if possible
5. **Trade-offs**: Discuss any trade-offs between optimizations

Format your response as:

Current Complexity: [Time and space complexity]
Bottlenecks: [Performance bottlenecks identified]
Optimization Strategy: [Approach to improve performance]
Optimized Code: [Improved implementation]
Performance Gain: [Expected improvement]
Trade-offs: [Any compromises made for performance]
Benchmarking: [How to measure the improvements]
"""
    
    return prompt

# Programming language specific prompts
LANGUAGE_SPECIFIC_PROMPTS = {
    "python": {
        "style_guide": "Follow PEP 8 style guidelines",
        "best_practices": "Use Pythonic idioms and built-in functions",
        "common_issues": "Watch for mutable default arguments, proper exception handling"
    },
    "javascript": {
        "style_guide": "Follow modern JavaScript (ES6+) conventions",
        "best_practices": "Use const/let instead of var, proper async/await usage",
        "common_issues": "Avoid callback hell, handle promises properly"
    },
    "java": {
        "style_guide": "Follow Oracle Java Code Conventions",
        "best_practices": "Proper use of access modifiers, follow SOLID principles",
        "common_issues": "Resource management, proper exception handling"
    },
    "cpp": {
        "style_guide": "Follow Google C++ Style Guide or similar",
        "best_practices": "RAII, proper memory management, const correctness",
        "common_issues": "Memory leaks, buffer overflows, undefined behavior"
    }
} 