"""
Database Models
SQLAlchemy models for local SQLite database

NOTE: Models are intentionally minimal/placeholder.
See tasks.md Task 2.1 for database schema design discussion.
"""

from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

# TODO: Design and implement database models (see tasks.md Task 2.1)
# Models to consider:
# - User: Profile, device UUID, subscription
# - LearningProgress: Track progress on concepts
# - FinancialConcept: Financial literacy topics
# - Activity: User activity log
# - Achievement: Badges and gamification
# - ConversationHistory: AI chat history
# - QuizAttempt: Quiz results
# - SyncQueue: Offline sync queue

