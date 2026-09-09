# Database package
from app.database.connection import engine, SessionLocal
from app.database.base import Base


def get_db():
    """FastAPI dependency that yields a database session and ensures it is closed."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
