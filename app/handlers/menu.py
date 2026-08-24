from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.enums import ParseMode
from app.services.db_service import DatabaseService
from app.keyboards.inline import (
    get_trainer_menu_keyboard,
    get_client_menu_keyboard,
    get_clients_list_keyboard,
    get_back_keyboard,
    get_cancel_keyboard
)
from app.models import UserRole
from app.utils.logger import get_logger
import traceback

logger = get_logger(__name__)
router = Router()
db = DatabaseService()


# ============================================================
#  ГЛАВНОЕ МЕНЮ
# ============================================================

@router.message(F.text == "🔙 Назад")
async def back_to_menu(message: Message):
    """
    Возврат в главное меню.
    """
    try:
        user = db.get_user_by_telegram(message.from_user.id)
        if not user:
            await message.answer(
                "❌ Вы не зарегистрированы. Используйте /start.",
                reply_markup=get_cancel_keyboard()
            )
            return

        if user.role == UserRole.TRAINER:
            await message.answer(
                f"👋 <b>Главное меню тренера</b>\n\n"
                f"Добро пожаловать, {user.full_name or 'Тренер'}!",
                parse_mode=ParseMode.HTML,
                reply_markup=get_trainer_menu_keyboard()
            )
        else:
            await message.answer(
                f"👋 <b>Главное меню ученика</b>\n\n"
                f"Добро пожаловать, {user.full_name or 'Ученик'}!",
                parse_mode=ParseMode.HTML,
                reply_markup=get_client_menu_keyboard()
            )
    except Exception as e:
        logger.error(f"Error in back_to_menu: {e}")
        await message.answer("❌ Ошибка при загрузке меню.")


# ============================================================
#  МЕНЮ ТРЕНЕРА
# ============================================================

@router.message(F.text == "👥 Мои ученики")
async def show_clients(message: Message):
    """
    Показывает список учеников тренера.
    """
    try:
        user = db.get_user_by_telegram(message.from_user.id)
        if not user:
            await message.answer("❌ Вы не зарегистрированы. Используйте /start.")
            return

        if user.role != UserRole.TRAINER:
            await message.answer("❌ Эта функция доступна только тренерам.")
            return

        clients = db.get_trainer_clients(user.id)

        if not clients:
            await message.answer(
                "📭 У вас пока нет учеников.\n\n"
                "Чтобы добавить ученика, используйте команду:\n"
                "/add_client @username",
                reply_markup=get_back_keyboard()
            )
            return

        keyboard = get_clients_list_keyboard(clients, action="info")

        await message.answer(
            f"👥 <b>Ваши ученики</b> ({len(clients)} чел.):\n\n"
            f"<i>Нажмите на ученика для просмотра информации.</i>",
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard
        )

    except Exception as e:
        logger.error(f"Error in show_clients: {e}\n{traceback.format_exc()}")
        await message.answer("❌ Ошибка при загрузке списка учеников.")


@router.message(F.text == "📊 Статистика")
async def menu_stats(message: Message):
    """
    Меню статистики.
    """
    try:
        user = db.get_user_by_telegram(message.from_user.id)
        if not user or user.role != UserRole.TRAINER:
            await message.answer("❌ Только для тренеров.")
            return

        clients = db.get_trainer_clients(user.id)

        if not clients:
            await message.answer(
                "📭 У вас пока нет учеников.\n"
                "Добавьте учеников для просмотра статистики.",
                reply_markup=get_back_keyboard()
            )
            return

        keyboard = get_clients_list_keyboard(clients, action="stats_select")

        await message.answer(
            f"📊 <b>Выберите ученика для статистики:</b>",
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard
        )

    except Exception as e:
        logger.error(f"Error in menu_stats: {e}")
        await message.answer("❌ Ошибка при загрузке статистики.")


