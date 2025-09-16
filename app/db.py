"""
Single place to:
- Read DATABASE_URL from env
- Create a SQLAlchemy Engine (talks to MySQL via PyMySQL)
- Create a Session factory (SessionLocal) for per-request DB sessions
- Provide get_db() dependency for FastAPI routes

Why: centralizing this keeps connection logic consistent and testable.
"""

import os
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from dotenv import load_dotenv

# 1) Load env vars from .env if present
# dev convenience; in prod my platform injects env vars
load_dotenv()

# 2) Pull the connection string.
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL is not set. Add it to your environment or a local .env (not committed)."
    )

# 3) Create the SQLAlchemy Engine.
#    pool_pre_ping=True = auto-detect dead connections (helps with long-lived processes).
#    echo=False = set True to print SQL during local debugging.
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    echo=False,
    future=True,
)

# 4) Session factory.
#    autocommit=False, autoflush=False are the usual FastAPI/SQLAlchemy defaults.
#    Each request gets its own session from this factory.
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

# 5) Base class for ORM models.
class Base(DeclarativeBase):
    pass

# 6) FastAPI dependency that yields a DB session for the duration of a request.
#    - Opens a session
#    - Yields it to the route/CRUD code
#    - Ensures it gets closed even if exceptions happen
def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
