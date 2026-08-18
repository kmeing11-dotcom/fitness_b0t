from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from app.config import Config
from app.models import Base
import logging

logger = logging.getLogger(__name__)


class Database:
    """Класс для управления подключением к БД"""

    _engine = None
    _session_factory = None
    _scoped_session = None

    @classmethod
    def get_engine(cls):
        """Создаёт и возвращает engine (ленивая инициализация)"""
        if cls._engine is None:
            try:
                connect_args = {}
                if Config.DATABASE_URL and Config.DATABASE_URL.startswith("sqlite"):
                    connect_args = {"check_same_thread": False}

                cls._engine = create_engine(
                    Config.DATABASE_URL,
                    connect_args=connect_args,
                    echo=Config.DEBUG,
                    pool_pre_ping=True,
                    pool_recycle=3600,
                )
                logger.info("Database engine created successfully")
            except Exception as e:
                logger.error(f"Failed to create database engine: {e}")
                raise
        return cls._engine

 @classmethod
def get_session_factory(cls):
    if cls._session_factory is None:
        cls._session_factory = sessionmaker(
            bind=cls.get_engine(),
            autoflush=False,
            autocommit=False,
            expire_on_commit=False,  # <-- ВАЖНО!
        )
    return cls._session_factory

    @classmethod
    def get_session(cls):
        """Возвращает scoped сессию (потокобезопасную)"""
        if cls._scoped_session is None:
            cls._scoped_session = scoped_session(cls.get_session_factory())
        return cls._scoped_session

    @classmethod
    def init_db(cls):
        """Создаёт все таблицы, если их нет"""
        try:
            Base.metadata.create_all(cls.get_engine())
            logger.info("Database tables created/verified successfully")
        except Exception as e:
            logger.error(f"Failed to create database tables: {e}")
            raise

    @classmethod
    def drop_db(cls):
        """Удаляет все таблицы (ТОЛЬКО ДЛЯ ТЕСТОВ!)"""
        if Config.ENV == "development":
            Base.metadata.drop_all(cls.get_engine())
            logger.warning("All database tables dropped!")
        else:
            logger.error("Cannot drop tables in production!")

    @classmethod
    def close_session(cls):
        """Закрывает текущую сессию"""
        if cls._scoped_session is not None:
            cls._scoped_session.remove()
            logger.debug("Database session closed")


# Для обратной совместимости
def get_engine():
    return Database.get_engine()


def get_session():
    return Database.get_session()


def init_db():
    Database.init_db()


# Создаём сессию для использования в handlers
Session = Database.get_session()
