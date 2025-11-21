"""
Hardware Identifier
Generates persistent device UUID for user identification across all fundAI AI Tutors

IMPORTANT: This uses a SHARED hardware ID file (~/.ai_tutors/hardware_id.json)
that is used by ALL fundAI AI Tutor applications (The Engineer, The Examiner, MoneyWise Academy).

This ensures:
- Same user is recognized across all AI Tutor apps
- Unified subscription/license management
- Consistent user experience across the fundAI ecosystem
"""

import json
import os
import uuid


class HardwareIdentifier:
    """
    Manages hardware identification using SHARED storage across all AI Tutors
    
    Storage Location: ~/.ai_tutors/hardware_id.json (SHARED)
    This file is used by:
    - The Engineer
    - The Examiner  
    - MoneyWise Academy
    - Future AI Tutor apps
    """
    
    @classmethod
    def get_hardware_id(cls) -> str:
        """Get or create hardware ID"""
        return cls.get_or_create_hardware_id()
    
    @classmethod
    def get_hardware_id_file_path(cls) -> str:
        """
        Get path to SHARED hardware ID file
        
        Returns:
            str: Path to ~/.ai_tutors/hardware_id.json
        """
        home_dir = os.path.expanduser("~")
        ai_tutors_dir = os.path.join(home_dir, ".ai_tutors")
        os.makedirs(ai_tutors_dir, exist_ok=True)
        return os.path.join(ai_tutors_dir, "hardware_id.json")
    
    @classmethod
    def get_or_create_hardware_id(cls) -> str:
        """
        Get existing hardware ID from shared file or create new one
        
        Returns:
            str: Hardware ID (UUID format)
        
        Note:
            - Reads from ~/.ai_tutors/hardware_id.json
            - If file doesn't exist, generates new UUID and saves it
            - This ID is shared across ALL fundAI AI Tutor applications
        """
        file_path = cls.get_hardware_id_file_path()
        
        # Try to read existing ID
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    if data.get('hardware_id'):
                        return data['hardware_id']
            except (json.JSONDecodeError, IOError):
                # If file is corrupted, continue to generate new ID
                pass
        
        # Generate new random UUID
        hardware_id = str(uuid.uuid4())
        
        # Save to shared file
        try:
            with open(file_path, 'w') as f:
                json.dump({'hardware_id': hardware_id}, f)
        except IOError:
            # If we can't save, still return the ID
            # (It won't persist, but app can still function)
            pass
        
        return hardware_id


# Convenience functions for backward compatibility
def get_device_uuid() -> str:
    """Get hardware ID (alias for consistency)"""
    return HardwareIdentifier.get_hardware_id()


def get_hardware_id() -> str:
    """Get hardware ID"""
    return HardwareIdentifier.get_hardware_id()


if __name__ == "__main__":
    # Test hardware identification
    print("Hardware Identifier Test")
    print("=" * 50)
    
    file_path = HardwareIdentifier.get_hardware_id_file_path()
    print(f"Storage location: {file_path}")
    
    hardware_id = HardwareIdentifier.get_hardware_id()
    print(f"Hardware ID: {hardware_id}")
    
    # Verify it persists
    hardware_id_2 = HardwareIdentifier.get_hardware_id()
    print(f"Second call: {hardware_id_2}")
    print(f"IDs match: {hardware_id == hardware_id_2}")
    
    print("\nNote: This ID is SHARED across all fundAI AI Tutor apps")
