"""
The Engineer AI Tutor - Groq Cloud AI Client
Programming-focused cloud evaluation
"""

import logging
from typing import Dict, Any, Optional, Tuple
import json

try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    Groq = None
    GROQ_AVAILABLE = False

from .prompt_examples import get_programming_prompt
from config.secrets import get_groq_api_key
from config.settings import AI_CONFIG

logger = logging.getLogger(__name__)

class GroqProgrammingClient:
    """Groq cloud AI client specialized for programming evaluation"""
    
    def __init__(self):
        self.client = None
        self.api_key = get_groq_api_key()
        
        print(f"[DEBUG GROQ INIT] GROQ_AVAILABLE: {GROQ_AVAILABLE}")
        print(f"[DEBUG GROQ INIT] API key present: {bool(self.api_key)}")
        
        if GROQ_AVAILABLE and self.api_key:
            print(f"[DEBUG GROQ INIT] Attempting to create Groq client...")
            try:
                self.client = Groq(api_key=self.api_key)
                print(f"[DEBUG GROQ INIT] ✅ Groq client created successfully")
                logger.info("Groq client initialized successfully")
            except Exception as e:
                print(f"[DEBUG GROQ INIT] ❌ Failed to create Groq client: {e}")
                logger.error(f"Failed to initialize Groq client: {e}")
                self.client = None
        else:
            print(f"[DEBUG GROQ INIT] ❌ Skipping Groq client creation - GROQ_AVAILABLE: {GROQ_AVAILABLE}, API key: {bool(self.api_key)}")
            logger.warning("Groq not available - missing dependency or API key")
    
    def is_available(self) -> bool:
        """Check if Groq AI is available for evaluation"""
        return self.client is not None
    
    def generate_response(self, prompt_string: str, system_message: str = None) -> str:
        """
        Generate a simple text response using Groq API
        
        Args:
            prompt_string: The prompt to send to the AI
            system_message: Optional system message to set context
            
        Returns:
            Generated text response or empty string if failed
        """
        if not self.is_available():
            return ""
        
        try:
            system_content = system_message or "You are a helpful AI tutor that creates engaging programming projects for young learners."
            
            completion = self.client.chat.completions.create(
                model=AI_CONFIG["cloud"]["groq_model"],
                messages=[
                    {
                        "role": "system", 
                        "content": system_content
                    },
                    {
                        "role": "user",
                        "content": prompt_string
                    }
                ],
                max_tokens=AI_CONFIG["cloud"]["max_tokens"],
                temperature=AI_CONFIG["cloud"]["temperature"],
            )
            
            response_text = completion.choices[0].message.content
            logger.info("Groq response generated successfully")
            return response_text or ""
            
        except Exception as e:
            logger.error(f"Groq API call failed: {e}")
            return ""
    
    def generate_report_from_prompt(self, prompt_string: str) -> Dict[str, Any]:
        """
        Generate evaluation report from prompt using Groq API
        
        Args:
            prompt_string: Formatted prompt for evaluation
            
        Returns:
            Dictionary with evaluation results
        """
        if not self.is_available():
            return {"error": "Groq client not available"}
        
        try:
            completion = self.client.chat.completions.create(
                model=AI_CONFIG["cloud"]["groq_model"],
                messages=[
                    {
                        "role": "system", 
                        "content": "You are an expert programming tutor and code reviewer. Provide detailed, constructive feedback on programming assignments."
                    },
                    {
                        "role": "user",
                        "content": prompt_string
                    }
                ],
                max_tokens=AI_CONFIG["cloud"]["max_tokens"],
                temperature=AI_CONFIG["cloud"]["temperature"],
            )
            
            response_text = completion.choices[0].message.content
            results = self._parse_evaluation_response(response_text)
            
            logger.info("Groq evaluation completed successfully")
            return results
            
        except Exception as e:
            logger.error(f"Groq API call failed: {e}")
            return {"error": f"API call failed: {str(e)}"}
    
    def run_ai_evaluation(
        self, 
        question_data: Dict[str, Any], 
        correct_answer_data: Dict[str, Any], 
        user_answer: Dict[str, str], 
        marks: Optional[int] = None
    ) -> Optional[Tuple[Dict[str, Any], str]]:
        """
        Main evaluation function for programming problems using Groq
        
        Args:
            question_data: Programming question details
            correct_answer_data: Expected solution and test cases
            user_answer: Student's code submission
            marks: Optional maximum marks
            
        Returns:
            Tuple of (results_dict, raw_response) or None if evaluation fails
        """
        if not self.is_available():
            logger.warning("Groq client not available")
            return None
        
        try:
            # Build programming-specific prompt
            prompt = get_programming_prompt(
                question_data, 
                correct_answer_data, 
                user_answer, 
                marks
            )
            
            # Generate evaluation using Groq
            results = self.generate_report_from_prompt(prompt)
            
            if "error" in results:
                logger.error(f"Groq evaluation error: {results['error']}")
                return None
            
            # Extract raw response for debugging
            raw_response = str(results)
            
            return results, raw_response
            
        except Exception as e:
            logger.error(f"Groq evaluation failed: {e}")
            return None
    
    def _parse_evaluation_response(self, response: str) -> Dict[str, Any]:
        """
        Parse the Groq response into structured evaluation results
        """
        results = {
            "Grade": "0/10",
            "Code Quality": "Fair",
            "Correctness": "Incorrect",
            "Efficiency": "Fair", 
            "Rationale": "Unable to parse evaluation",
            "Study Topics": "Review basic programming concepts",
            "Suggested Improvements": "Please review the solution"
        }
        
        try:
            # Try to parse as JSON first
            if response.strip().startswith('{'):
                json_data = json.loads(response)
                results.update(json_data)
                return results
            
            # Otherwise parse line by line
            lines = response.strip().split('\n')
            
            for line in lines:
                line = line.strip()
                if ':' in line and not line.startswith('#'):
                    key, value = line.split(':', 1)
                    key = key.strip()
                    value = value.strip()
                    
                    if key in results:
                        results[key] = value
                    elif key.lower().replace(' ', '_') in [k.lower().replace(' ', '_') for k in results.keys()]:
                        # Handle case variations
                        for result_key in results.keys():
                            if key.lower().replace(' ', '_') == result_key.lower().replace(' ', '_'):
                                results[result_key] = value
                                break
            
            logger.debug(f"Parsed Groq evaluation results: {results}")
            return results
            
        except Exception as e:
            logger.error(f"Failed to parse Groq response: {e}")
            results["Rationale"] = f"Response parsing failed: {response[:200]}..."
            return results
    
    def analyze_code_complexity(self, code: str, language: str) -> Dict[str, Any]:
        """
        Analyze code complexity using Groq AI
        
        Args:
            code: Source code to analyze
            language: Programming language
            
        Returns:
            Dictionary with complexity analysis
        """
        if not self.is_available():
            return {"error": "Groq client not available"}
        
        try:
            prompt = f"""
Analyze the complexity and quality of this {language} code:

```{language}
{code}
```

Provide analysis in JSON format:
{{
    "time_complexity": "O(n)",
    "space_complexity": "O(1)",
    "readability_score": 8,
    "maintainability": "Good",
    "code_smells": ["List any issues"],
    "optimization_suggestions": ["Specific improvements"],
    "design_patterns": ["Patterns used or suggested"]
}}
"""
            
            completion = self.client.chat.completions.create(
                model=AI_CONFIG["cloud"]["groq_model"],
                messages=[
                    {
                        "role": "system",
                        "content": "You are a senior software engineer specializing in code review and complexity analysis."
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                max_tokens=1024,
                temperature=0.1,
            )
            
            response_text = completion.choices[0].message.content
            
            # Try to parse as JSON
            try:
                return json.loads(response_text)
            except json.JSONDecodeError:
                # Fallback to text parsing
                return {"analysis": response_text, "format": "text"}
                
        except Exception as e:
            logger.error(f"Code complexity analysis failed: {e}")
            return {"error": f"Analysis failed: {str(e)}"}
    
    def suggest_test_cases(self, code: str, language: str, problem_description: str) -> Dict[str, Any]:
        """
        Generate test cases for given code using Groq AI
        
        Args:
            code: Source code
            language: Programming language
            problem_description: Description of the problem being solved
            
        Returns:
            Dictionary with suggested test cases
        """
        if not self.is_available():
            return {"error": "Groq client not available"}
        
        try:
            prompt = f"""
Given this {language} code that solves: {problem_description}

```{language}
{code}
```

Generate comprehensive test cases in JSON format:
{{
    "basic_tests": [
        {{"input": "example", "expected": "result", "description": "Basic functionality"}}
    ],
    "edge_cases": [
        {{"input": "edge", "expected": "result", "description": "Edge case scenario"}}  
    ],
    "stress_tests": [
        {{"input": "large", "expected": "result", "description": "Performance test"}}
    ]
}}
"""
            
            completion = self.client.chat.completions.create(
                model=AI_CONFIG["cloud"]["groq_model"],
                messages=[
                    {
                        "role": "system",
                        "content": "You are a test automation engineer creating comprehensive test suites."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=1500,
                temperature=0.2,
            )
            
            response_text = completion.choices[0].message.content
            
            try:
                return json.loads(response_text)
            except json.JSONDecodeError:
                return {"test_cases": response_text, "format": "text"}
                
        except Exception as e:
            logger.error(f"Test case generation failed: {e}")
            return {"error": f"Test generation failed: {str(e)}"} 