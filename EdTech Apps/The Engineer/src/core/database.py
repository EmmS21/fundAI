import sqlite3
from pathlib import Path
import json
from utils.hardware_identifier import HardwareIdentifier


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
                    hardware_id TEXT UNIQUE,
                    assessment_completed_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_skills (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER REFERENCES users(id),
                    hardware_id TEXT NOT NULL,
                    skill_name TEXT NOT NULL,
                    current_score REAL DEFAULT 0.0,
                    total_evaluations INTEGER DEFAULT 0,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    synced_to_cloud BOOLEAN DEFAULT FALSE,
                    UNIQUE(user_id, skill_name)
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS github_projects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER REFERENCES users(id),
                    hardware_id TEXT NOT NULL,
                    repo_url TEXT NOT NULL,
                    branch_name TEXT DEFAULT 'main',
                    project_name TEXT NOT NULL,
                    requirements_checklist TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP,
                    synced_to_cloud BOOLEAN DEFAULT FALSE
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS commit_evaluations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER REFERENCES github_projects(id),
                    commit_hash TEXT NOT NULL,
                    commit_message TEXT,
                    files_changed TEXT,
                    evaluation_results TEXT,
                    ai_feedback TEXT,
                    evaluated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    synced_to_cloud BOOLEAN DEFAULT FALSE,
                    UNIQUE(project_id, commit_hash)
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
            hardware_id = HardwareIdentifier.get_hardware_id()
            cursor = self.connection.cursor()
            cursor.execute("INSERT INTO users (username, age, hardware_id) VALUES (?, ?, ?)", 
                         (username, age, hardware_id))
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
            
            updates = []
            params = []
            
            if username:
                updates.append("username = ?")
                params.append(username)
            if age:
                updates.append("age = ?")
                params.append(age)
            if profile_picture is not None:
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
    
    def get_user_skills(self, user_id):
        if not self.connection:
            return []
        
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                SELECT skill_name, current_score, total_evaluations, last_updated 
                FROM user_skills WHERE user_id = ? 
                ORDER BY current_score DESC
            """, (user_id,))
            return cursor.fetchall()
        except Exception:
            return []
    
    def update_skill_score(self, user_id, skill_name, new_score):
        if not self.connection:
            return False
        
        try:
            hardware_id = HardwareIdentifier.get_hardware_id()
            cursor = self.connection.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO user_skills 
                (user_id, hardware_id, skill_name, current_score, total_evaluations, last_updated)
                VALUES (?, ?, ?, ?, 
                    COALESCE((SELECT total_evaluations FROM user_skills 
                             WHERE user_id = ? AND skill_name = ?), 0) + 1,
                    CURRENT_TIMESTAMP)
            """, (user_id, hardware_id, skill_name, new_score, user_id, skill_name))
            
            self.connection.commit()
            return True
        except Exception:
            return False
    
    def create_github_project(self, user_id, repo_url, project_name, branch_name='main'):
        if not self.connection:
            return None
        
        try:
            hardware_id = HardwareIdentifier.get_hardware_id()
            cursor = self.connection.cursor()
            cursor.execute("""
                INSERT INTO github_projects (user_id, hardware_id, repo_url, project_name, branch_name)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, hardware_id, repo_url, project_name, branch_name))
            self.connection.commit()
            return cursor.lastrowid
        except Exception:
            return None
    
    def add_commit_evaluation(self, project_id, commit_hash, commit_message, evaluation_results, ai_feedback):
        if not self.connection:
            return False
        
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO commit_evaluations 
                (project_id, commit_hash, commit_message, evaluation_results, ai_feedback)
                VALUES (?, ?, ?, ?, ?)
            """, (project_id, commit_hash, commit_message, evaluation_results, ai_feedback))
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