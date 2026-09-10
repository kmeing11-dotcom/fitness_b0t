from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.enums import ParseMode
from app.services.db_service import DatabaseService
from app.models import UserRole
from app.keyboards.inline import get_back_keyboard
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = Router()
db = DatabaseService()


@router.message(Command("help"))
async def cmd_help(message: Message):
    try:
        user = db.get_user_by_telegram(message.from_user.id)

        if not user:
            await message.answer(
                "👋 <b>Добро пожаловать в Fitness CRM Bot!</b>\n\n"
                "Используйте /start для регистрации.",
                parse_mode=ParseMode.HTML
            )
            return

        if user['role'] == UserRole.TRAINER.value:
            help_text = (
                "📚 <b>Справка для тренера</b>\n\n"
                "👥 <b>Управление учениками:</b>\n"
                "/add_client @username — добавить ученика\n"
                "/my_clients — список учеников\n"
                "/delete_client @username — удалить ученика\n\n"
                "📊 <b>Статистика и отчёты:</b>\n"
                "/stats — графики прогресса\n"
                "/report @username — PDF-отчёт\n\n"
                "⏰ <b>Напоминания:</b>\n"
                "/set_reminder — настроить напоминания\n"
                "/my_reminders — мои напоминания\n\n"
                "❓ <b>Помощь:</b>\n"
                "/help — эта справка"
            )
        else:
            help_text = (
                "📚 <b>Справка для ученика</b>\n\n"
                "📝 <b>Замеры:</b>\n"
                "/set_measurements — внести замеры\n"
                "/my_progress — мой прогресс\n\n"
                "📄 <b>Отчёты:</b>\n"
                "/my_report — PDF-отчёт\n\n"
                "❓ <b>Помощь:</b>\n"
                "/help — эта справка"
            )

        await message.answer(
            help_text,
            parse_mode=ParseMode.HTML,
            reply_markup=get_back_keyboard()
        )

    except Exception as e:
        logger.error(f"Error in cmd_help: {e}")
        await message.answer("❌ Ошибка при загрузке справки.")


@router.message(Command("faq"))
async def cmd_faq(message: Message):
    await help_faq(message)
