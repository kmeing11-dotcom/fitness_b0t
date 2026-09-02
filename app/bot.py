import sys
from pathlib import Path

# Добавляем корневую папку в путь
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
    reminders, admin, help, menu, trainer, reports
)
from app.services.reminder_service import ReminderService
from app.utils.logger import get_logger
from app.db import init_db, Database, engine, add_missing_columns
from app.handlers.reminders import init_reminder_service
from sqlalchemy import text

logger = get_logger(__name__)


def fix_goal_enum():
    """Исправляет enum goal в PostgreSQL"""
    try:
        if not Config.DATABASE_URL or not Config.DATABASE_URL.startswith("postgresql"):
            logger.info("Not using PostgreSQL, skipping enum fix")
            return
        
        with engine.connect() as conn:
            result = conn.execute(text(
                "SELECT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'goal');"
            ))
            exists = result.scalar()
            
            if exists:
                result = conn.execute(text("SELECT enum_range(NULL::goal);"))
                values = result.fetchone()
                if values:
                    current_values = values[0][1:-1].split(',')
                    logger.info(f"Current goal enum values: {current_values}")
                    
                    if 'weight_loss' not in current_values:
                        logger.warning("⚠️ 'weight_loss' not found in enum, recreating...")
                        conn.execute(text("DROP TYPE IF EXISTS goal CASCADE;"))
                        conn.execute(text(
                            "CREATE TYPE goal AS ENUM ('weight_loss', 'muscle_gain', 'maintain');"
                        ))
                        conn.commit()
                        logger.info("✅ Goal enum recreated successfully!")
                else:
                    logger.warning("⚠️ Goal enum exists but no values, recreating...")
                    conn.execute(text("DROP TYPE IF EXISTS goal CASCADE;"))
                    conn.execute(text(
                        "CREATE TYPE goal AS ENUM ('weight_loss', 'muscle_gain', 'maintain');"
                    ))
                    conn.commit()
                    logger.info("✅ Goal enum recreated successfully!")
            else:
                logger.info("Creating goal enum...")
                conn.execute(text(
                    "CREATE TYPE goal AS ENUM ('weight_loss', 'muscle_gain', 'maintain');"
                ))
                conn.commit()
                logger.info("✅ Goal enum created successfully!")
                
    except Exception as e:
        logger.error(f"Error fixing goal enum: {e}")


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

        # Исправляем enum перед созданием таблиц
        fix_goal_enum()
        
        # Добавляем недостающие колонки
        add_missing_columns()
        
        # Инициализируем БД (создаёт таблицы, если их нет)
        Database.drop_db()
        init_db()
        logger.info("✅ Database initialized")

        session = AiohttpSession(timeout=120)

        self.bot = Bot(
            token=Config.BOT_TOKEN,
            session=session,
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
            try:
                await self.dp.stop_polling()
                logger.info("✅ Polling stopped")
            except Exception as e:
                logger.info(f"Polling already stopped: {e}")

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
