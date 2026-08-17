from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from app.services.db_service import DatabaseService
from app.keyboards.inline import trainer_menu_keyboard, client_menu_keyboard
from app.db import get_db
from app.models import UserRole

router = Router()

@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    db = DatabaseService(next(get_db()))
    user = db.get_user(message.from_user.id)
    if user:
        if user.role == UserRole.TRAINER:
            await message.answer(f"👋 Привет, {user.full_name}!", reply_markup=trainer_menu_keyboard())
        else:
            await message.answer(f"👋 Привет, {user.full_name}!", reply_markup=client_menu_keyboard())
        return
    await message.answer("Выбери роль:\n/register_trainer - Тренер\n/register_client - Ученик")