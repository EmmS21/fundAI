"""
test_connection.py

Purpose: Test database connection to Supabase PostgreSQL instance
"""
from app.db.database import engine, Base
from app.core.config import settings
from sqlalchemy import text

def test_connection():
    print("🔄 Testing database connection...")
    print(f"🔗 Database URL: {settings.compute_db_url()}")
    
    try:
        # Test connection
        with engine.connect() as connection:
            result = connection.execute(text("SELECT version();"))
            version = result.scalar()
            print("✅ Successfully connected to database!")
            print(f"📊 PostgreSQL version: {version}")
            
        # Test table creation
        Base.metadata.create_all(bind=engine)
        print("✅ Successfully created database tables!")
        
    except Exception as e:
        print(f"❌ Connection failed: {str(e)}")

if __name__ == "__main__":
    test_connection()