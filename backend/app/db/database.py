"""Backward-compatible imports for the database module."""

from app.core.database import Base, get_db, get_engine, get_session_local

__all__ = ["Base", "get_db", "get_engine", "get_session_local"]
