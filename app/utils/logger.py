import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

# Ленивый импорт Config, чтобы избежать циклических зависимостей
_config = None


def get_config():
    global _config
    if _config is None:
        from app.config import Config
        _config = Config
    return _config


def setup_logger(name: str = "fitness_bot") -> logging.Logger:
    """Настройка и получение логгера"""
    config = get_config()

    # Создаём папку для логов
    log_path = Path(config.LOG_FILE)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, config.LOG_LEVEL, logging.INFO))

    # Очищаем старые хендлеры, чтобы не дублировать
    if logger.handlers:
        logger.handlers.clear()

    # Консольный хендлер
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(console_format)
    logger.addHandler(console_handler)

    # Файловый хендлер
    try:
        file_handler = RotatingFileHandler(
            str(log_path),
            maxBytes=config.LOG_MAX_BYTES,
            backupCount=config.LOG_BACKUP_COUNT,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_format = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
        )
        file_handler.setFormatter(file_format)
        logger.addHandler(file_handler)

        # Отдельный лог для ошибок
        error_log_path = log_path.parent / "errors.log"
        error_handler = RotatingFileHandler(
            str(error_log_path),
            maxBytes=config.LOG_MAX_BYTES,
            backupCount=config.LOG_BACKUP_COUNT,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(file_format)
        logger.addHandler(error_handler)

    except Exception as e:
        print(f"⚠️ Failed to create file handler: {e}")

    return logger


# Глобальный логгер (создаётся при первом вызове)
_logger = None


def get_logger(name: str = "fitness_bot") -> logging.Logger:
    """Получить основной логгер"""
    global _logger
    if _logger is None:
        _logger = setup_logger(name)
    return _logger


def get_child_logger(name: str) -> logging.Logger:
    """Получить дочерний логгер для модуля"""
    parent = get_logger()
    return parent.getChild(name)


# Создаём основной логгер при первом импорте
logger = get_logger()
