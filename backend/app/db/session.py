"""
ConversX Database Session & Connection Management.
Connects to PostgreSQL in production with connection pooling and health checks.
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
    engine_kwargs: dict[str, Any] = {
        "pool_pre_ping": True,
        "connect_args": connect_args,
    }

    # Production PostgreSQL connection pool configuration
    if "postgres" in DATABASE_URL.lower():
        engine_kwargs.update({
            "pool_size": int(os.getenv("DB_POOL_SIZE", "10")),
            "max_overflow": int(os.getenv("DB_MAX_OVERFLOW", "20")),
            "pool_timeout": int(os.getenv("DB_POOL_TIMEOUT", "30")),
            "pool_recycle": int(os.getenv("DB_POOL_RECYCLE", "1800")),
        })

    engine = create_engine(DATABASE_URL, **engine_kwargs)
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
    except Exception as e:
        logger.warning(f"Database health check failed: {e}")
        return False


def close_db_connections() -> None:
    """Disposes the SQLAlchemy engine connection pool on application shutdown."""
    if HAS_SQLALCHEMY and engine is not None:
        try:
            engine.dispose()
            logger.info("Database connection pool cleanly disposed.")
        except Exception as e:
            logger.warning(f"Error disposing database engine: {e}")
