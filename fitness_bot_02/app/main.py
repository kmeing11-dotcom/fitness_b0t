import asyncio
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage
from redis import asyncio as aioredis
from app.config import Config
from app.db import init_db
from app.bot import bot, dp
from app.handlers import start, menu, trainer, client, admin, help
from app.services.reminder_service import ReminderService
from app.services.backup_service import BackupService


async def main():
    init_db()

    # Подключаем Redis, если есть
    redis = aioredis.from_url(Config.REDIS_URL, decode_responses=True)
    dp.storage = RedisStorage(redis)

    # Подключаем роутеры
    dp.include_router(start.router)
    dp.include_router(menu.router)
    dp.include_router(trainer.router)
    dp.include_router(client.router)
    dp.include_router(admin.router)
    dp.include_router(help.router)

    # Запускаем напоминания
    reminder_service = ReminderService(bot)

    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())