from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.config import Config
from app.models import Base

engine = create_engine(
    Config.DATABASE_URL,
    connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(engine)

def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()