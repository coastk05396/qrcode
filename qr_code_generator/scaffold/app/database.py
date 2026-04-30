from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

# Local SQLite file used by the prototype during development.
DATABASE_URL = "sqlite:///./qr_code.db"

# check_same_thread=False lets FastAPI handlers share the same SQLite DB file safely.
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
# SessionLocal is the factory that creates one SQLAlchemy session per request.
SessionLocal = sessionmaker(bind=engine)


# All ORM models inherit from this shared declarative base.
class Base(DeclarativeBase):
    pass


def get_db():
    # FastAPI injects this dependency into route handlers and closes it afterward.
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
