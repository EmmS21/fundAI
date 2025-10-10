#!/usr/bin/env python3
"""
Simple script to update a user's password in the database.
Usage: python update_password.py
"""

import os
from getpass import getpass
from dotenv import load_dotenv
from supabase import create_client, Client
from passlib.context import CryptContext

# Load environment variables from .env file
load_dotenv()

# Initialize password hashing context (same as your app)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str) -> str:
    """Generate password hash using bcrypt."""
    return pwd_context.hash(password)

def update_user_password():
    """Update a user's password"""
    
    # Get Supabase credentials from environment
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    
    if not supabase_url or not supabase_key:
        print("❌ Error: SUPABASE_URL and SUPABASE_KEY must be set in .env file")
        return
    
    # Initialize Supabase client
    supabase: Client = create_client(supabase_url, supabase_key)
    
    # Get user input
    email = input("Enter user email: ").strip()
    if not email:
        print("Email is required!")
        return
    
    new_password = input("Enter new password: ")  # Changed from getpass to input to show password
    print(f"New password entered: {new_password}")
    if not new_password:
        print("Password is required!")
        return
    
    confirm_password = input("Confirm new password: ")  # Changed from getpass to input to show password
    print(f"Confirmed password: {confirm_password}")
    if new_password != confirm_password:
        print("Passwords don't match!")
        return
    
    try:
        # Check if user exists
        print(f"Checking if user {email} exists...")
        response = supabase.table('users').select('id, email').eq('email', email).execute()
        
        if not response.data:
            print(f"User with email {email} not found!")
            return
        
        user_id = response.data[0]['id']
        print(f"Found user: {email} (ID: {user_id})")
        
        # Get the current hashed password first
        print("Getting current password hash...")
        current_response = supabase.table('users').select('hashed_password').eq('email', email).execute()
        if current_response.data:
            old_password_hash = current_response.data[0]['hashed_password']
            print(f"Current hashed password: {old_password_hash}")
        else:
            print("Could not retrieve current password hash")
        
        # Hash the new password
        print("Hashing new password...")
        new_password_hash = get_password_hash(new_password)
        print(f"New hashed password: {new_password_hash}")
        
        # Update the password
        print("Updating password in database...")
        update_response = supabase.table('users').update({
            'hashed_password': new_password_hash
        }).eq('email', email).execute()
        
        if hasattr(update_response, 'error') and update_response.error:
            print(f"Error updating password: {update_response.error}")
            return
        
        if update_response.data:
            print(f"✅ Password updated successfully for {email}")
            
            # Verify the update by checking the hash again
            print("Verifying the update...")
            verify_response = supabase.table('users').select('hashed_password').eq('email', email).execute()
            if verify_response.data:
                updated_hash = verify_response.data[0]['hashed_password']
                print(f"Updated hashed password in database: {updated_hash}")
                if updated_hash == new_password_hash:
                    print("✅ Verification successful: Password hash matches!")
                else:
                    print("❌ Verification failed: Password hash doesn't match!")
                    print(f"Expected: {new_password_hash}")
                    print(f"Got:      {updated_hash}")
            else:
                print("❌ Could not verify update - failed to retrieve updated password")
        else:
            print("❌ No rows were updated. User might not exist.")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("=== Password Update Script ===")
    print("This script will update a user's password in the database.")
    print()
    
    update_user_password() 