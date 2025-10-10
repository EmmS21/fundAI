import bcrypt

# Test your suspected password
password = "Sanctuary21"
stored_hash = "$2b$12$gsXcUFa2t3VWMBQZs/CswujBWBrxhqbNUlXgpf6X71fiHiNnbAUpC"

if bcrypt.checkpw(password.encode('utf-8'), stored_hash.encode('utf-8')):
    print("✅ Password is correct!")
else:
    print("❌ Password is wrong")