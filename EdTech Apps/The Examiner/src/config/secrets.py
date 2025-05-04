_GROQ_API_KEY_PART1 = "gsk_Ot12Zktra1rveyt2jVWCW"
_GROQ_API_KEY_PART2 = "Gdyb3FY5cMQu6a4BfjEYyXvJ"
_GROQ_API_KEY_PART3 = "gNntAf8"

def get_groq_api_key():
    """Retrieves the assembled Groq API key."""
    return f"{_GROQ_API_KEY_PART1}{_GROQ_API_KEY_PART2}{_GROQ_API_KEY_PART3}"

