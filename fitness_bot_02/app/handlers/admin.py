from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from app.config import Config
from app.services.db_service import DatabaseService
from app.db import get_db
import asyncio

router = Router()
pending_broadcast = None

def is_admin(user_id: int) -> bool:
    return user_id == Config.ADMIN_TELEGRAM_ID

@router.message(Command("broadcast"))
async def broadcast_command(message: Message):
    if not is_admin(message.from_user.id):
        return
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Использование: /broadcast Текст")
        return
    global pending_broadcast
    pending_broadcast = args[1]
    await message.answer(f"📢 Рассылка:\n\n{pending_broadcast}\n\nПодтвердить: /confirm_broadcast")

@router.message(Command("confirm_broadcast"))
async def confirm_broadcast(message: Message):
    if not is_admin(message.from_user.id) or not pending_broadcast:
        return
    db = DatabaseService(next(get_db()))
    users = db.get_all_users()
    sent = 0
    for user in users:
        try:
            await message.bot.send_message(user.telegram_id, f"📢 {pending_broadcast}")
            sent += 1
            await asyncio.sleep(0.05)
        except:
            pass
    await message.answer(f"✅ Отправлено: {sent} из {len(users)}")
    global pending_broadcast
    pending_broadcast = None