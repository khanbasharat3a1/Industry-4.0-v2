"""
Database Configuration and Setup
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from config.settings import config

# Create database engine
engine = create_engine(
    config.database.url,
    echo=False,  # Set to True for SQL query logging
    pool_pre_ping=True,  # Verify connections before use
    pool_recycle=3600    # Recycle connections every hour
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for all models
Base = declarative_base()

def get_db_session():
    """Get database session with proper cleanup"""
    session = SessionLocal()
    try:
        return session
    except Exception:
        session.close()
        raise

def init_database():
    """Initialize database tables"""
    Base.metadata.create_all(bind=engine)
