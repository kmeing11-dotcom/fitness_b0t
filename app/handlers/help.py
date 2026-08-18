from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from app.services.db_service import DatabaseService
from app.models import UserRole

router = Router()
db = DatabaseService()


@router.message(Command("help"))
async def cmd_help(message: Message):
    user = db.get_user(message.from_user.id)

    if not user:
        await message.answer(
            "👋 Привет! Сначала зарегистрируйся через /start"
        )
        return

    if user.role == UserRole.TRAINER:
        help_text = (
            "📚 **Справка для тренера**\n\n"
            "👥 **Управление учениками:**\n"
            "/add_client @username - добавить ученика\n"
            "/my_clients - список учеников\n"
            "/delete_client @username - удалить ученика\n\n"
            "📊 **Статистика и отчёты:**\n"
            "/stats - графики прогресса ученика\n"
            "/report @username - PDF-отчёт\n\n"
            "⏰ **Напоминания:**\n"
            "/set_reminder - настроить напоминания\n"
            "/my_reminders - мои напоминания\n\n"
            "❓ **Помощь:**\n"
            "/help - эта справка"
        )
    else:
        help_text = (
            "📚 **Справка для ученика**\n\n"
            "📝 **Замеры:**\n"
            "/set_measurements - внести замеры\n"
            "/my_progress - мой прогресс\n\n"
            "❓ **Помощь:**\n"
            "/help - эта справка"
        )

    await message.answer(help_text, parse_mode="Markdown")
