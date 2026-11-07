"""Pytest configuration: isolated SQLite database for the test suite."""

import os

# Point the application at a test database before any application module is
# imported, so pydantic-settings and SQLAlchemy pick it up.
os.environ["DATABASE_URL"] = "sqlite:///./.test_placement_sync.db"
os.environ["EXCEL_FILE_PATH"] = "./.test_placement_register.xlsx"
os.environ["LOG_FILE"] = "./.test_placement_sync.log"
os.environ["GOOGLE_CLIENT_ID"] = "test-client-id.apps.googleusercontent.com"
os.environ["GOOGLE_CLIENT_SECRET"] = "test-client-secret"
os.environ["GOOGLE_REDIRECT_URI"] = "http://localhost:8000/api/auth/gmail/callback"
os.environ["FRONTEND_URL"] = "http://localhost:5173"

from app.core.database import Base, get_engine, reset_engine  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

_TABLES = [
    "audit_logs",
    "placement_records",
    "extraction_results",
    "emails",
    "students",
    "companies",
]


@pytest.fixture(scope="session", autouse=True)
def bootstrap_database():
    reset_engine()
    db_file = ".test_placement_sync.db"
    if os.path.exists(db_file):
        os.remove(db_file)
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    yield
    reset_engine()
    if os.path.exists(db_file):
        os.remove(db_file)


@pytest.fixture
def clean_db():
    """Drop all rows from every table before and after each test."""
    from sqlalchemy import text

    engine = get_engine()
    with engine.begin() as conn:
        for table in _TABLES:
            conn.execute(text(f"DELETE FROM {table}"))
        conn.commit()
    yield
    engine = get_engine()
    with engine.begin() as conn:
        for table in _TABLES:
            conn.execute(text(f"DELETE FROM {table}"))
        conn.commit()


@pytest.fixture
def client():
    return TestClient(app)
