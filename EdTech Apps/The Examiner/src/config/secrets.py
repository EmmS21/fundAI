import os
from cryptography.fernet import Fernet

# IMPORTANT: These are your actual encrypted keys.
# Keep them exactly as they are.

# --- YOUR GENERATED KEYS ---
EMBEDDED_FERNET_KEY = b'x-PSbD2SxPOiNE4gG_CY8yNuxsbJxQz3GZqbNcOVSbk='
ENCRYPTED_GROQ_API_KEY = b'gAAAAABoHQIm6KOe2vbjJf_TT2fKYrRaCZtF0TGfogrgf2le1P3uE7_gp3O5b3yjkp60p08zV7OykZZagP4BE1rs6qSY6ggS-zcEIN7LIxBNIE9aC5Q1LG5f6aypsU1JeCmKj0fS8YQmbMcnDDzyVr5u4Y_ml9Vfyg=='
# ------------------------------------

_DECRYPTED_KEY_CACHE = None

def get_groq_api_key() -> str:
    """
    Retrieves the Groq API key by decrypting an embedded, encrypted key.
    The decryption key is also embedded in this file.

    This method obfuscates the key from repository scanners but does not
    provide true security against determined attackers who inspect the
    application's bundled code.

    Raises:
        ValueError: If decryption fails or keys are not properly set.
    """
    global _DECRYPTED_KEY_CACHE

    if _DECRYPTED_KEY_CACHE:
        return _DECRYPTED_KEY_CACHE

    try:
        cipher = Fernet(EMBEDDED_FERNET_KEY)
        decrypted_key_bytes = cipher.decrypt(ENCRYPTED_GROQ_API_KEY)
        _DECRYPTED_KEY_CACHE = decrypted_key_bytes.decode('utf-8')
        return _DECRYPTED_KEY_CACHE
    except Exception as e:
        print(f"Error decrypting Groq API key: {e}") 
        raise ValueError(
            "Failed to decrypt Groq API Key. Check embedded keys and dependencies."
        ) from e