@router.message(F.text == "📈 Отчёты")
async def menu_reports(message: Message):
    """
    Меню отчётов.
    """
    try:
        user = db.get_user_by_telegram(message.from_user.id)
        if not user or user.role != UserRole.TRAINER:
            await message.answer("❌ Только для тренеров.")
            return

        clients = db.get_trainer_clients(user.id)

        if not clients:
            await message.answer(
                "📭 У вас пока нет учеников.\n"
                "Добавьте учеников для создания отчётов.",
                reply_markup=get_back_keyboard()
            )
            return

        keyboard = get_clients_list_keyboard(clients, action="report_select")

        await message.answer(
            f"📈 <b>Выберите ученика для отчёта:</b>\n\n"
            f"<i>Доступны отчёты в формате PDF.</i>",
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard
        )

    except Exception as e:
        logger.error(f"Error in menu_reports: {e}")
        await message.answer("❌ Ошибка при загрузке отчётов.")


@router.message(F.text == "⏰ Напоминания")
async def menu_reminders(message: Message):
    """
    Меню управления напоминаниями.
    """
    try:
        user = db.get_user_by_telegram(message.from_user.id)
        if not user or user.role != UserRole.TRAINER:
            await message.answer("❌ Только для тренеров.")
            return

        reminders = db.get_trainer_reminders(user.id)

        status_text = f"({len(reminders)} настроено)" if reminders else "(нет напоминаний)"

        await message.answer(
            f"⏰ <b>Управление напоминаниями</b> {status_text}\n\n"
            f"📌 <b>Команды:</b>\n"
            f"• /set_reminder — установить новое напоминание\n"
            f"• /my_reminders — посмотреть текущие напоминания\n\n"
            f"<i>Напоминания будут отправляться вашим ученикам в указанное время.</i>",
            parse_mode=ParseMode.HTML,
            reply_markup=get_back_keyboard()
        )

    except Exception as e:
        logger.error(f"Error in menu_reminders: {e}")
        await message.answer("❌ Ошибка при загрузке напоминаний.")


@router.message(F.text == "📨 Рассылка")
async def menu_broadcast(message: Message):
    try:
        user = db.get_user_by_telegram(message.from_user.id)
        if not user or user.role != UserRole.TRAINER:
            await message.answer("❌ Только для тренеров.")
            return

        clients = db.get_trainer_clients(user.id)

        if not clients:
            await message.answer(
                "📭 У вас пока нет учеников.\n"
                "Добавьте учеников для отправки сообщений.",
                reply_markup=get_back_keyboard()
            )
            return

        keyboard = get_clients_list_keyboard(clients, action="msg")  # <-- ИЗМЕНИЛ action с "msg_select" на "msg"

        await message.answer(
            f"📨 <b>Выберите ученика для отправки сообщения:</b>\n\n"
            f"<i>Вы также можете использовать команду /msg @username Текст</i>",
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard
        )

    except Exception as e:
        logger.error(f"Error in menu_broadcast: {e}")
        await message.answer("❌ Ошибка при загрузке рассылки.")

@router.message(F.text == "⚙️ Настройки")
async def menu_settings(message: Message):
    """
    Меню настроек.
    """
    try:
        user = db.get_user_by_telegram(message.from_user.id)
        if not user:
            await message.answer("❌ Вы не зарегистрированы.")
            return

        text = f"⚙️ <b>Настройки</b>\n\n"
        text += f"👤 Имя: {user.full_name or 'Не указано'}\n"
        text += f"📱 Username: @{user.username or 'Не указан'}\n"
        text += f"🎯 Роль: {'Тренер' if user.role == UserRole.TRAINER else 'Ученик'}\n"

        if user.role == UserRole.CLIENT:
            text += f"🎂 Возраст: {user.age or 'Не указан'}\n"
            text += f"📏 Рост: {user.height or 'Не указан'} см\n"
            text += f"🎯 Цель: {user.goal or 'Не указана'}\n"
        elif user.role == UserRole.TRAINER:
            text += f"📱 Телефон: {user.phone or 'Не указан'}\n"
            text += f"🏢 Студия: {user.studio_name or 'Не указана'}\n"

        text += f"\n<i>Команды для управления:</i>\n"
        text += f"• /edit_profile — изменить профиль\n"
        text += f"• /delete_account — удалить аккаунт"

        await message.answer(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=get_back_keyboard()
        )

    except Exception as e:
        logger.error(f"Error in menu_settings: {e}")
        await message.answer("❌ Ошибка при загрузке настроек.")


