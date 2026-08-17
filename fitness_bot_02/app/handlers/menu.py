from aiogram import Router, F
from aiogram.types import Message
from app.keyboards.inline import trainer_menu_keyboard, client_menu_keyboard
from app.db import get_db
from app.services.db_service import DatabaseService

router = Router()

@router.message(F.text == "👥 Ученики")
async def menu_clients(message: Message):
    db = DatabaseService(next(get_db()))
    user = db.get_user(message.from_user.id)
    clients = db.get_trainer_clients(user.id)
    if not clients:
        await message.answer("У тебя пока нет учеников.")
        return
    from app.keyboards.inline import clients_list_keyboard
    await message.answer("Выбери ученика:", reply_markup=clients_list_keyboard(clients))

@router.message(F.text == "📊 Статистика")
async def menu_stats(message: Message):
    await message.answer("Статистика будет здесь (в разработке).")

# Добавь аналогично для всех кнопок меню