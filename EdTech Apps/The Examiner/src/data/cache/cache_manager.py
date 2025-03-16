from src.data.database.operations import PaperCacheOperations, UserOperations
from src.utils.db import get_db_session
from typing import Any, List, Dict, Optional
import threading
import time
import os
import json
import logging
import sqlite3
from datetime import datetime

logger = logging.getLogger(__name__)

class CacheManager:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(CacheManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self._initialized = True
        self._running = False
        self._thread = None
        self._check_interval = 3600  # Check every hour
        self._papers_per_subject = 5  # Target papers per subject/level
        self._max_completed_papers = 10  # Max completed papers to keep
        self.db_path = "student_profile.db"
        self._ensure_tables()
        
    def start(self):
        """Start the cache manager background thread"""
        if self._running:
            return
            
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        
    def stop(self):
        """Stop the cache manager background thread"""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
            
    def _run(self):
        """Main loop for cache management"""
        while self._running:
            try:
                # Get current user
                user = UserOperations.get_current_user()
                if user:
                    # Clean up cache if needed
                    PaperCacheOperations.cleanup_cache()
                    
                    # Invalidate completed papers
                    PaperCacheOperations.invalidate_completed_papers(
                        user.id, 
                        self._max_completed_papers
                    )
                    
                    # Check for papers to download
                    papers_to_download = PaperCacheOperations.get_papers_to_download(
                        user.id,
                        self._papers_per_subject
                    )
                    
                    # Queue papers for download (in a real implementation, this would
                    # connect to a download service or API)
                    if papers_to_download:
                        self._queue_paper_downloads(papers_to_download)
                
            except Exception as e:
                print(f"Error in cache manager: {e}")
                
            # Sleep until next check
            time.sleep(self._check_interval)
    
    def _queue_paper_downloads(self, papers: List[Dict]):
        """Queue papers for download (placeholder)"""
        # In a real implementation, this would connect to a download service
        print(f"Queueing {len(papers)} papers for download:")
        for paper in papers:
            print(f"  - {paper['subject_name']} ({paper['level']}) Year: {paper['year']}")
    
    def mark_paper_completed(self, user_subject_id: int, year: int) -> bool:
        """Mark a paper as completed and trigger cache check"""
        result = PaperCacheOperations.mark_completed(user_subject_id, year)
        
        # If we successfully marked as completed, check if we need to invalidate
        if result:
            # Get user ID from user_subject_id
            with get_db_session() as session:
                from src.data.database.models import UserSubject
                user_subject = session.query(UserSubject).get(user_subject_id)
                if user_subject:
                    PaperCacheOperations.invalidate_completed_papers(
                        user_subject.user_id,
                        self._max_completed_papers
                    )
        
        return result
    
    def force_cache_check(self, user_id: int) -> Dict:
        """Force an immediate cache check"""
        result = {
            'invalidated': [],
            'to_download': []
        }
        
        # Invalidate completed papers
        result['invalidated'] = PaperCacheOperations.invalidate_completed_papers(
            user_id,
            self._max_completed_papers
        )
        
        # Check for papers to download
        result['to_download'] = PaperCacheOperations.get_papers_to_download(
            user_id,
            self._papers_per_subject
        )
        
        return result

    def _ensure_tables(self):
        """Ensure the necessary tables exist in the database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create questions table if it doesn't exist
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS cached_questions (
                question_id TEXT PRIMARY KEY,
                paper_id TEXT NOT NULL,
                paper_year INTEGER NOT NULL,
                paper_number TEXT NOT NULL,
                subject TEXT NOT NULL,
                level TEXT NOT NULL,
                topic TEXT,
                content TEXT NOT NULL,
                marks INTEGER NOT NULL,
                cached_at TIMESTAMP NOT NULL,
                last_accessed TIMESTAMP NOT NULL
            )
            ''')
            
            # Create question_assets table for images, tables, etc.
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS question_assets (
                asset_id TEXT PRIMARY KEY,
                question_id TEXT NOT NULL,
                asset_type TEXT NOT NULL,
                content BLOB NOT NULL,
                cached_at TIMESTAMP NOT NULL,
                FOREIGN KEY (question_id) REFERENCES cached_questions (question_id) ON DELETE CASCADE
            )
            ''')
            
            # Create paper_metadata table to track which papers we have
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS paper_metadata (
                paper_id TEXT PRIMARY KEY,
                paper_year INTEGER NOT NULL,
                paper_number TEXT NOT NULL,
                subject TEXT NOT NULL,
                level TEXT NOT NULL,
                total_questions INTEGER NOT NULL,
                cached_questions INTEGER NOT NULL DEFAULT 0,
                last_updated TIMESTAMP NOT NULL
            )
            ''')
            
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Error ensuring tables: {e}")
    
    def save_question(self, question_data: Dict[str, Any], assets: List[Dict[str, Any]] = None) -> bool:
        """
        Save a question and its assets to the cache
        
        Args:
            question_data: Dictionary containing question data
            assets: List of dictionaries containing asset data (images, tables, etc.)
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            now = datetime.now().isoformat()
            
            # Insert or replace question
            cursor.execute('''
            INSERT OR REPLACE INTO cached_questions 
            (question_id, paper_id, paper_year, paper_number, subject, level, topic, content, marks, cached_at, last_accessed)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                question_data['question_id'],
                question_data['paper_id'],
                question_data['paper_year'],
                question_data['paper_number'],
                question_data['subject'],
                question_data['level'],
                question_data.get('topic'),
                json.dumps(question_data['content']),
                question_data['marks'],
                now,
                now
            ))
            
            # Update paper metadata
            cursor.execute('''
            INSERT OR IGNORE INTO paper_metadata
            (paper_id, paper_year, paper_number, subject, level, total_questions, cached_questions, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, 0, ?)
            ''', (
                question_data['paper_id'],
                question_data['paper_year'],
                question_data['paper_number'],
                question_data['subject'],
                question_data['level'],
                question_data.get('total_questions', 0),
                now
            ))
            
            # Increment cached_questions count for this paper
            cursor.execute('''
            UPDATE paper_metadata
            SET cached_questions = cached_questions + 1,
                last_updated = ?
            WHERE paper_id = ? AND cached_questions < total_questions
            ''', (now, question_data['paper_id']))
            
            # Save assets if provided
            if assets:
                for asset in assets:
                    cursor.execute('''
                    INSERT OR REPLACE INTO question_assets
                    (asset_id, question_id, asset_type, content, cached_at)
                    VALUES (?, ?, ?, ?, ?)
                    ''', (
                        asset['asset_id'],
                        question_data['question_id'],
                        asset['asset_type'],
                        asset['content'],
                        now
                    ))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            logger.error(f"Error saving question: {e}")
            return False
    
    def get_question(self, question_id: str) -> Optional[Dict[str, Any]]:
        """Get a question and its assets from the cache"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Get question
            cursor.execute('''
            SELECT * FROM cached_questions
            WHERE question_id = ?
            ''', (question_id,))
            
            row = cursor.fetchone()
            if not row:
                conn.close()
                return None
                
            # Update last_accessed
            now = datetime.now().isoformat()
            cursor.execute('''
            UPDATE cached_questions
            SET last_accessed = ?
            WHERE question_id = ?
            ''', (now, question_id))
            
            # Get assets
            cursor.execute('''
            SELECT * FROM question_assets
            WHERE question_id = ?
            ''', (question_id,))
            
            assets = []
            for asset_row in cursor.fetchall():
                assets.append(dict(asset_row))
            
            # Convert row to dict and parse content
            question = dict(row)
            question['content'] = json.loads(question['content'])
            question['assets'] = assets
            
            conn.commit()
            conn.close()
            return question
            
        except Exception as e:
            logger.error(f"Error getting question: {e}")
            return None
    
    def get_paper_questions(self, paper_id: str) -> List[Dict[str, Any]]:
        """Get all questions for a specific paper"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Get all questions for this paper
            cursor.execute('''
            SELECT question_id FROM cached_questions
            WHERE paper_id = ?
            ''', (paper_id,))
            
            questions = []
            for row in cursor.fetchall():
                question = self.get_question(row['question_id'])
                if question:
                    questions.append(question)
            
            conn.close()
            return questions
            
        except Exception as e:
            logger.error(f"Error getting paper questions: {e}")
            return []
    
    def get_papers_needing_questions(self, subject: str, level: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Get papers that need more questions cached
        
        Args:
            subject: Subject to filter by
            level: Level to filter by
            limit: Maximum number of papers to return
            
        Returns:
            List of paper metadata dictionaries
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
            SELECT * FROM paper_metadata
            WHERE subject = ? AND level = ? AND cached_questions < total_questions
            ORDER BY paper_year DESC, paper_number ASC
            LIMIT ?
            ''', (subject, level, limit))
            
            papers = [dict(row) for row in cursor.fetchall()]
            conn.close()
            return papers
            
        except Exception as e:
            logger.error(f"Error getting papers needing questions: {e}")
            return []
    
    def get_completion_status(self, subject: str, level: str) -> Dict[str, Any]:
        """Get completion status for a subject/level combination"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
            SELECT 
                COUNT(*) as total_papers,
                SUM(total_questions) as total_questions,
                SUM(cached_questions) as cached_questions,
                MAX(paper_year) as latest_year,
                MIN(paper_year) as earliest_year
            FROM paper_metadata
            WHERE subject = ? AND level = ?
            ''', (subject, level))
            
            row = cursor.fetchone()
            conn.close()
            
            if not row or row[0] == 0:
                return {
                    'total_papers': 0,
                    'total_questions': 0,
                    'cached_questions': 0,
                    'completion_percentage': 0,
                    'latest_year': None,
                    'earliest_year': None
                }
            
            total_papers, total_questions, cached_questions, latest_year, earliest_year = row
            
            completion_percentage = 0
            if total_questions > 0:
                completion_percentage = (cached_questions / total_questions) * 100
                
            return {
                'total_papers': total_papers,
                'total_questions': total_questions,
                'cached_questions': cached_questions,
                'completion_percentage': completion_percentage,
                'latest_year': latest_year,
                'earliest_year': earliest_year
            }
            
        except Exception as e:
            logger.error(f"Error getting completion status: {e}")
            return {
                'total_papers': 0,
                'total_questions': 0,
                'cached_questions': 0,
                'completion_percentage': 0,
                'latest_year': None,
                'earliest_year': None
            }
