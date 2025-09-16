"""
Dev convenience: create tables if they don't exist.
Call this at startup in local/dev only
"""

from .db import engine, Base

def create_all():
    Base.metadata.create_all(bind=engine)
