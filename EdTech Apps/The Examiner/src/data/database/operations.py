from sqlalchemy.orm import Session
from .models import User
from src.utils.db import get_db_session

class UserOperations:
    @staticmethod
    def create_user(user_data: dict):
        with get_db_session() as session:
            user = User(**user_data)
            session.add(user)
            session.commit()
            return user
