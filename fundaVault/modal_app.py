from modal import Image, App, web_endpoint, Mount
import os

# Create Modal app (not Stub)
app = App("user-management-api")

# Include all necessary packages
image = (
    Image.debian_slim()
    .pip_install([
        # Core dependencies with compatible ranges
        "fastapi>=0.100.0,<0.110.0",    
        
        # Settings management
        "pydantic-settings>=2.0.0,<3.0.0",  
        "python-dotenv>=0.21.0,<0.22.0",
        "python-multipart>=0.0.6,<0.1.0",
        "email-validator>=2.0.0",

        # Database
        "aiosqlite>=0.17.0,<0.18.0",
        
        # Auth & Security
        "PyJWT>=2.6.0,<2.7.0",
        "passlib[bcrypt]>=1.7.4,<1.8.0",
        "python-jose[cryptography]>=3.3.0,<4.0.0"
    ])

)

@app.function(
    image=image,
    mounts=[
        Mount.from_local_dir(".", remote_path="/root/code"),
        Mount.from_local_file(".env", remote_path="/root/code/.env")        
    ]  
)
@web_endpoint()
async def api():
    import sys
    sys.path.append("/root/code")  # Add the root code directory to Python path
    
    # Debug prints
    print("Current directory:", os.getcwd())
    print("Directory contents:", os.listdir())
    
    # Import the pre-configured FastAPI app from main.py
    from app.main import app as fastapi_app
    
    # Print routes for debugging
    print("Available routes:")
    for route in fastapi_app.routes:
        print(f"Path: {route.path}, Methods: {route.methods}")
    
    return fastapi_app