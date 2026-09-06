# ============================================================================
# Database Module
# ============================================================================
# File: app/database.py
# Purpose: Database connection, session management, and ORM setup
# Status: Production-Ready ✅

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from app.config import settings
import logging


logger = logging.getLogger(__name__)


# ============= ENGINE & SESSION SETUP =============
# Create database engine
engine = create_engine(
    settings.database_url,
    connect_args={
        "check_same_thread": False
    } if "sqlite" in settings.database_url else {},
    echo=settings.debug,  # Log SQL queries in debug mode
    pool_pre_ping=True,  # Verify connections before using
)

logger.info(f"Database engine created: {settings.database_url}")


# Create session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

logger.info("Session factory created")


# ============= BASE CLASS =============
Base = declarative_base()

logger.info("Declarative base created")


# ============= DEPENDENCY INJECTION =============
def get_db() -> Session:
    """
    Dependency: Get database session
    
    Usage:
        @app.get("/")
        def get_data(db: Session = Depends(get_db)):
            ...
    
    Yields:
        Session: Database session
    """
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"Database session error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


# ============= UTILITY FUNCTIONS =============
def init_db():
    """
    Initialize database
    
    Creates all tables defined in models
    """
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        raise


def drop_all_tables():
    """
    Drop all tables (USE WITH CAUTION!)
    
    Only use in development/testing
    """
    try:
        Base.metadata.drop_all(bind=engine)
        logger.warning("All tables dropped")
    except Exception as e:
        logger.error(f"Error dropping tables: {e}")
        raise