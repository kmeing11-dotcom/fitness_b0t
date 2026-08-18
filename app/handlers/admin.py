from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from app.config import Config
from app.services.db_service import DatabaseService
from app.models import UserRole

router = Router()
db = DatabaseService()

def is_admin(user_id: int) -> bool:
    return user_id == Config.ADMIN_TELEGRAM_ID

@router.message(Command("admin_stats"))
async def admin_stats(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ Доступ запрещен.")
        return

    trainers = db.get_users_by_role(UserRole.TRAINER)
    clients = db.get_users_by_role(UserRole.CLIENT)
    subs = db.get_all_active_subscriptions()

    response = (
        "📊 Статистика системы:\n\n"
        f"👨‍🏫 Тренеры: {len(trainers)}\n"
        f"👨‍🎓 Ученики: {len(clients)}\n"
        f"💳 Активных подписок (Pro): {subs}\n"
        f"👥 Всего пользователей: {len(trainers) + len(clients)}"
    )
    await message.answer(response)

@router.message(Command("set_trial"))
async def set_trial(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ Доступ запрещен.")
        return

    args = message.text.split()
    if len(args) < 3:
        await message.answer("❌ Использование: /set_trial @username 7 (дней)")
        return

    username = args[1].lstrip('@')
    user = db.get_user_by_username(username)
    if not user:
        await message.answer(f"❌ Пользователь @{username} не найден.")
        return

    try:
        days = int(args[2])
        if days <= 0:
            await message.answer("❌ Количество дней должно быть больше 0.")
            return
    except ValueError:
        await message.answer("❌ Укажите количество дней числом.")
        return

    db.set_trial_subscription(user.id, days)
    await message.answer(
        f"✅ Пользователю @{username} выдан пробный период на {days} дней (Pro)."
    )

@router.message(Command("cancel_subscription"))
async def cancel_subscription(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ Доступ запрещен.")
        return

    args = message.text.split()
    if len(args) < 2:
        await message.answer("❌ Использование: /cancel_subscription @username")
        return

    username = args[1].lstrip('@')
    user = db.get_user_by_username(username)
    if not user:
        await message.answer(f"❌ Пользователь @{username} не найден.")
        return

    if db.cancel_subscription(user.id):
        await message.answer(f"✅ Подписка пользователя @{username} отключена.")
    else:
        await message.answer(f"❌ У пользователя @{username} не было активной подписки.")
