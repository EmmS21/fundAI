import sys
sys.path.append('src')

from core.ai.groq_client import GroqClient

try:
    print("Initializing GroqClient...")
    client = GroqClient()
    print("✅ GroqClient initialized successfully!")
    
    # Test with a simple evaluation prompt
    test_prompt = """Please evaluate this student answer:

Question: What is photosynthesis?
Correct Answer: The process by which plants convert light energy into chemical energy using carbon dioxide and water.
Student Answer: Plants use sunlight to make food.

Please provide:
Grade: [score out of 5]
Rationale: [explanation of the grade]
Study Topics: [topics the student should focus on]"""
    
    print("Sending test prompt to Groq...")
    response = client.generate_report_from_prompt(test_prompt)
    
    if response and "error" not in response:
        print("✅ SUCCESS! Cloud AI Response:")
        print("Grade:", response.get("grade", "N/A"))
        print("Rationale:", response.get("rationale", "N/A"))
        print("Study Topics:", response.get("study_topics", {}).get("raw", "N/A"))
    else:
        print("❌ ERROR in response:")
        print(response)
        
except Exception as e:
    print("❌ ERROR:", str(e))
    print("Error type:", type(e).__name__) 