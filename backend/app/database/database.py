"""
Database Configuration and Session Management

This module provides SQLAlchemy database engine, session factory,
and database initialization utilities.
"""

import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Ensure data directory exists
DATA_DIR = Path(__file__).parent.parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)

# Database URL - SQLite for hackathon simplicity
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    f"sqlite:///{DATA_DIR}/traffic_intelligence.db"
)

# Create SQLAlchemy engine
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},  # SQLite specific
    echo=False  # Set to True for SQL debugging
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for ORM models
Base = declarative_base()


def get_db():
    """
    Dependency for FastAPI - provides database session
    
    Usage in FastAPI endpoint:
        @app.get("/items")
        def get_items(db: Session = Depends(get_db)):
            return db.query(Item).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Initialize database - create all tables
    
    Called on application startup to ensure all tables exist.
    """
    # Import all models to ensure they're registered with Base
    from app.database import models  # noqa: F401
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    print(f"[OK] Database initialized at: {DATABASE_URL}")


def reset_db():
    """
    Reset database - drop and recreate all tables
    
    WARNING: This will delete all data!
    Only use during development/testing.
    """
    from app.database import models  # noqa: F401
    
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    
    print("[WARNING] Database reset complete - all data deleted")

