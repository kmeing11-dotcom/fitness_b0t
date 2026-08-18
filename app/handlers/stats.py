from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from app.services.db_service import DatabaseService
from app.services.chart_service import ChartService
from app.keyboards.inline import clients_list_keyboard

router = Router()
db = DatabaseService()


@router.message(Command("stats"))
async def stats_command(message: Message):
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


@router.callback_query(F.data.startswith("stats_"))
async def show_client_stats(callback: CallbackQuery):
    # Разделяем по "_" (подчёркивание), а не по ":"
    parts = callback.data.split("_")
    if len(parts) != 2:
        await callback.answer("❌ Ошибка в данных.")
        return
    client_id = int(parts[1])

    client = db.get_user(client_id)
    if not client:
        await callback.answer("❌ Ученик не найден.")
        return

    measurements = db.get_measurements(client_id, days=30)

    if len(measurements) < 2:
        await callback.message.answer(
            f"❌ Недостаточно данных для ученика {client.full_name}. Нужно минимум 2 замера."
        )
        await callback.answer()
        return

    from app.services.chart_service import ChartService
    chart_service = ChartService()
    chart_path = chart_service.generate_stats_chart(client_id, measurements)

    if chart_path:
        await callback.message.answer_photo(
            photo=open(chart_path, 'rb'),
            caption=f"📊 Статистика прогресса: {client.full_name}"
        )
    else:
        await callback.message.answer("❌ Ошибка при генерации графика.")

    await callback.answer()
