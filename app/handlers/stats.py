from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from app.services.db_service import DatabaseService
from app.services.chart_service import ChartService
import traceback
from io import BytesIO

router = Router()
db = DatabaseService()


@router.message(Command("stats"))
async def stats_command(message: Message):
    try:
        # Проверяем, что пользователь — тренер
        user = db.get_user(message.from_user.id)
        if not user or user.role != "trainer":
            await message.answer("❌ Эта команда доступна только тренерам.")
            return

        # Разбираем аргументы
        args = message.text.split()
        if len(args) < 2:
            await message.answer(
                "❌ Использование: /stats @username\n"
                "Пример: /stats @ivan_ivanov"
            )
            return

        username = args[1].lstrip('@')
        client = db.get_user_by_username(username)

        if not client:
            await message.answer(f"❌ Пользователь @{username} не найден.")
            return

        # Проверяем, что ученик действительно привязан к тренеру
        clients = db.get_trainer_clients(user.id)
        if client.id not in [c.id for c in clients]:
            await message.answer(f"❌ @{username} не является вашим учеником.")
            return

        # Получаем замеры
        measurements = db.get_measurements(client.id, days=30)

        if len(measurements) < 2:
            await message.answer(
                f"❌ Недостаточно данных. Нужно минимум 2 замера."
            )
            return

        # Генерируем график в память
        chart_service = ChartService()
        chart_data = await chart_service.generate_stats_chart_bytes(client.id, measurements)

        if not chart_data:
            await message.answer("❌ Не удалось сгенерировать график.")
            return

        # Отправляем график
        await message.answer_photo(
            photo=BytesIO(chart_data),
            caption=f"📊 Статистика прогресса: {client.full_name}"
        )

    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")
        print(f"ERROR: {traceback.format_exc()}")
