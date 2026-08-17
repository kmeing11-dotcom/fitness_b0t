from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from app.services.db_service import DatabaseService
from app.db import get_db
from app.models import UserRole

router = Router()

@router.message(Command("help"))
async def cmd_help(message: Message):
    db = DatabaseService(next(get_db()))
    user = db.get_user(message.from_user.id)
    if not user:
        await message.answer("Сначала /start")
        return
    if user.role == UserRole.TRAINER:
        text = "📚 Тренер: /my_clients, /stats, /report, /set_reminder"
    else:
        text = "📚 Ученик: /set_measurements, /my_progress"
    await message.answer(text)