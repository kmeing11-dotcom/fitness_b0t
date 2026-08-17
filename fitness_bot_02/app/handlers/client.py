from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from app.services.db_service import DatabaseService
from app.keyboards.inline import client_menu_keyboard
from app.db import get_db
from app.models import UserRole

router = Router()

class MeasurementStates(StatesGroup):
    weight = State()
    waist = State()
    hips = State()
    chest = State()
    biceps = State()

@router.message(F.text == "📝 Внести замеры")
async def start_measurements(message: Message, state: FSMContext):
    db = DatabaseService(next(get_db()))
    user = db.get_user(message.from_user.id)
    if not user or user.role != UserRole.CLIENT:
        await message.answer("❌ Только для учеников.")
        return
    await message.answer("⚖️ Введите вес (в кг) или 'пропустить':")
    await state.set_state(MeasurementStates.weight)

@router.message(StateFilter(MeasurementStates.weight))
async def process_weight(message: Message, state: FSMContext):
    if message.text.lower() == "пропустить":
        await state.update_data(weight=None)
    else:
        try:
            await state.update_data(weight=float(message.text.replace(',', '.')))
        except ValueError:
            await message.answer("❌ Введите число или 'пропустить'.")
            return
    await message.answer("📏 Введите обхват талии (см) или 'пропустить':")
    await state.set_state(MeasurementStates.waist)

@router.message(StateFilter(MeasurementStates.waist))
async def process_waist(message: Message, state: FSMContext):
    if message.text.lower() == "пропустить":
        await state.update_data(waist=None)
    else:
        try:
            await state.update_data(waist=float(message.text.replace(',', '.')))
        except ValueError:
            await message.answer("❌ Введите число или 'пропустить'.")
            return
    await message.answer("📏 Введите обхват бедер (см) или 'пропустить':")
    await state.set_state(MeasurementStates.hips)

# ... аналогично для hips, chest, biceps (копируй логику выше, меняя названия)

@router.message(StateFilter(MeasurementStates.biceps))
async def process_biceps(message: Message, state: FSMContext):
    if message.text.lower() == "пропустить":
        await state.update_data(biceps=None)
    else:
        try:
            await state.update_data(biceps=float(message.text.replace(',', '.')))
        except ValueError:
            await message.answer("❌ Введите число или 'пропустить'.")
            return
    data = await state.get_data()
    db = DatabaseService(next(get_db()))
    user = db.get_user(message.from_user.id)
    measurement_data = {k: v for k, v in data.items() if v is not None}
    if measurement_data:
        db.create_measurement(user.id, measurement_data)
        await message.answer("✅ Замеры сохранены!", reply_markup=client_menu_keyboard())
    else:
        await message.answer("❌ Ни одного замера не введено.", reply_markup=client_menu_keyboard())
    await state.clear()