from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from app.config import Config
from app.services.db_service import DatabaseService
from app.models import UserRole
import asyncio

router = Router()
db = DatabaseService()


def is_admin(user_id: int) -> bool:
    return user_id == Config.ADMIN_TELEGRAM_ID


@router.message(Command("admin_stats"))
async def admin_stats(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ Доступ запрещен.")
        return

    trainers = await db.get_users_by_role(UserRole.TRAINER)
    clients = await db.get_users_by_role(UserRole.CLIENT)
    daily_measurements = await db.get_daily_measurements_count()

    response = (
        "📊 Статистика системы:\n\n"
        f"👨‍🏫 Тренеры: {len(trainers)}\n"
        f"👨‍🎓 Ученики: {len(clients)}\n"
        f"📝 Замеров за сегодня: {daily_measurements}\n"
        f"👥 Всего пользователей: {len(trainers) + len(clients)}"
    )

    await message.answer(response)


_pending_broadcast = None


@router.message(Command("broadcast"))
async def broadcast_command(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ Доступ запрещен.")
        return

    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer(
            "📢 Использование: /broadcast Текст сообщения\n\n"
            "Пример: /broadcast Дорогие пользователи! У нас обновление бота."
        )
        return

    global _pending_broadcast
    _pending_broadcast = args[1]

    await message.answer(
        f"📢 Вы собираетесь отправить рассылку всем пользователям:\n\n"
        f"\"{_pending_broadcast}\"\n\n"
        f"Подтвердите отправку: /confirm_broadcast"
    )


@router.message(Command("confirm_broadcast"))
async def confirm_broadcast(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ Доступ запрещен.")
        return

    global _pending_broadcast
    if not _pending_broadcast:
        await message.answer("❌ Нет ожидающей рассылки. Сначала используйте /broadcast")
        return

    users = await db.get_all_users()

    sent_count = 0
    failed_count = 0

    for user in users:
        try:
            await message.bot.send_message(
                chat_id=user.telegram_id,
                text=f"📢 {_pending_broadcast}"
            )
            sent_count += 1
            await asyncio.sleep(0.05)
        except Exception as e:
            failed_count += 1
            print(f"Failed to send to {user.telegram_id}: {e}")

    broadcast_id = await db.broadcast_message(_pending_broadcast, message.from_user.id)
    await db.update_broadcast_count(broadcast_id, sent_count)

    await message.answer(
        f"✅ Рассылка завершена!\n\n"
        f"Отправлено: {sent_count}\n"
        f"Не отправлено: {failed_count}\n"
        f"Всего пользователей: {len(users)}"
    )

    _pending_broadcast = None