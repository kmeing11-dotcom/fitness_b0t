# app/utils/logger.py
import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

# Ленивый импорт Config
_config = None


def get_config():
    global _config
    if _config is None:
        from app.config import Config
        _config = Config
    return _config


# ============================================================
#  ГЛОБАЛЬНОЕ СОСТОЯНИЕ
# ============================================================

_initialized = False
_base_logger: logging.Logger = None


# ============================================================
#  НАСТРОЙКА
# ============================================================

def _setup_base_logger() -> logging.Logger:
    """
    FIX: настраивает БАЗОВЫЙ логгер 'fitness_bot' один раз.
    Все остальные логгеры — его дети (child), они пишут через его хендлеры.
    """
    global _initialized, _base_logger

    if _initialized:
        return _base_logger

    config = get_config()

    # Создаём папку для логов
    log_path = Path(config.LOG_FILE)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    base_logger = logging.getLogger("fitness_bot")
    level = getattr(logging, config.LOG_LEVEL, logging.INFO)
    base_logger.setLevel(level)

    # Убираем старые хендлеры, если setup_logger вызвали повторно
    if base_logger.handlers:
        base_logger.handlers.clear()

    # Не пропагандируем в root, чтобы не было двойного логирования
    base_logger.propagate = False

    # ----- Консольный хендлер -----
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(console_format)
    base_logger.addHandler(console_handler)

    # ----- Файловые хендлеры -----
    try:
        file_format = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - '
            '%(filename)s:%(lineno)d - %(message)s'
        )

        file_handler = RotatingFileHandler(
            str(log_path),
            maxBytes=config.LOG_MAX_BYTES,
            backupCount=config.LOG_BACKUP_COUNT,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(file_format)
        base_logger.addHandler(file_handler)

        # Отдельный файл для ошибок
        error_log_path = log_path.parent / "errors.log"
        error_handler = RotatingFileHandler(
            str(error_log_path),
            maxBytes=config.LOG_MAX_BYTES,
            backupCount=config.LOG_BACKUP_COUNT,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(file_format)
        base_logger.addHandler(error_handler)

    except Exception as e:
        logging.basicConfig(level=logging.INFO)
        logging.error(f"⚠️ Failed to create file handler: {e}")

    _initialized = True
    _base_logger = base_logger

    return base_logger


# ============================================================
#  ПУБЛИЧНОЕ API
# ============================================================

def setup_logger(name: str = "fitness_bot") -> logging.Logger:
    """
    Совместимость со старым API.
    Возвращает дочерний логгер базового 'fitness_bot'.
    """
    base = _setup_base_logger()
    if name == "fitness_bot":
        return base
    # Если name уже с префиксом fitness_bot — не дублируем
    if name.startswith("fitness_bot."):
        return logging.getLogger(name)
    return base.getChild(name)


def get_logger(name: str = "fitness_bot") -> logging.Logger:
    """
    FIX: теперь возвращает дочерний логгер для каждого модуля.
    Все они пишут через хендлеры базового 'fitness_bot'.

    Пример:
        get_logger(__name__)    # → 'fitness_bot.app.handlers.start'
        get_logger()            # → 'fitness_bot'
    """
    base = _setup_base_logger()

    if not name or name == "fitness_bot":
        return base

    # Убираем "app." из имени, чтобы было короче
    short_name = name
    if short_name.startswith("app."):
        short_name = short_name[4:]

    return base.getChild(short_name)


def get_child_logger(name: str) -> logging.Logger:
    """Совместимость со старым API."""
    return get_logger(name)


# ============================================================
#  ГЛОБАЛЬНЫЙ ЛОГГЕР
# ============================================================

logger = get_logger()
