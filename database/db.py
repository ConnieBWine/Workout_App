"""
Database configuration and session creation for FastAPI.
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from config import DATABASE_URI

# Create SQLAlchemy engine
engine = create_engine(
    DATABASE_URI,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URI else {},
)

# Create sessionmaker
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create base class for models
Base = declarative_base()

# Dependency to get DB session
def get_db():
    """
    Dependency function to get a database session.
    
    Yields:
        SQLAlchemy session that will be automatically closed after use.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()