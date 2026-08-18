from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from app.services.db_service import DatabaseService
from app.models import UserRole

router = Router()
db = DatabaseService()


class MeasurementStates(StatesGroup):
    weight = State()
    waist = State()
    hips = State()
    chest = State()
    biceps = State()


@router.message(Command("set_measurements"))
async def start_measurements(message: Message, state: FSMContext):
    user = await db.get_user(message.from_user.id)
    if not user or user.role != UserRole.CLIENT:
        await message.answer("❌ Эта команда доступна только ученикам.")
        return

    await message.answer(
        "📝 Введите замеры. На каждом шаге введите значение или отправьте 'пропустить'.\n\n"
        "⚖️ Введите вес (в кг):"
    )
    await state.set_state(MeasurementStates.weight)


@router.message(StateFilter(MeasurementStates.weight))
async def process_weight(message: Message, state: FSMContext):
    if message.text.lower() == "пропустить":
        await state.update_data(weight=None)
    else:
        try:
            weight = float(message.text.replace(',', '.'))
            await state.update_data(weight=weight)
        except ValueError:
            await message.answer("❌ Пожалуйста, введите корректное число или 'пропустить'.")
            return

    await message.answer("📏 Введите обхват талии (в см):")
    await state.set_state(MeasurementStates.waist)


@router.message(StateFilter(MeasurementStates.waist))
async def process_waist(message: Message, state: FSMContext):
    if message.text.lower() == "пропустить":
        await state.update_data(waist=None)
    else:
        try:
            waist = float(message.text.replace(',', '.'))
            await state.update_data(waist=waist)
        except ValueError:
            await message.answer("❌ Пожалуйста, введите корректное число или 'пропустить'.")
            return

    await message.answer("📏 Введите обхват бедер (в см):")
    await state.set_state(MeasurementStates.hips)


@router.message(StateFilter(MeasurementStates.hips))
async def process_hips(message: Message, state: FSMContext):
    if message.text.lower() == "пропустить":
        await state.update_data(hips=None)
    else:
        try:
            hips = float(message.text.replace(',', '.'))
            await state.update_data(hips=hips)
        except ValueError:
            await message.answer("❌ Пожалуйста, введите корректное число или 'пропустить'.")
            return

    await message.answer("📏 Введите обхват груди (в см):")
    await state.set_state(MeasurementStates.chest)


@router.message(StateFilter(MeasurementStates.chest))
async def process_chest(message: Message, state: FSMContext):
    if message.text.lower() == "пропустить":
        await state.update_data(chest=None)
    else:
        try:
            chest = float(message.text.replace(',', '.'))
            await state.update_data(chest=chest)
        except ValueError:
            await message.answer("❌ Пожалуйста, введите корректное число или 'пропустить'.")
            return

    await message.answer("💪 Введите обхват бицепса (в см):")
    await state.set_state(MeasurementStates.biceps)


@router.message(StateFilter(MeasurementStates.biceps))
async def process_biceps(message: Message, state: FSMContext):
    if message.text.lower() == "пропустить":
        await state.update_data(biceps=None)
    else:
        try:
            biceps = float(message.text.replace(',', '.'))
            await state.update_data(biceps=biceps)
        except ValueError:
            await message.answer("❌ Пожалуйста, введите корректное число или 'пропустить'.")
            return

    data = await state.get_data()
    user = await db.get_user(message.from_user.id)

    measurement_data = {
        key: data.get(key) for key in ['weight', 'waist', 'hips', 'chest', 'biceps']
        if data.get(key) is not None
    }

    if not measurement_data:
        await message.answer("❌ Вы должны ввести хотя бы один замер.")
        await state.clear()
        return

    await db.create_measurement(user.id, measurement_data)

    response = "✅ Замеры сохранены!\n\n"
    for key, value in measurement_data.items():
        emoji = {
            'weight': '⚖️',
            'waist': '📏',
            'hips': '📏',
            'chest': '📏',
            'biceps': '💪'
        }.get(key, '📊')
        label = {
            'weight': 'Вес',
            'waist': 'Талия',
            'hips': 'Бедра',
            'chest': 'Грудь',
            'biceps': 'Бицепс'
        }.get(key, key.capitalize())
        response += f"{emoji} {label}: {value:.1f}\n"

    await message.answer(response)
    await state.clear()


@router.message(Command("my_progress"))
async def my_progress(message: Message):
    user = await db.get_user(message.from_user.id)
    if not user or user.role != UserRole.CLIENT:
        await message.answer("❌ Эта команда доступна только ученикам.")
        return

    measurements = await db.get_measurements(user.id, days=30)

    if not measurements:
        await message.answer(
            "📊 У вас пока нет замеров.\n\n"
            "Внесите первый замер: /set_measurements"
        )
        return

    last = measurements[-1]
    first = measurements[0]

    response = f"📊 Ваш прогресс за последний месяц:\n\n"
    response += f"📅 Последний замер: {last.measured_at.strftime('%d/%m/%Y %H:%M')}\n\n"

    response += "📝 Текущие замеры:\n"
    if last.weight: response += f"⚖️ Вес: {last.weight:.1f} кг\n"
    if last.waist: response += f"📏 Талия: {last.waist:.1f} см\n"
    if last.hips: response += f"📏 Бедра: {last.hips:.1f} см\n"
    if last.chest: response += f"📏 Грудь: {last.chest:.1f} см\n"
    if last.biceps: response += f"💪 Бицепс: {last.biceps:.1f} см\n"

    if len(measurements) >= 2:
        response += "\n📈 Изменения за месяц:\n"

        if first.weight and last.weight:
            change = last.weight - first.weight
            emoji = "⬇️" if change < 0 else "⬆️" if change > 0 else "➡️"
            response += f"{emoji} Вес: {change:+.1f} кг\n"

        if first.waist and last.waist:
            change = last.waist - first.waist
            emoji = "⬇️" if change < 0 else "⬆️" if change > 0 else "➡️"
            response += f"{emoji} Талия: {change:+.1f} см\n"

        if first.hips and last.hips:
            change = last.hips - first.hips
            emoji = "⬇️" if change < 0 else "⬆️" if change > 0 else "➡️"
            response += f"{emoji} Бедра: {change:+.1f} см\n"

        if first.chest and last.chest:
            change = last.chest - first.chest
            emoji = "⬇️" if change < 0 else "⬆️" if change > 0 else "➡️"
            response += f"{emoji} Грудь: {change:+.1f} см\n"

        if first.biceps and last.biceps:
            change = last.biceps - first.biceps
            emoji = "⬆️" if change > 0 else "⬇️" if change < 0 else "➡️"
            response += f"{emoji} Бицепс: {change:+.1f} см\n"

    await message.answer(response)