import asyncio
import sys
from pathlib import Path
from aiohttp import web
import os
import signal



sys.path.append(str(Path(__file__).parent.parent))

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from app.config import Config
from app.handlers import (
    start, client, measurements, stats,
    reminders, admin, help, menu, trainer, reports
)
from app.services.reminder_service import ReminderService
from app.utils.logger import get_logger
from app.db import init_db, Database
from app.handlers.reminders import init_reminder_service

logger = get_logger(__name__)


class FitnessBot:
    def __init__(self):
        self.bot = None
        self.dp = None
        self.reminder_service = None
        self.web_runner = None
        self._tasks = []
        self._running = False

    async def initialize(self):
        try:
            Config.validate()
        except ValueError as e:
            logger.error(f"❌ Configuration error: {e}")
            raise
        init_db()
        logger.info("✅ Database initialized")

        session = AiohttpSession(timeout=120)

        self.bot = Bot(
            token=Config.BOT_TOKEN,
            session=session,
            # Убираем HTML-парсинг глобально
            # default=DefaultBotProperties(parse_mode=ParseMode.HTML)
        )
        logger.info("✅ Bot created")

        self.dp = Dispatcher(storage=MemoryStorage())
        self._setup_routers()
        logger.info("✅ Routers registered")

        self.reminder_service = ReminderService(self.bot)
        await self.reminder_service.start()
        init_reminder_service(self.reminder_service)
        logger.info("✅ Reminder service created and started")

        Config.ensure_temp_folder()
        logger.info(f"✅ Temp folder: {Config.get_temp_folder()}")

        self._setup_signal_handlers()

    def _setup_routers(self):
        routers = [
            start.router,
            client.router,
            measurements.router,
            stats.router,
            reminders.router,
            admin.router,
            help.router,
            menu.router,
            trainer.router,
            reports.router,
        ]
        for router in routers:
            self.dp.include_router(router)

    def _setup_signal_handlers(self):
        def signal_handler(sig, frame):
            logger.info(f"Received signal {sig}, stopping bot...")
            asyncio.create_task(self.shutdown())

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

    async def start_web_server(self):
        app = web.Application()
        app.router.add_get("/", self.health_check)
        app.router.add_get("/health", self.health_check)

        runner = web.AppRunner(app)
        await runner.setup()

        port = int(os.getenv("PORT", 10000))
        site = web.TCPSite(runner, host="0.0.0.0", port=port)
        await site.start()

        self.web_runner = runner
        logger.info(f"✅ Health check server started on port {port}")

    @staticmethod
    async def health_check(request):
        return web.Response(text="OK")

    async def run(self):
        try:
            self._running = True
            await self.start_web_server()
            logger.info("🚀 Bot started successfully!")

            await self.dp.start_polling(
                self.bot,
                allowed_updates=["message", "callback_query", "my_chat_member"]
            )

        except Exception as e:
            logger.error(f"❌ Fatal error: {e}")
            raise
        finally:
            await self.shutdown()

    async def shutdown(self):
        if not self._running:
            return

        logger.info("🔄 Shutting down bot...")
        self._running = False

        if self.dp and self.bot:
            await self.dp.stop_polling()
            logger.info("✅ Polling stopped")

        if self.reminder_service:
            await self.reminder_service.stop()
            logger.info("✅ Reminder service stopped")

        if self.web_runner:
            await self.web_runner.cleanup()
            logger.info("✅ Web server stopped")

        if self.bot:
            await self.bot.session.close()
            logger.info("✅ Bot session closed")

        Database.close_session()
        logger.info("✅ Database sessions closed")

        logger.info("👋 Bot stopped successfully")


async def main():
    bot = FitnessBot()
    await bot.initialize()
    await bot.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 Bot stopped by user")
    except Exception as e:
        logger.error(f"❌ Unhandled exception: {e}")
        raise
