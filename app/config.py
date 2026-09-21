# app/config.py
import os
from pathlib import Path
from dotenv import load_dotenv
import logging

load_dotenv()

logger = logging.getLogger(__name__)

# Корень проекта (на уровень выше app/)
BASE_DIR = Path(__file__).resolve().parent.parent


class Config:
    # ===== ОБЯЗАТЕЛЬНЫЕ =====
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    DATABASE_URL = os.getenv("DATABASE_URL")

    # ===== ОПЦИОНАЛЬНЫЕ =====
    ADMIN_TELEGRAM_ID = os.getenv("ADMIN_TELEGRAM_ID")
    REDIS_URL = os.getenv("REDIS_URL")

    # ===== ЛОГИРОВАНИЕ =====
    # FIX: LOG_LEVEL — в верхнем регистре
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

    # FIX: LOG_FILE — абсолютный путь (было относительно cwd)
    _log_file_env = os.getenv("LOG_FILE", "logs/app.log")
    LOG_FILE = str(
        Path(_log_file_env) if Path(_log_file_env).is_absolute()
        else BASE_DIR / _log_file_env
    )

    LOG_MAX_BYTES = int(os.getenv("LOG_MAX_BYTES", "10485760"))  # 10 MB
    LOG_BACKUP_COUNT = int(os.getenv("LOG_BACKUP_COUNT", "5"))

    # ===== ПАПКИ =====
    # FIX: TEMP_FOLDER — абсолютный путь
    _temp_folder_env = os.getenv("TEMP_FOLDER", "temp")
    TEMP_FOLDER = str(
        Path(_temp_folder_env) if Path(_temp_folder_env).is_absolute()
        else BASE_DIR / _temp_folder_env
    )

    # ===== ДРУГОЕ =====
    ENV = os.getenv("ENV", "development")
    DEBUG = os.getenv("DEBUG", "False").lower() == "true"

    # ============================================================
    #  МЕТОДЫ
    # ============================================================

    @classmethod
    def validate(cls):
        """Проверяет наличие обязательных переменных."""
        errors = []

        if not cls.BOT_TOKEN:
            errors.append("BOT_TOKEN is required but not set in .env")
        if not cls.DATABASE_URL:
            errors.append("DATABASE_URL is required but not set in .env")

        if errors:
            error_msg = "\n".join(errors)
            logger.error(f"Configuration errors:\n{error_msg}")
            raise ValueError(f"Missing required environment variables:\n{error_msg}")

        logger.info("✅ Configuration validated successfully")
        return True

    @classmethod
    def get_admin_ids(cls):
        """Возвращает список ID администраторов."""
        if not cls.ADMIN_TELEGRAM_ID:
            return []

        if "," in cls.ADMIN_TELEGRAM_ID:
            result = []
            for id_ in cls.ADMIN_TELEGRAM_ID.split(","):
                id_ = id_.strip()
                if not id_:
                    continue
                try:
                    result.append(int(id_))
                except ValueError:
                    logger.warning(f"Invalid admin ID: {id_}")
            return result
        else:
            try:
                return [int(cls.ADMIN_TELEGRAM_ID.strip())]
            except ValueError:
                logger.warning(f"Invalid ADMIN_TELEGRAM_ID: {cls.ADMIN_TELEGRAM_ID}")
                return []

    @classmethod
    def ensure_temp_folder(cls):
        """Создаёт временную папку. Возвращает абсолютный путь."""
        temp_path = Path(cls.TEMP_FOLDER)
        temp_path.mkdir(parents=True, exist_ok=True)
        return str(temp_path.resolve())

    @classmethod
    def get_temp_folder(cls):
        """Возвращает абсолютный путь к временной папке (создаёт, если нет)."""
        return cls.ensure_temp_folder()

    @classmethod
    def ensure_log_folder(cls):
        """Создаёт папку для логов."""
        log_path = Path(cls.LOG_FILE)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        return str(log_path)

    @classmethod
    def is_admin(cls, telegram_id: int) -> bool:
        """Проверяет, является ли пользователь админом."""
        admin_ids = cls.get_admin_ids()
        return telegram_id in admin_ids if admin_ids else False

    @classmethod
    def is_production(cls) -> bool:
        return cls.ENV.lower() == "production"

    @classmethod
    def is_development(cls) -> bool:
        return cls.ENV.lower() == "development"


# ============================================================
#  ВАЛИДАЦИЯ ПРИ ИМПОРТЕ
# ============================================================
# FIX: раньше тут был try/except с print() — теперь logging
try:
    Config.validate()
except ValueError as e:
    logging.basicConfig(level=logging.ERROR)
    logging.error(f"❌ {e}")
    logging.error("Please check your .env file")
    # НЕ выходим — bot.py всё равно вызовет validate() и упадёт с понятной ошибкой
