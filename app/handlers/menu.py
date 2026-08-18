from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from app.services.db_service import DatabaseService
from app.keyboards.inline import trainer_menu_keyboard, client_menu_keyboard
from app.models import UserRole
import traceback

router = Router()
db = DatabaseService()


# ================== ТРЕНЕР ==================

@router.message(F.text == "👥 Ученики")
async def show_clients(message: Message):
    try:
        user = db.get_user(message.from_user.id)
        if not user or user.role != UserRole.TRAINER:
            await message.answer("❌ Вы не тренер.")
            return
        clients = db.get_trainer_clients(user.id)
        if not clients:
            await message.answer("📭 У вас пока нет учеников.", reply_markup=trainer_menu_keyboard())
            return
        from app.keyboards.inline import clients_list_keyboard
        await message.answer("📋 Выберите ученика:", reply_markup=clients_list_keyboard(clients))
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")
        print(f"ERROR in menu: {traceback.format_exc()}")


@router.message(F.text == "📊 Статистика")
async def menu_stats(message: Message):
    try:
        from app.handlers.stats import stats_command
        await stats_command(message)
    except Exception as e:
        await message.answer(f"❌ Ошибка статистики: {e}")


@router.message(F.text == "📈 Отчёты")
async def menu_reports(message: Message):
    try:
        user = db.get_user(message.from_user.id)
        if not user or user.role != UserRole.TRAINER:
            return
        await message.answer(
            "📈 Для получения отчёта используйте команду:\n"
            "/report @username\n\n"
            "Пример: /report @ivan_ivanov",
            reply_markup=trainer_menu_keyboard()
        )
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")


@router.message(F.text == "⏰ Напоминания")
async def menu_reminders(message: Message):
    try:
        user = db.get_user(message.from_user.id)
        if not user or user.role != UserRole.TRAINER:
            return
        await message.answer(
            "⏰ Для управления напоминаниями:\n"
            "/set_reminder — установить новое напоминание\n"
            "/my_reminders — посмотреть текущие",
            reply_markup=trainer_menu_keyboard()
        )
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")


@router.message(F.text == "📨 Сообщение ученику")
async def menu_msg_client(message: Message):
    try:
        user = db.get_user(message.from_user.id)
        if not user or user.role != UserRole.TRAINER:
            return
        await message.answer(
            "📨 Для отправки сообщения ученику используйте команду:\n"
            "/msg @username Текст сообщения\n\n"
            "Пример: /msg @ivan_ivanov Привет! Как тренировка?",
            reply_markup=trainer_menu_keyboard()
        )
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")


@router.message(F.text == "❓ Помощь")
async def menu_help(message: Message):
    try:
        from app.handlers.help import cmd_help
        await cmd_help(message)
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")


# ================== УЧЕНИК ==================

@router.message(F.text == "📝 Внести замеры")
async def menu_measurements(message: Message, state: FSMContext):
    try:
        user = db.get_user(message.from_user.id)
        if not user or user.role != UserRole.CLIENT:
            await message.answer("❌ Только для учеников.")
            return
        from app.handlers.measurements import start_measurements
        await start_measurements(message, state)
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")


@router.message(F.text == "📊 Мой прогресс")
async def menu_progress(message: Message):
    try:
        user = db.get_user(message.from_user.id)
        if not user or user.role != UserRole.CLIENT:
            return
        from app.handlers.measurements import my_progress
        await my_progress(message)
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")
