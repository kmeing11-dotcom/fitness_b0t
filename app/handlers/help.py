# app/handlers/help.py
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.enums import ParseMode

from app.services.db_service import DatabaseService
from app.models import UserRole
from app.keyboards.inline import get_back_inline_keyboard
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = Router()
db = DatabaseService()


# ============================================================
#  /help
# ============================================================

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
                "/help — эта справка\n"
                "/faq — частые вопросы"
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
                "/help — эта справка\n"
                "/faq — частые вопросы"
            )

        await message.answer(
            help_text,
            parse_mode=ParseMode.HTML
        )

    except Exception as e:
        logger.error(f"Error in cmd_help: {e}")
        await message.answer("❌ Ошибка при загрузке справки.")


# ============================================================
#  /faq — FIX: раньше вызывалась несуществующая help_faq
# ============================================================

@router.message(Command("faq"))
async def cmd_faq(message: Message):
    try:
        user = db.get_user_by_telegram(message.from_user.id)

        if not user:
            await message.answer(
                "👋 Сначала зарегистрируйтесь: /start",
                parse_mode=ParseMode.HTML
            )
            return

        if user['role'] == UserRole.TRAINER.value:
            faq_text = (
                "❓ <b>Частые вопросы (тренер)</b>\n\n"
                "<b>1. Как добавить ученика?</b>\n"
                "Ученик должен сначала зарегистрироваться в боте через /start "
                "как «Ученик». Затем вы отправляете /add_client @username — "
                "он получит приглашение и подтвердит его.\n\n"
                "<b>2. Почему ученик не получает напоминания?</b>\n"
                "Проверьте /my_reminders — напоминание должно быть активно. "
                "Также убедитесь, что ученик не заблокировал бота.\n\n"
                "<b>3. Как сделать PDF-отчёт?</b>\n"
                "У ученика должно быть минимум 2 замера. Затем /report @username "
                "или нажмите «📈 Отчёты» в меню.\n\n"
                "<b>4. Что входит в Pro-подписку?</b>\n"
                "Неограниченное количество учеников, PDF-отчёты, "
                "напоминания, статистика и графики."
            )
        else:
            faq_text = (
                "❓ <b>Частые вопросы (ученик)</b>\n\n"
                "<b>1. Как внести замеры?</b>\n"
                "Отправьте /set_measurements и следуйте шагам. "
                "Понадобится вес, талия, бёдра, грудь, бицепс.\n\n"
                "<b>2. Как посмотреть прогресс?</b>\n"
                "/my_progress — покажет текущие значения, "
                "изменения за период и график.\n\n"
                "<b>3. Как получить PDF-отчёт?</b>\n"
                "/my_report — сгенерирует отчёт (нужно минимум 2 замера).\n\n"
                "<b>4. Почему не приходят напоминания?</b>\n"
                "Напоминания настраивает ваш тренер. "
                "Если их нет — напишите ему."
            )

        await message.answer(faq_text, parse_mode=ParseMode.HTML)

    except Exception as e:
        logger.error(f"Error in cmd_faq: {e}")
        await message.answer("❌ Ошибка при загрузке FAQ.")
