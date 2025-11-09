# app/db/session.py
"""
Database session management.
Provides database connections for FastAPI and context managers.
"""
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from contextlib import contextmanager

from app.core.config import DATABASE_URL

log = logging.getLogger("whatspy.database")

# ────────────────────────────────────────────
# SQLAlchemy Engine
# ────────────────────────────────────────────
engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,  # Verify connections before using
    echo=False  # Set to True for SQL debugging
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# ────────────────────────────────────────────
# FastAPI Dependency
# ────────────────────────────────────────────
def get_db() -> Session:
    """
    FastAPI dependency for database sessions.
    
    Usage:
        @app.get("/items")
        def get_items(db: Session = Depends(get_db)):
            return db.query(Item).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ────────────────────────────────────────────
# Context Manager
# ────────────────────────────────────────────
@contextmanager
def get_db_session():
    """
    Context manager for database sessions.
    
    Usage:
        with get_db_session() as db:
            user = db.query(User).first()
            db.commit()
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# ────────────────────────────────────────────
# Database Utilities
# ────────────────────────────────────────────
def test_db_connection() -> bool:
    """Test database connection"""
    try:
        with get_db_session() as db:
            db.execute(text("SELECT 1"))
        log.info("✅ Database connection successful")
        return True
    except Exception as e:
        log.error(f"❌ Database connection failed: {e}")
        return False


def init_db():
    """
    Initialize database tables.
    This will create all tables defined in models.
    """
    from app.db.base import Base
    try:
        Base.metadata.create_all(bind=engine)
        log.info("✅ Database tables initialized")
    except Exception as e:
        log.error(f"❌ Failed to initialize database: {e}")
        raise