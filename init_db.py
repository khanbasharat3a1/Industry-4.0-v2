"""
Database Initialization Script
Run this once to create all database tables
"""

import os
from sqlalchemy import create_engine
from database.models import Base
from config.settings import config

def init_database():
    """Initialize database with all tables"""
    print("🔧 Initializing database...")
    
    # Create data directory if it doesn't exist
    os.makedirs('data', exist_ok=True)
    
    # Create database engine
    engine = create_engine(config.database.url, echo=True)
    
    # Create all tables
    Base.metadata.create_all(engine)
    
    print("✅ Database tables created successfully!")
    print("📊 Tables created:")
    
    # List created tables
    from sqlalchemy import inspect
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    for table in tables:
        print(f"   - {table}")

if __name__ == "__main__":
    init_database()
