import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    ADMIN_TELEGRAM_ID = int(os.getenv("ADMIN_TELEGRAM_ID", 6602953094))
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///fitness.db")
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    TEMP_FOLDER = "temp"