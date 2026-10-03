from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
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


@router.message(F.text == "🔙 Назад")
async def back_to_menu(message: Message):
    try:
        user = db.get_user_by_telegram(message.from_user.id)
        if not user:
            await message.answer(
                "❌ Вы не зарегистрированы. Используйте /start.",
                reply_markup=get_cancel_keyboard()
            )
            return

        if user['role'] == UserRole.TRAINER.value:
            await message.answer(
                f"👋 <b>Главное меню тренера</b>\n\n"
                f"Добро пожаловать, {user['full_name'] or 'Тренер'}!",
                parse_mode=ParseMode.HTML,
                reply_markup=get_trainer_menu_keyboard()
            )
        else:
            await message.answer(
                f"👋 <b>Главное меню ученика</b>\n\n"
                f"Добро пожаловать, {user['full_name'] or 'Ученик'}!",
                parse_mode=ParseMode.HTML,
                reply_markup=get_client_menu_keyboard()
            )
    except Exception as e:
        logger.error(f"Error in back_to_menu: {e}")
        await message.answer("❌ Ошибка при загрузке меню.")


@router.message(F.text == "👥 Мои ученики")
async def show_clients(message: Message):
    try:
        user = db.get_user_by_telegram(message.from_user.id)
        if not user:
            await message.answer("❌ Вы не зарегистрированы. Используйте /start.")
            return

        if user['role'] != UserRole.TRAINER.value:
            await message.answer("❌ Эта функция доступна только тренерам.")
            return

        clients = db.get_trainer_clients(user['id'])

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
    try:
        user = db.get_user_by_telegram(message.from_user.id)
        if not user or user['role'] != UserRole.TRAINER.value:
            await message.answer("❌ Только для тренеров.")
            return

        clients = db.get_trainer_clients(user['id'])

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
    try:
        user = db.get_user_by_telegram(message.from_user.id)
        if not user or user['role'] != UserRole.TRAINER.value:
            await message.answer("❌ Только для тренеров.")
            return

        clients = db.get_trainer_clients(user['id'])

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
    try:
        user = db.get_user_by_telegram(message.from_user.id)
        if not user or user['role'] != UserRole.TRAINER.value:
            await message.answer("❌ Только для тренеров.")
            return

        reminders = db.get_trainer_reminders(user['id'])

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
        if not user or user['role'] != UserRole.TRAINER.value:
            await message.answer("❌ Только для тренеров.")
            return

        clients = db.get_trainer_clients(user['id'])

        if not clients:
            await message.answer(
                "📭 У вас пока нет учеников.\n"
                "Добавьте учеников для отправки сообщений.",
                reply_markup=get_back_keyboard()
            )
            return

        keyboard = get_clients_list_keyboard(clients, action="msg")

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
    try:
        user = db.get_user_by_telegram(message.from_user.id)
        if not user:
            await message.answer("❌ Вы не зарегистрированы.")
            return

        text = f"⚙️ <b>Настройки</b>\n\n"
        text += f"👤 Имя: {user['full_name'] or 'Не указано'}\n"
        text += f"📱 Username: @{user['username'] or 'Не указан'}\n"
        text += f"🎯 Роль: {'Тренер' if user['role'] == UserRole.TRAINER.value else 'Ученик'}\n"

        if user['role'] == UserRole.CLIENT.value:
            text += f"🎂 Возраст: {user['age'] or 'Не указан'}\n"
            text += f"📏 Рост: {user['height'] or 'Не указан'} см\n"
            text += f"🎯 Цель: {user['goal'] or 'Не указана'}\n"
        elif user['role'] == UserRole.TRAINER.value:
            text += f"📱 Телефон: {user['phone'] or 'Не указан'}\n"
            text += f"🏢 Студия: {user['studio_name'] or 'Не указана'}\n"

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


@router.message(F.text == "📝 Внести замеры")
async def menu_measurements(message: Message, state: FSMContext):
    try:
        user = db.get_user_by_telegram(message.from_user.id)
        if not user or user['role'] != UserRole.CLIENT.value:
            await message.answer("❌ Эта функция доступна только ученикам.")
            return

        from app.handlers.measurements import start_measurements
        await start_measurements(message, state)

    except Exception as e:
        logger.error(f"Error in menu_measurements: {e}")
        await message.answer("❌ Ошибка при открытии формы замеров.")


@router.message(F.text == "📊 Мой прогресс")
async def menu_progress(message: Message):
    try:
        user = db.get_user_by_telegram(message.from_user.id)
        if not user or user['role'] != UserRole.CLIENT.value:
            await message.answer("❌ Только для учеников.")
            return

        from app.handlers.measurements import my_progress
        await my_progress(message)

    except Exception as e:
        logger.error(f"Error in menu_progress: {e}")
        await message.answer("❌ Ошибка при загрузке прогресса.")


@router.message(F.text == "📄 Мой отчёт")
async def menu_my_report(message: Message):
    try:
        user = db.get_user_by_telegram(message.from_user.id)
        if not user or user['role'] != UserRole.CLIENT.value:
            await message.answer("❌ Только для учеников.")
            return

        from app.handlers.reports import my_report_command
        await my_report_command(message)

    except Exception as e:
        logger.error(f"Error in menu_my_report: {e}")
        await message.answer("❌ Ошибка при генерации отчёта.")


