from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from app.services.db_service import DatabaseService
from app.services.chart_service import ChartService
from app.keyboards.inline import clients_list_keyboard
import traceback

router = Router()
db = DatabaseService()


@router.message(Command("stats"))
async def stats_command(message: Message):
    try:
        user = db.get_user(message.from_user.id)
        if not user or user.role != "trainer":
            await message.answer("❌ Эта команда доступна только тренерам.")
            return

        clients = db.get_trainer_clients(user.id)

        if not clients:
            await message.answer(
                "📊 У вас пока нет учеников.\n\n"
                "Добавьте ученика: /add_client @username"
            )
            return

        keyboard = clients_list_keyboard(clients, action="stats")
        await message.answer(
            "📊 Выберите ученика для просмотра статистики:",
            reply_markup=keyboard
        )
    except Exception as e:
        await message.answer(f"❌ Ошибка в stats_command: {e}")
        print(f"ERROR: {traceback.format_exc()}")


@router.callback_query(F.data.startswith("stats_"))
async def show_client_stats(callback: CallbackQuery):
    try:
        # 1. Разбираем callback_data
        parts = callback.data.split("_")
        if len(parts) != 2:
            await callback.answer("❌ Ошибка: неверный формат данных.")
            return

        # 2. Пытаемся получить ID ученика
        try:
            client_id = int(parts[1])
        except ValueError:
            await callback.answer("❌ Ошибка: ID ученика должен быть числом.")
            return

        # 3. Проверяем, что ученик существует
        client = db.get_user(client_id)
        if not client:
            await callback.answer(f"❌ Ученик с ID {client_id} не найден в базе.")
            return

        # 4. Получаем замеры
        measurements = db.get_measurements(client_id, days=30)

        if len(measurements) < 2:
            await callback.message.answer(
                f"❌ Недостаточно данных для ученика {client.full_name}.\n"
                f"Нужно минимум 2 замера (сейчас: {len(measurements)})."
            )
            await callback.answer()
            return

        # 5. Генерируем график
        chart_service = ChartService()
        chart_path = chart_service.generate_stats_chart(client_id, measurements)

        if not chart_path:
            await callback.message.answer("❌ Не удалось сгенерировать график.")
            await callback.answer()
            return

        # 6. Отправляем график
        await callback.message.answer_photo(
            photo=open(chart_path, 'rb'),
            caption=f"📊 Статистика прогресса: {client.full_name}"
        )
        await callback.answer()

    except Exception as e:
        await callback.message.answer(f"❌ Критическая ошибка: {e}")
        print(f"ERROR in show_client_stats: {traceback.format_exc()}")
        await callback.answer()
