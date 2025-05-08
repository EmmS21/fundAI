from cryptography.fernet import Fernet

# --- Your details ---
GROQ_API_KEY_TO_ENCRYPT = "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"
# --------------------

# 1. Generate a new Fernet key (this will be your MASTER_KEY for decryption)
#    Keep this key safe if you ever need to re-encrypt, but it will also be embedded in your app.
fern_key = Fernet.generate_key()

# 2. Create a Fernet cipher instance with your key
cipher = Fernet(fern_key)

# 3. Encrypt your Groq API key
encrypted_groq_api_key = cipher.encrypt(GROQ_API_KEY_TO_ENCRYPT.encode('utf-8'))

print("--- Copy these values into your src/config/secrets.py ---")
print(f"EMBEDDED_FERNET_KEY = {fern_key}")
print(f"ENCRYPTED_GROQ_API_KEY = {encrypted_groq_api_key}")
print("-----------------------------------------------------------")
print("\nMake sure to add 'cryptography' to your project's dependencies (e.g., requirements.txt).")
