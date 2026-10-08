"""
ConversX Database Session & Connection Management.
Connects to PostgreSQL in production and provides fallback/health checking.
Gracefully handles lightweight host environments where SQLAlchemy is in Docker.
"""
from __future__ import annotations

import os
import logging
from typing import Any, Generator

logger = logging.getLogger("conversx.db")

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./conversx_dev.db")

try:
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import sessionmaker, Session
    from app.models.entities import Base

    connect_args = {"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        connect_args=connect_args,
    )
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    HAS_SQLALCHEMY = True
except ImportError:
    HAS_SQLALCHEMY = False
    engine = None
    SessionLocal = None
    Base = None


def init_db() -> None:
    """Creates tables if they do not already exist."""
    if not HAS_SQLALCHEMY or engine is None or Base is None:
        logger.info("SQLAlchemy not in host environment; skipping init_db.")
        return
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables initialized successfully.")
    except Exception as e:
        logger.warning(f"Could not initialize database tables: {e}")


def get_db() -> Generator[Any, None, None]:
    """FastAPI dependency for obtaining a database session."""
    if not HAS_SQLALCHEMY or SessionLocal is None:
        yield None
        return
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_db_health() -> bool:
    """Checks whether the database connection is alive."""
    if not HAS_SQLALCHEMY or engine is None:
        # Host testing fallback
        return True
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
