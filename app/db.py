from sqlalchemy import create_engine
from app.config import Config
from app.models import Base

# Создаём движок базы данных
engine = create_engine(
    Config.DATABASE_URL,
    connect_args={"check_same_thread": False}
)

def init_db():
    """Создаёт все таблицы, если их нет"""
    Base.metadata.create_all(engine)
