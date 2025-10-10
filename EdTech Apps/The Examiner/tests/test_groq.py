import sys
sys.path.append('src')

from groq import Groq
from config.secrets import get_groq_api_key

try:
    print("Getting decrypted API key...")
    key = get_groq_api_key()
    print(f"Key format: {key[:10]}... (length: {len(key)})")
    
    print("Creating Groq client...")
    client = Groq(api_key=key)
    
    print("Attempting API call...")
    response = client.chat.completions.create(
        messages=[{"role": "user", "content": "Hello"}],
        model="llama3-8b-8192",
        max_tokens=10
    )
    
    print("✅ SUCCESS!")
    print("Response:", response.choices[0].message.content)
    
except Exception as e:
    print("❌ ERROR:", str(e))
    print("Error type:", type(e).__name__) 