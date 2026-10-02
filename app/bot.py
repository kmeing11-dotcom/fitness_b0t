# app/bot.py
import sys
from pathlib import Path

root_path = Path(__file__).parent.parent
sys.path.insert(0, str(root_path))

import asyncio
from aiohttp import web
import os
import signal

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from app.config import Config
from app.handlers import (
    start, client, measurements, stats,
    reminders, admin, help, menu, reports,
    profile,
    payments        # ← ДОЛЖЕН БЫТЬ ЗДЕСЬ
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
            default=DefaultBotProperties(parse_mode=ParseMode.HTML)
        )
        logger.info("✅ Bot created")

        self.dp = Dispatcher(storage=MemoryStorage())
        self._setup_routers()
        logger.info("✅ Routers registered")

        self.reminder_service = ReminderService(self.bot)
        init_reminder_service(self.reminder_service)
        await self.reminder_service.start()
        logger.info("✅ Reminder service created and started")

        Config.ensure_temp_folder()
        logger.info(f"✅ Temp folder: {Config.get_temp_folder()}")

        self._setup_signal_handlers()

    def _setup_routers(self):
        """
        Порядок критичен:
        - reports ДО client (report_select_*)
        - profile — обычные команды
        - menu — Reply-кнопки в конце
        """
        routers = [
            start.router,
            help.router,
            profile.router,        # /edit_profile, /delete_account
            measurements.router,
            client.router,
            reports.router,
            stats.router,
            payments.router,
            reminders.router,
            admin.router,
            menu.router,
        ]
        for router in routers:
            self.dp.include_router(router)

    def _setup_signal_handlers(self):
        try:
            loop = asyncio.get_event_loop()
            for sig in (signal.SIGINT, signal.SIGTERM):
                loop.add_signal_handler(
                    sig,
                    lambda s=sig: asyncio.create_task(self.shutdown())
                )
            logger.info("✅ Signal handlers installed")
        except NotImplementedError:
            logger.warning("⚠️ loop.add_signal_handler not supported, using signal.signal")

            def signal_handler(sig, frame):
                logger.info(f"Received signal {sig}, stopping bot...")
                asyncio.create_task(self.shutdown())

            signal.signal(signal.SIGINT, signal_handler)
            try:
                signal.signal(signal.SIGTERM, signal_handler)
            except (AttributeError, ValueError):
                pass

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
                allowed_updates=["message", "callback_query"],
                skip_updates=True
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
            try:
                await self.dp.stop_polling()
                logger.info("✅ Polling stopped")
            except Exception as e:
                logger.info(f"Polling already stopped: {e}")

        if self.reminder_service:
            try:
                await self.reminder_service.stop()
                logger.info("✅ Reminder service stopped")
            except Exception as e:
                logger.warning(f"Error stopping reminder service: {e}")

        if self.web_runner:
            try:
                await self.web_runner.cleanup()
                logger.info("✅ Web server stopped")
            except Exception as e:
                logger.warning(f"Error stopping web server: {e}")

        if self.bot:
            try:
                await self.bot.session.close()
                logger.info("✅ Bot session closed")
            except Exception as e:
                logger.warning(f"Error closing bot session: {e}")

        try:
            Database.close_session()
            logger.info("✅ Database sessions closed")
        except Exception as e:
            logger.warning(f"Error closing DB session: {e}")

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
