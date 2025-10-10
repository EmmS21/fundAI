import sys
sys.path.append('src')
from core.ai.groq_client import GroqClient

# Test various response formats
test_cases = [
    'DeepSeek format with **',
    'Simple format', 
    'Alternative format',
    'Unstructured format'
]

responses = [
    '''<think>reasoning</think>

**Grade: 3/5**

**Rationale:**
Student shows basic understanding but lacks detail.

**Study Topics:**
- Topic 1
- Topic 2''',
    
    '''Grade: 4/5
Rationale: Good answer with some minor gaps.
Study Topics: Review cellular processes, photosynthesis basics''',
    
    '''Score: 2 out of 5
Explanation: The student's response demonstrates limited understanding.
Areas for Improvement:
• Cell structure
• Energy conversion''',

    '''The student got 1/5 marks. They need to work on understanding basic concepts.
They should focus on studying membrane transport and enzyme function.'''
]

client = GroqClient()
print("Testing Robust Parser with Multiple Formats")
print("=" * 50)

for i, (name, response) in enumerate(zip(test_cases, responses)):
    print(f'\n--- TEST {i+1}: {name} ---')
    result = client._parse_groq_text_response(response)
    print(f'Grade: {result["grade"]}')
    print(f'Rationale: {result["rationale"][:100]}...' if len(result["rationale"]) > 100 else f'Rationale: {result["rationale"]}')
    print(f'Study Topics: {result["study_topics"].get("raw", "N/A")[:100]}...' if len(str(result["study_topics"].get("raw", ""))) > 100 else f'Study Topics: {result["study_topics"].get("raw", "N/A")}')

print("\n" + "=" * 50)
print("✅ Robust parser test completed!") 