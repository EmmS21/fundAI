from sqlalchemy.orm import Session
from .models import User
from src.utils.db import get_db_session
from src.utils.hardware_identifier import HardwareIdentifier
from src.core.queue_manager import QueueManager, QueuePriority

class UserOperations:
    @staticmethod
    def create_user(user_data: dict):
        # Get hardware ID
        _, _, hardware_id = HardwareIdentifier.get_hardware_id()
        
        # Add hardware_id to user_data
        user_data['hardware_id'] = hardware_id
        
        with get_db_session() as session:
            # Check if user already exists
            existing_user = session.query(User).filter_by(hardware_id=hardware_id).first()
            
            if existing_user:
                # Update existing user
                for key, value in user_data.items():
                    setattr(existing_user, key, value)
                user = existing_user
            else:
                # Create new user
                user = User(**user_data)
                session.add(user)
            
            session.commit()
            
            # Add to sync queue (will handle deduplication)
            queue_manager = QueueManager()
            queue_manager.add_to_queue(
                data={
                    'type': 'user_create',
                    'hardware_id': hardware_id,
                    'user_data': user_data
                },
                item_type='user',
                priority=QueuePriority.HIGH
            )
            
            return user
