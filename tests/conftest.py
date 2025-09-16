"""
- Spins up temp test DB
- Create tables before tests run
- Provide a db_session fixture and override FastAPI’s get_db so routes use the test session.
- Provide a client fixture (TestClient(app)) that already has the DB override applied.
"""
import os
import pytest
from typing import Generator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Ensure the app does NOT run dev-only startup hooks (e.g., auto-create tables against real DB)
os.environ.setdefault("APP_ENV", "test")

from app.db import Base, get_db
from app.main import app
from app import models

# Use SQLite in-memory for tests (fast, isolated)
TEST_DATABASE_URL = "sqlite+pysqlite:///:memory:"

@pytest.fixture(scope="session")
def engine():
    # StaticPool + check_same_thread=False lets Starlette's TestClient and SQLAlchemy
    # share ONE in-memory SQLite database across threads. Otherwise each thread would
    # see a different empty DB.
    engine = create_engine(
        TEST_DATABASE_URL,
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,  # <-- share one connection across threads
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def db_session(engine) -> Generator:
    """Provide a clean session per test with rollback."""
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    db = TestingSessionLocal()
    try:
        yield db
        # Roll back uncommitted changes in this session
        db.rollback()
    finally:
        db.close()

@pytest.fixture(autouse=True)
def _clean_db(engine):
    """
    Keep tests independent:
    The app/repository commits inside requests, so data would leak between tests.
    We delete rows before each test to ensure a clean slate.
    """
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM guesses"))
        conn.execute(text("DELETE FROM games"))
        conn.execute(text("DELETE FROM stats"))
    yield

@pytest.fixture(autouse=True)
def override_dep(db_session):
    """Force the app to use our test session for every request."""
    def _get_db_for_tests():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _get_db_for_tests
    yield
    app.dependency_overrides.clear()

@pytest.fixture
def client():
    # This client talks to the FastAPI app in-process. Because we’ve overridden get_db,
    # every request uses our SQLite in-memory session instead of my real MySQL connection.
    return TestClient(app)
