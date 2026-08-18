from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.enums import ParseMode
from app.services.db_service import DatabaseService
from app.models import UserRole
from app.keyboards.inline import get_back_keyboard, get_cancel_keyboard
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
                "Я помогу вам отслеживать прогресс в фитнесе.\n\n"
                "📌 <b>Для начала:</b>\n"
                "Используйте /start для регистрации.\n\n"
                "❓ Если у вас возникнут вопросы, обратитесь к своему тренеру.",
                parse_mode=ParseMode.HTML
            )
            return

        if user.role == UserRole.TRAINER:
            await show_trainer_help(message)
        else:
            await show_client_help(message)

    except Exception as e:
        logger.error(f"Error in cmd_help: {e}")
        await message.answer("❌ Ошибка при загрузке справки.")


async def show_trainer_help(message: Message):
    help_text = (
        "📚 <b>Справка для тренера</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "👥 <b>Управление учениками</b>\n"
        "➡️ /add_client @username — добавить ученика\n"
        "➡️ /my_clients — список учеников\n"
        "➡️ /delete_client @username — удалить ученика\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "📊 <b>Статистика и отчёты</b>\n"
        "➡️ /stats @username — графики прогресса\n"
        "➡️ /report @username — PDF-отчёт\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "⏰ <b>Напоминания</b>\n"
        "➡️ /set_reminder — настроить напоминания\n"
        "➡️ /my_reminders — мои напоминания\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "📨 <b>Сообщения</b>\n"
        "➡️ /msg @username текст — отправить сообщение ученику\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "❓ <b>Помощь</b>\n"
        "➡️ /help — эта справка\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        "💡 <b>Советы:</b>\n"
        "• Регулярно проверяйте прогресс учеников\n"
        "• Настройте напоминания для дисциплины\n"
        "• Используйте отчёты для анализа результатов"
    )

    await message.answer(
        help_text,
        parse_mode=ParseMode.HTML,
        reply_markup=get_back_keyboard()
    )


async def show_client_help(message: Message):
    help_text = (
        "📚 <b>Справка для ученика</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "📝 <b>Замеры</b>\n"
        "➡️ /set_measurements — внести замеры\n"
        "➡️ /my_progress — мой прогресс\n"
        "➡️ /my_report — PDF-отчёт\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "👨‍🏫 <b>Тренеры</b>\n"
        "➡️ /my_trainers — мои тренеры\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "❓ <b>Помощь</b>\n"
        "➡️ /help — эта справка\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        "💡 <b>Советы:</b>\n"
        "• Вносите замеры регулярно для лучшего прогресса\n"
        "• Следите за изменениями в разделе /my_progress\n"
        "• Обсуждайте свои результаты с тренером"
    )

    await message.answer(
        help_text,
        parse_mode=ParseMode.HTML,
        reply_markup=get_back_keyboard()
    )


@router.callback_query(F.data == "help_faq")
async def help_faq(callback: CallbackQuery):
    faq_text = (
        "❓ <b>Часто задаваемые вопросы</b>\n\n"
        "❓ <b>Как внести замеры?</b>\n"
        "Используйте /set_measurements или кнопку 'Внести замеры' в меню.\n\n"
        "❓ <b>Как посмотреть прогресс?</b>\n"
        "Используйте /my_progress или кнопку 'Мой прогресс' в меню.\n\n"
        "❓ <b>Как получить отчёт?</b>\n"
        "Используйте /my_report или кнопку 'Мой отчёт' в меню.\n\n"
        "❓ <b>Что делать, если я не вижу своих тренеров?</b>\n"
        "Попросите тренера добавить вас через /add_client.\n\n"
        "❓ <b>Можно ли изменить данные профиля?</b>\n"
        "Используйте /edit_profile для изменения данных.\n\n"
        "❓ <b>Как удалить аккаунт?</b>\n"
        "Используйте /delete_account (это действие нельзя отменить)."
    )

    await callback.message.edit_text(
        faq_text,
        parse_mode=ParseMode.HTML,
        reply_markup=get_back_keyboard()
    )
    await callback.answer()


@router.message(Command("faq"))
async def cmd_faq(message: Message):
    await help_faq(message)
