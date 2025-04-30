"""
Database module initialization
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

from backend.db.models import Base, WordCounter, VerdictCache, GameSession, GameStatistics

__all__ = ["Base", "WordCounter", "VerdictCache", "GameSession", "GameStatistics"]

# Load environment variables
load_dotenv()

# Database connection URL from environment variables
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./whatbeatsrock.db")

# Create SQLAlchemy engine
engine = create_engine(
    DATABASE_URL, 
    echo=False,
    pool_pre_ping=True,  # Enables connection pool "pre-ping" feature
    pool_size=10,        # Maximum number of connections to keep
    max_overflow=20      # Maximum allowed connections beyond pool_size
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Function to create database tables
def create_tables():
    """Create all database tables"""
    Base.metadata.create_all(bind=engine)

# Dependency to get a database session
def get_db():
    """Dependency to get a database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()