@router.message(F.text == "❓ Помощь")
async def menu_help(message: Message):
    """
    Меню помощи.
    """
    try:
        user = db.get_user_by_telegram(message.from_user.id)
        if not user:
            await message.answer("❌ Вы не зарегистрированы. Используйте /start.")
            return

        from app.handlers.help import cmd_help
        await cmd_help(message)

    except Exception as e:
        logger.error(f"Error in menu_help: {e}")
        await message.answer("❌ Ошибка при загрузке помощи.")


# ============================================================
#  МЕНЮ УЧЕНИКА
# ============================================================

@router.message(F.text == "📝 Внести замеры")
async def menu_measurements(message: Message, state: FSMContext):
    """
    Внос замеров учеником.
    """
    try:
        user = db.get_user_by_telegram(message.from_user.id)
        if not user:
            await message.answer("❌ Вы не зарегистрированы. Используйте /start.")
            return

        if user.role != UserRole.CLIENT:
            await message.answer("❌ Эта функция доступна только ученикам.")
            return

        from app.handlers.measurements import start_measurements
        await start_measurements(message, state)

    except Exception as e:
        logger.error(f"Error in menu_measurements: {e}")
        await message.answer("❌ Ошибка при открытии формы замеров.")


@router.message(F.text == "📊 Мой прогресс")
async def menu_progress(message: Message):
    """
    Просмотр прогресса учеником.
    """
    try:
        user = db.get_user_by_telegram(message.from_user.id)
        if not user or user.role != UserRole.CLIENT:
            await message.answer("❌ Только для учеников.")
            return

        from app.handlers.measurements import my_progress
        await my_progress(message)

    except Exception as e:
        logger.error(f"Error in menu_progress: {e}")
        await message.answer("❌ Ошибка при загрузке прогресса.")


@router.message(F.text == "📄 Мой отчёт")
async def menu_my_report(message: Message):
    """
    Генерация отчёта учеником.
    """
    try:
        user = db.get_user_by_telegram(message.from_user.id)
        if not user or user.role != UserRole.CLIENT:
            await message.answer("❌ Только для учеников.")
            return

        from app.handlers.reports import my_report_command
        await my_report_command(message)

    except Exception as e:
        logger.error(f"Error in menu_my_report: {e}")
        await message.answer("❌ Ошибка при генерации отчёта.")



@router.message(Command("set_timezone"))
async def set_timezone(message: Message):
    user = db.get_user_by_telegram(message.from_user.id)
    if not user:
        await message.answer("❌ Вы не зарегистрированы.")
        return

    args = message.text.split()
    if len(args) < 2:
        await message.answer(
            "❌ Использование: /set_timezone Europe/Moscow\n\n"
            "Доступные часовые пояса:\n"
            "• Europe/Moscow (UTC+3)\n"
            "• Europe/Kaliningrad (UTC+2)\n"
            "• Asia/Yekaterinburg (UTC+5)\n"
            "• Asia/Novosibirsk (UTC+7)\n"
            "• Asia/Vladivostok (UTC+10)\n"
            "• UTC\n"
            "• ... и другие"
        )
        return

    timezone = args[1]
    
    # Проверяем, существует ли такой часовой пояс
    import pytz
    try:
        pytz.timezone(timezone)
    except:
        await message.answer(f"❌ Часовой пояс '{timezone}' не найден.")
        return
    
    db.update_user(user.id, timezone=timezone)
    await message.answer(f"✅ Часовой пояс изменён на {timezone}")
