# bot.py
import asyncio
import sys
from pathlib import Path
from aiohttp import web
import os
import signal

# Добавляем путь к корню проекта
sys.path.append(str(Path(__file__).parent.parent))

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

# Прямые импорты, а не через app
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
    """Главный класс бота"""

    def __init__(self):
        self.bot = None
        self.dp = None
        self.reminder_service = None
        self.web_runner = None
        self._tasks = []
        self._running = False

    async def initialize(self):
        """Инициализация бота и всех компонентов"""
        # Валидируем конфиг
        try:
            Config.validate()
        except ValueError as e:
            logger.error(f"❌ Configuration error: {e}")
            raise

        # Инициализируем БД
        init_db()
        logger.info("✅ Database initialized")

        # Создаём сессию для бота
        session = AiohttpSession(timeout=120)

        self.bot = Bot(
            token=Config.BOT_TOKEN,
            session=session,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML)
        )
        logger.info("✅ Bot created")

        # Создаём диспетчер
        self.dp = Dispatcher(storage=MemoryStorage())

        # Подключаем роутеры
        self._setup_routers()
        logger.info("✅ Routers registered")

        # Создаём сервис напоминаний
        self.reminder_service = ReminderService(self.bot)
        await self.reminder_service.start()
        init_reminder_service(self.reminder_service)  # <-- Инициализация в reminders
        logger.info("✅ Reminder service created and started")

        # Создаём временную папку
        Config.ensure_temp_folder()
        logger.info(f"✅ Temp folder: {Config.get_temp_folder()}")

        # Настраиваем обработчики сигналов
        self._setup_signal_handlers()

    def _setup_routers(self):
        """Подключает все роутеры"""
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
        """Настраивает обработку сигналов для graceful shutdown"""
        def signal_handler(sig, frame):
            logger.info(f"Received signal {sig}, stopping bot...")
            asyncio.create_task(self.shutdown())

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

    async def start_web_server(self):
        """Запускает веб-сервер для health checks"""
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
        """Health check endpoint"""
        return web.Response(text="OK")

    async def start_background_tasks(self):
        """Запускает фоновые задачи"""
        # Напоминания уже запущены через self.reminder_service.start()
        pass

    async def run(self):
        """Запускает бота"""
        try:
            self._running = True

            # Запускаем health check сервер
            await self.start_web_server()

            logger.info("🚀 Bot started successfully!")

            # Запускаем polling
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
        """Корректное завершение работы"""
        if not self._running:
            return

        logger.info("🔄 Shutting down bot...")
        self._running = False

        # Останавливаем polling
        if self.dp and self.bot:
            await self.dp.stop_polling()
            logger.info("✅ Polling stopped")

        # Останавливаем reminder service
        if self.reminder_service:
            await self.reminder_service.stop()
            logger.info("✅ Reminder service stopped")

        # Останавливаем веб-сервер
        if self.web_runner:
            await self.web_runner.cleanup()
            logger.info("✅ Web server stopped")

        # Закрываем сессию бота
        if self.bot:
            await self.bot.session.close()
            logger.info("✅ Bot session closed")

        # Закрываем сессии БД
        Database.close_session()
        logger.info("✅ Database sessions closed")

        logger.info("👋 Bot stopped successfully")


async def main():
    """Точка входа"""
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
