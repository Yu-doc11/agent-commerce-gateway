from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.db.models import Base

# SQLite database file — banega project ke root me "gateway.db" naam se
DATABASE_URL = "sqlite:///./gateway.db"

engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Creates all tables in the database if they don't exist yet."""
    Base.metadata.create_all(bind=engine)


def get_db():
    """Used by FastAPI routes to get a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()