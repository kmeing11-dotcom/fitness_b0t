import asyncio
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from app.config import Config
from app.db import init_db
from app.handlers import start, menu, trainer, client, admin, help
from app.services.reminder_service import ReminderService

async def main():
    # Создаём таблицы в БД
    init_db()

    # Создаём бота
    bot = Bot(token=Config.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()

    # Подключаем роутеры
    dp.include_router(start.router)
    dp.include_router(menu.router)
    dp.include_router(trainer.router)
    dp.include_router(client.router)
    dp.include_router(admin.router)
    dp.include_router(help.router)

    # Запускаем напоминания
    reminder_service = ReminderService(bot)

    print("🚀 Bot started successfully")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
