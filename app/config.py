import os
from dotenv import load_dotenv
from pathlib import Path
import logging

load_dotenv()

logger = logging.getLogger(__name__)


class Config:
    # ===== ОБЯЗАТЕЛЬНЫЕ ПЕРЕМЕННЫЕ =====
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    DATABASE_URL = os.getenv("DATABASE_URL")

    # ===== ОПЦИОНАЛЬНЫЕ ПЕРЕМЕННЫЕ =====
    ADMIN_TELEGRAM_ID = os.getenv("ADMIN_TELEGRAM_ID")
    REDIS_URL = os.getenv("REDIS_URL")

    # ===== ЛОГИРОВАНИЕ =====
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE = os.getenv("LOG_FILE", "logs/app.log")
    LOG_MAX_BYTES = int(os.getenv("LOG_MAX_BYTES", "10485760"))
    LOG_BACKUP_COUNT = int(os.getenv("LOG_BACKUP_COUNT", "5"))

    # ===== ПАПКИ =====
    TEMP_FOLDER = os.getenv("TEMP_FOLDER", "temp")

    # ===== ДРУГОЕ =====
    ENV = os.getenv("ENV", "development")
    DEBUG = os.getenv("DEBUG", "False").lower() == "true"

    @classmethod
    def validate(cls):
        """Проверяет наличие обязательных переменных"""
        errors = []

        if not cls.BOT_TOKEN:
            errors.append("BOT_TOKEN is required but not set in .env")
        if not cls.DATABASE_URL:
            errors.append("DATABASE_URL is required but not set in .env")

        if errors:
            error_msg = "\n".join(errors)
            logger.error(f"Configuration errors:\n{error_msg}")
            raise ValueError(f"Missing required environment variables:\n{error_msg}")

        logger.info("Configuration validated successfully")
        return True

    @classmethod
    def get_admin_ids(cls):
        """Возвращает список ID администраторов"""
        if not cls.ADMIN_TELEGRAM_ID:
            return []

        if "," in cls.ADMIN_TELEGRAM_ID:
            return [int(id_.strip()) for id_ in cls.ADMIN_TELEGRAM_ID.split(",") if id_.strip()]
        else:
            try:
                return [int(cls.ADMIN_TELEGRAM_ID)]
            except ValueError:
                logger.warning(f"Invalid ADMIN_TELEGRAM_ID: {cls.ADMIN_TELEGRAM_ID}")
                return []

    @classmethod
    def ensure_temp_folder(cls):
        """Создаёт временную папку в корне проекта"""
        base = Path(__file__).parent.parent
        temp_path = base / cls.TEMP_FOLDER
        temp_path.mkdir(parents=True, exist_ok=True)
        return str(temp_path.absolute())

    @classmethod
    def get_temp_folder(cls):
        """Возвращает абсолютный путь к временной папке (создаёт, если нет)"""
        return cls.ensure_temp_folder()

    @classmethod
    def is_admin(cls, telegram_id: int) -> bool:
        """Проверяет, является ли пользователь админом"""
        admin_ids = cls.get_admin_ids()
        return telegram_id in admin_ids if admin_ids else False

    @classmethod
    def is_production(cls) -> bool:
        return cls.ENV.lower() == "production"

    @classmethod
    def is_development(cls) -> bool:
        return cls.ENV.lower() == "development"


# Выполняем валидацию при первом импорте
try:
    Config.validate()
except ValueError as e:
    print(f"❌ {e}")
    print("Please check your .env file")
