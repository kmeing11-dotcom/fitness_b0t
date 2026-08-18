from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from app.services.db_service import DatabaseService
from app.services.chart_service import ChartService
from app.keyboards.inline import clients_list_keyboard
import traceback
from io import BytesIO

router = Router()
db = DatabaseService()


@router.message(Command("stats"))
async def stats_command(message: Message):
    try:
        print(f"🔍 stats_command вызван от {message.from_user.id}")
        user = db.get_user(message.from_user.id)
        if not user or user.role != "trainer":
            await message.answer("❌ Эта команда доступна только тренерам.")
            return

        clients = db.get_trainer_clients(user.id)
        print(f"📋 Найдено учеников: {len(clients)}")

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
        print("✅ stats_command выполнен успешно")
    except Exception as e:
        await message.answer(f"❌ Ошибка в stats_command: {e}")
        print(f"❌ ERROR: {traceback.format_exc()}")


@router.callback_query(F.data.startswith("stats_"))
async def show_client_stats(callback: CallbackQuery):
    try:
        print(f"🔍 show_client_stats вызван, callback_data: {callback.data}")
        
        # 1. Разбираем callback_data
        parts = callback.data.split("_")
        if len(parts) != 2:
            await callback.answer("❌ Ошибка: неверный формат данных.")
            print(f"❌ Неверный формат: {parts}")
            return

        # 2. Пытаемся получить ID ученика
        try:
            client_id = int(parts[1])
            print(f"✅ ID ученика: {client_id}")
        except ValueError:
            await callback.answer("❌ Ошибка: ID ученика должен быть числом.")
            print(f"❌ ID не число: {parts[1]}")
            return

        # 3. Проверяем, что ученик существует
        client = db.get_user(client_id)
        if not client:
            await callback.answer(f"❌ Ученик с ID {client_id} не найден в базе.")
            print(f"❌ Ученик с ID {client_id} не найден")
            return
        print(f"✅ Ученик найден: {client.full_name}")

        # 4. Получаем замеры
        measurements = db.get_measurements(client_id, days=30)
        print(f"📊 Найдено замеров: {len(measurements)}")

        if len(measurements) < 2:
            await callback.message.answer(
                f"❌ Недостаточно данных для ученика {client.full_name}.\n"
                f"Нужно минимум 2 замера (сейчас: {len(measurements)})."
            )
            await callback.answer()
            print(f"❌ Замеров меньше 2")
            return

        # 5. Генерируем график в память (без сохранения на диск)
        chart_service = ChartService()
        print(f"🔄 Начинаем генерацию графика...")
        chart_data = await chart_service.generate_stats_chart_bytes(client_id, measurements)
        
        if not chart_data:
            await callback.message.answer("❌ Не удалось сгенерировать график.")
            await callback.answer()
            print(f"❌ chart_data вернул None")
            return

        # 6. Отправляем график прямо из памяти
        print(f"✅ График создан в памяти")
        await callback.message.answer_photo(
            photo=BytesIO(chart_data),
            caption=f"📊 Статистика прогресса: {client.full_name}"
        )
        print(f"✅ График успешно отправлен ученику {client.full_name}")

        await callback.answer()

    except Exception as e:
        await callback.message.answer(f"❌ Критическая ошибка: {e}")
        print(f"❌ ERROR in show_client_stats: {traceback.format_exc()}")
        await callback.answer()
