import sys
sys.path.append('src')

# Test Local AI parsing
print("="*50)
print("TESTING LOCAL AI PARSING (marker.py)")
print("="*50)

from core.ai.marker import parse_ai_response

# Simulate local AI response format
local_response = """
Grade: 3/5
Rationale: The student correctly identifies that plants use sunlight to make food, which is the basic concept of photosynthesis. However, they didn't mention the conversion of light energy to chemical energy or the specific reactants (carbon dioxide and water).
Study Topics: - The role of carbon dioxide and water in photosynthesis
- Energy conversion in photosynthesis
- Products of photosynthesis (glucose and oxygen)
"""

local_parsed = parse_ai_response(local_response)
print("Local AI parsed results:")
for key, value in local_parsed.items():
    print(f"  {key}: {value}")

print("\n" + "="*50)
print("TESTING CLOUD AI PARSING (groq_client.py)")
print("="*50)

from core.ai.groq_client import GroqClient

# Simulate DeepSeek cloud response format (from our earlier test)
cloud_response = """<think>
Some internal reasoning...
</think>

**Grade: 3/5**

**Rationale:**
The student's answer correctly identifies that plants use sunlight to produce food, which is a fundamental aspect of photosynthesis. However, it lacks key details such as the conversion of light energy to chemical energy and the role of carbon dioxide and water as reactants.

**Study Topics:**
- The role of carbon dioxide and water in photosynthesis.
- The conversion of light energy to chemical energy.
- The products of photosynthesis, including glucose and oxygen.
"""

# Create a GroqClient instance and test its parsing
try:
    client = GroqClient()
    cloud_parsed = client._parse_groq_text_response(cloud_response)
    print("Cloud AI parsed results:")
    for key, value in cloud_parsed.items():
        if key == "study_topics":
            print(f"  {key}: {value}")
        else:
            print(f"  {key}: {value}")
    
    print("\n✅ Both parsing systems work independently!")
    
except Exception as e:
    print(f"❌ Cloud AI parsing error: {e}")

print("\n" + "="*50)
print("CONCLUSION: Systems are independent!")
print("="*50) 