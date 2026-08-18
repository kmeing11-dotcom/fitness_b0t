from aiogram import Router, F
from aiogram.types import Message
from app.services.db_service import DatabaseService
from app.keyboards.inline import trainer_menu_keyboard, client_menu_keyboard
from app.models import UserRole

router = Router()
db = DatabaseService()


@router.message(F.text == "👥 Ученики")
async def show_clients(message: Message):
    user = db.get_user(message.from_user.id)
    if not user or user.role != UserRole.TRAINER:
        return
    clients = db.get_trainer_clients(user.id)
    if not clients:
        await message.answer("📭 У вас пока нет учеников.", reply_markup=trainer_menu_keyboard())
        return
    from app.keyboards.inline import clients_list_keyboard
    await message.answer("Выберите ученика:", reply_markup=clients_list_keyboard(clients))


@router.message(F.text == "📊 Статистика")
async def menu_stats(message: Message):
    user = db.get_user(message.from_user.id)
    if not user or user.role != UserRole.TRAINER:
        return
    from app.handlers.stats import stats_command
    await stats_command(message)


@router.message(F.text == "📈 Отчёты")
async def menu_reports(message: Message):
    user = db.get_user(message.from_user.id)
    if not user or user.role != UserRole.TRAINER:
        return
    await message.answer("📈 Используйте команду /report @username для получения отчёта.")


@router.message(F.text == "⏰ Напоминания")
async def menu_reminders(message: Message):
    user = db.get_user(message.from_user.id)
    if not user or user.role != UserRole.TRAINER:
        return
    await message.answer("⏰ Используйте /set_reminder для настройки напоминаний.")


@router.message(F.text == "📨 Сообщение ученику")
async def menu_message_client(message: Message):
    user = db.get_user(message.from_user.id)
    if not user or user.role != UserRole.TRAINER:
        return
    await message.answer("📨 Используйте команду /add_client @username для добавления ученика.")


@router.message(F.text == "❓ Помощь")
async def menu_help(message: Message):
    user = db.get_user(message.from_user.id)
    if not user:
        return
    from app.handlers.help import cmd_help
    await cmd_help(message)


@router.message(F.text == "📝 Внести замеры")
async def menu_measurements(message: Message):
    user = db.get_user(message.from_user.id)
    if not user or user.role != UserRole.CLIENT:
        return
    from app.handlers.measurements import start_measurements
    await start_measurements(message, None)


@router.message(F.text == "📊 Мой прогресс")
async def menu_progress(message: Message):
    user = db.get_user(message.from_user.id)
    if not user or user.role != UserRole.CLIENT:
        return
    from app.handlers.measurements import my_progress
    await my_progress(message)
