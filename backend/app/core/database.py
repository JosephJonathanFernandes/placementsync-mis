"""Database session and engine management.

SQLite is used for the MVP. The SQLAlchemy async/sync setup is kept modular
so PostgreSQL can replace SQLite by changing DATABASE_URL only.
"""

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from app.core.config import settings

Base = declarative_base()

_engine: Engine | None = None
_session_factory: sessionmaker | None = None


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        connect_args = {}
        if settings.database_url.startswith("sqlite"):
            connect_args["check_same_thread"] = False
        _engine = create_engine(
            settings.database_url,
            connect_args=connect_args,
            echo=settings.debug,
        )
    return _engine


def get_session_factory() -> sessionmaker:
    global _session_factory
    if _session_factory is None:
        _session_factory = sessionmaker(
            bind=get_engine(), autoflush=False, autocommit=False
        )
    return _session_factory


def reset_engine() -> None:
    """Drop the cached engine (useful for tests switching DATABASE_URL)."""
    global _engine, _session_factory
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _session_factory = None


def get_db() -> Session:
    """Yield a SQLAlchemy session (FastAPI dependency)."""
    db = get_session_factory()()
    try:
        yield db
    finally:
        db.close()


def create_all() -> None:
    get_engine()
    Base.metadata.create_all(bind=_engine)
