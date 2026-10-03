# app/db.py
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, scoped_session
from app.config import Config
from app.models import Base
from app.utils.logger import get_logger

logger = get_logger(__name__)


class Database:
    """
    Единый источник engine и session для всего проекта.
    DatabaseService и ReminderService используют ЭТОТ engine.
    """
    _engine = None
    _session_factory = None
    _scoped_session = None

    @classmethod
    def get_engine(cls):
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
                logger.info("✅ Database engine created")
            except Exception as e:
                logger.error(f"❌ Failed to create database engine: {e}")
                raise
        return cls._engine

    @classmethod
    def get_session_factory(cls):
        if cls._session_factory is None:
            cls._session_factory = sessionmaker(
                bind=cls.get_engine(),
                autoflush=False,
                autocommit=False,
                expire_on_commit=False,
            )
        return cls._session_factory

    @classmethod
    def get_session(cls):
        """scoped_session для ORM-операций (reminder_service)."""
        if cls._scoped_session is None:
            cls._scoped_session = scoped_session(cls.get_session_factory())
        return cls._scoped_session

    @classmethod
    def get_raw_session(cls):
        """Обычная session (не scoped) — для db_service."""
        return cls.get_session_factory()()

    @classmethod
    def init_db(cls):
        try:
            Base.metadata.create_all(cls.get_engine())
            logger.info("✅ Database tables created/verified")

            # FIX: миграции для существующих таблиц
            cls._run_migrations()
        except Exception as e:
            logger.error(f"❌ Failed to create tables: {e}")
            raise

    @classmethod
    def _run_migrations(cls):
        """
        Добавляет недостающие колонки в существующие таблицы.
        Безопасно запускать много раз — IF NOT EXISTS.
        """
        migrations = [
            # users.invite_token
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS invite_token VARCHAR(32)",
            "CREATE UNIQUE INDEX IF NOT EXISTS ix_users_invite_token ON users(invite_token)",
        ]

        with cls.get_engine().connect() as conn:
            for sql in migrations:
                try:
                    conn.execute(text(sql))
                    conn.commit()
                except Exception as e:
                    logger.debug(f"Migration skipped: {sql[:60]}... ({e})")

        logger.info("✅ Migrations applied")

    @classmethod
    def drop_db(cls):
        if Config.ENV == "development":
            Base.metadata.drop_all(cls.get_engine())
            logger.warning("⚠️ All database tables dropped!")
        else:
            logger.error("❌ Cannot drop tables in production!")

    @classmethod
    def close_session(cls):
        if cls._scoped_session is not None:
            cls._scoped_session.remove()
            logger.debug("Database scoped session closed")


# ============================================================
#  МОДУЛЬНЫЕ ОБЁРТКИ (для обратной совместимости)
# ============================================================

def get_engine():
    return Database.get_engine()


def get_session():
    return Database.get_session()


def init_db():
    Database.init_db()


# Для импорта в reminder_service.py:
Session = Database.get_session()
engine = Database.get_engine()