# ============================================================
#  ДОБАВИТЬ УЧЕНИКА (кнопка)
# ============================================================

@router.message(F.text == "➕ Добавить ученика")
async def menu_add_client(message: Message):
    """Показывает выбор: по ссылке или по @username."""
    try:
        user = db.get_user_by_telegram(message.from_user.id)
        if not user:
            await message.answer("❌ Вы не зарегистрированы. /start")
            return

        if user['role'] != UserRole.TRAINER.value:
            await message.answer("❌ Только для тренеров.")
            return

        from app.keyboards.inline import get_add_client_choice_keyboard

        await message.answer(
            "➕ <b>Добавить ученика</b>\n\n"
            "<b>Выберите способ:</b>\n\n"
            "🔗 <b>По ссылке</b> — если ученик новый или не в Telegram\n"
            "📱 <b>По @username</b> — если ученик уже в Telegram и знает свой username",
            parse_mode=ParseMode.HTML,
            reply_markup=get_add_client_choice_keyboard()
        )

    except Exception as e:
        logger.error(f"Error in menu_add_client: {e}\n{traceback.format_exc()}")
        await message.answer("❌ Ошибка.")


# ============================================================
#  CALLBACK: ВЫБОР СПОСОБА
# ============================================================

@router.callback_query(F.data == "add_client_link")
async def callback_add_client_link(callback: CallbackQuery):
    """Генерирует invite-ссылку."""
    try:
        user = db.get_user_by_telegram(callback.from_user.id)
        if not user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return

        if user['role'] != UserRole.TRAINER.value:
            await callback.answer("❌ Только для тренеров", show_alert=True)
            return

        # Проверка Pro
        from app.services.subscription_service import is_pro
        if not is_pro(user['id']):
            await callback.message.edit_text(
                "❌ <b>Приглашение по ссылке — только на Pro</b>\n\n"
                "На Free-плане используйте способ «По @username».\n\n"
                "💎 Оформить Pro: /pro",
                parse_mode=ParseMode.HTML
            )
            await callback.answer()
            return

        # Генерируем токен
        token = db.generate_invite_token(user['id'])
        if not token:
            await callback.message.edit_text("❌ Не удалось создать ссылку.")
            await callback.answer()
            return

        bot_info = await callback.bot.get_me()
        invite_link = f"https://t.me/{bot_info.username}?start=inv_{token}"

        text = (
            f"🔗 <b>Ссылка для приглашения</b>\n\n"
            f"<code>{invite_link}</code>\n\n"
            f"<b>Что делать:</b>\n"
            f"• Скопируйте ссылку\n"
            f"• Отправьте ученику в любом мессенджере\n"
            f"• Он перейдёт → зарегистрируется → <b>привяжется к вам</b>\n\n"
            f"<i>Можно отправлять много раз — все, кто перейдёт, станут вашими учениками.</i>"
        )

        from app.keyboards.inline import get_back_inline_keyboard

        await callback.message.edit_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=get_back_inline_keyboard("back_to_menu")
        )
        await callback.answer()

        logger.info(f"🔗 Invite link shown for trainer {user['id']}")

    except Exception as e:
        logger.error(f"Error in callback_add_client_link: {e}\n{traceback.format_exc()}")
        await callback.answer("❌ Ошибка", show_alert=True)


@router.callback_query(F.data == "add_client_username")
async def callback_add_client_username(callback: CallbackQuery):
    """Показывает инструкцию по /add_client @username."""
    try:
        text = (
            f"📱 <b>Добавить по @username</b>\n\n"
            f"<b>Как это работает:</b>\n"
            f"1. Ученик <b>уже</b> зарегистрирован в боте\n"
            f"2. Вы знаете его Telegram username\n"
            f"3. Отправьте команду:\n\n"
            f"<code>/add_client @username</code>\n\n"
            f"<b>Пример:</b>\n"
            f"<code>/add_client @ivan_petrov</code>\n\n"
            f"<i>Ученик получит приглашение и должен будет его подтвердить.</i>"
        )

        from app.keyboards.inline import get_add_client_username_keyboard

        await callback.message.edit_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=get_add_client_username_keyboard()
        )
        await callback.answer()

    except Exception as e:
        logger.error(f"Error in callback_add_client_username: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@router.callback_query(F.data == "add_client_back")
async def callback_add_client_back(callback: CallbackQuery):
    """Возврат к выбору способа."""
    try:
        from app.keyboards.inline import get_add_client_choice_keyboard

        await callback.message.edit_text(
            "➕ <b>Добавить ученика</b>\n\n"
            "<b>Выберите способ:</b>\n\n"
            "🔗 <b>По ссылке</b> — если ученик новый или не в Telegram\n"
            "📱 <b>По @username</b> — если ученик уже в Telegram",
            parse_mode=ParseMode.HTML,
            reply_markup=get_add_client_choice_keyboard()
        )
        await callback.answer()

    except Exception as e:
        logger.error(f"Error in callback_add_client_back: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)
