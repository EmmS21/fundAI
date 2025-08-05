import sqlite3
from pathlib import Path
import json

class Database:
    def __init__(self):
        self.db_path = Path("data/engineer.db")
        self.db_path.parent.mkdir(exist_ok=True)
        self.connection = None
        self._connect()
        self._create_tables()
    
    def _connect(self):
        try:
            self.connection = sqlite3.connect(str(self.db_path))
            self.connection.row_factory = sqlite3.Row
        except Exception:
            self.connection = None
    
    def _create_tables(self):
        if not self.connection:
            return
        
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    age INTEGER,
                    overall_score REAL,
                    section_scores TEXT,
                    profile_picture TEXT,
                    assessment_completed_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            self.connection.commit()
        except Exception:
            pass
    
    def is_connected(self):
        return self.connection is not None
    
    def create_user(self, username, age):
        if not self.connection:
            return None
        
        try:
            cursor = self.connection.cursor()
            cursor.execute("INSERT INTO users (username, age) VALUES (?, ?)", (username, age))
            self.connection.commit()
            return cursor.lastrowid
        except Exception:
            return None
    
    def get_user(self, username):
        if not self.connection:
            return None
        
        try:
            cursor = self.connection.cursor()
            cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
            return cursor.fetchone()
        except Exception:
            return None
    
    def store_assessment_results(self, user_id, results):
        if not self.connection:
            return False
        
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                UPDATE users SET 
                    overall_score = ?,
                    section_scores = ?,
                    assessment_completed_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (
                results['overall_score'],
                json.dumps(results['section_scores']),
                user_id
            ))
            self.connection.commit()
            return True
        except Exception:
            return False
    
    def update_user_profile(self, user_id, username=None, age=None, profile_picture=None):
        if not self.connection:
            return False
        
        try:
            cursor = self.connection.cursor()
            
            # Build dynamic query based on provided parameters
            updates = []
            params = []
            
            if username:
                updates.append("username = ?")
                params.append(username)
            if age:
                updates.append("age = ?")
                params.append(age)
            if profile_picture is not None:  # Allow empty string to clear picture
                updates.append("profile_picture = ?")
                params.append(profile_picture)
            
            if updates:
                params.append(user_id)
                cursor.execute(f"""
                    UPDATE users SET {', '.join(updates)} WHERE id = ?
                """, params)
                self.connection.commit()
            
            return True
        except Exception:
            return False
    
    def get_user_by_id(self, user_id):
        if not self.connection:
            return None
        
        try:
            cursor = self.connection.cursor()
            cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
            row = cursor.fetchone()
            
            if row:
                user_data = dict(row)
                if user_data['section_scores']:
                    user_data['section_scores'] = json.loads(user_data['section_scores'])
                return user_data
            return None
        except Exception:
            return None 