import sys
sys.path.append('src')

from core.ai.groq_client import GroqClient

try:
    print("Initializing GroqClient...")
    client = GroqClient()
    
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
    
    # Let's see the raw response by calling the Groq API directly
    messages = [
        {"role": "system", "content": "You are an AI assistant. Process the user's request carefully."},
        {"role": "user", "content": test_prompt}
    ]
    
    chat_completion = client.client.chat.completions.create(
        messages=messages,
        model="deepseek-r1-distill-llama-70b",
        temperature=0.2,
        max_tokens=2048,
    )
    
    raw_response = chat_completion.choices[0].message.content
    print("="*50)
    print("RAW GROQ RESPONSE:")
    print("="*50)
    print(repr(raw_response))
    print("="*50)
    print("FORMATTED RESPONSE:")
    print("="*50)
    print(raw_response)
    print("="*50)
        
except Exception as e:
    print("❌ ERROR:", str(e))
    import traceback
    traceback.print_exc() 