import json
import os
import uuid

class HardwareIdentifier:
    @classmethod
    def get_hardware_id(cls) -> str:
        return cls.get_or_create_hardware_id()
    
    @classmethod
    def get_hardware_id_file_path(cls) -> str:
        home_dir = os.path.expanduser("~")
        ai_tutors_dir = os.path.join(home_dir, ".ai_tutors")
        os.makedirs(ai_tutors_dir, exist_ok=True)
        return os.path.join(ai_tutors_dir, "hardware_id.json")
    
    @classmethod
    def get_or_create_hardware_id(cls) -> str:
        file_path = cls.get_hardware_id_file_path()
        
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    if data.get('hardware_id'):
                        return data['hardware_id']
            except (json.JSONDecodeError, IOError):
                pass
        
        hardware_id = str(uuid.uuid4())
        
        try:
            with open(file_path, 'w') as f:
                json.dump({'hardware_id': hardware_id}, f)
        except IOError:
            pass
        
        return hardware_id 