import asyncio
import sys
from pathlib import Path
from aiohttp import web

sys.path.append(str(Path(__file__).parent.parent))

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from app.config import Config
from app.handlers import start, client, measurements, stats, reminders, admin, help
from app.services.reminder_service import ReminderService
from app.utils.logger import logger


async def main():
    # БЕЗ ПРОКСИ! Просто используем VPN
    session = AiohttpSession(timeout=120)

    bot = Bot(
        token=Config.BOT_TOKEN,
        session=session,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )

    dp = Dispatcher(storage=MemoryStorage())

    dp.include_router(start.router)
    dp.include_router(client.router)
    dp.include_router(measurements.router)
    dp.include_router(stats.router)
    dp.include_router(reminders.router)
    dp.include_router(admin.router)
    dp.include_router(help.router)

    reminder_service = ReminderService(bot)
    Config.ensure_temp_folder()

    logger.info("🚀 Bot started successfully")

    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        raise
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())


async def health_check(request):
    return web.Response(text="OK")

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host="0.0.0.0", port=10000)
    await site.start()
    print("✅ Health check server started on port 10000")
