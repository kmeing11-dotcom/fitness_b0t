from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from app.models import UserRole
from app.services.db_service import DatabaseService
from app.keyboards.inline import (
    role_keyboard, trainer_menu_keyboard, client_menu_keyboard
)

router = Router()
db = DatabaseService()


class RegistrationStates(StatesGroup):
    choosing_role = State()
    trainer_name = State()
    trainer_phone = State()
    trainer_studio = State()
    client_name = State()
    client_age = State()
    client_height = State()
    client_goal = State()


@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    user = await db.get_user(message.from_user.id)
    
    if user:
        if user.role == UserRole.TRAINER:
            await message.answer(
                f"👋 Добро пожаловать, {user.full_name}!",
                reply_markup=trainer_menu_keyboard()
            )
        else:
            await message.answer(
                f"👋 Добро пожаловать, {user.full_name}!",
                reply_markup=client_menu_keyboard()
            )
        await state.clear()
        return
    
    await message.answer(
        "👋 Добро пожаловать в Fitness CRM Bot!\n\n"
        "Выберите вашу роль:",
        reply_markup=role_keyboard()
    )
    await state.set_state(RegistrationStates.choosing_role)


@router.callback_query(StateFilter(RegistrationStates.choosing_role), F.data == "role_trainer")
async def register_trainer(callback: CallbackQuery, state: FSMContext):
    await callback.message.delete()
    await callback.message.answer("📝 Введите ваше полное имя:")
    await state.update_data(role=UserRole.TRAINER)
    await state.set_state(RegistrationStates.trainer_name)
    await callback.answer()


@router.callback_query(StateFilter(RegistrationStates.choosing_role), F.data == "role_client")
async def register_client(callback: CallbackQuery, state: FSMContext):
    await callback.message.delete()
    await callback.message.answer("📝 Введите ваше полное имя:")
    await state.update_data(role=UserRole.CLIENT)
    await state.set_state(RegistrationStates.client_name)
    await callback.answer()


@router.message(StateFilter(RegistrationStates.trainer_name))
async def process_trainer_name(message: Message, state: FSMContext):
    await state.update_data(full_name=message.text)
    await message.answer("📱 Введите ваш номер телефона (+7XXXXXXXXXX):")
    await state.set_state(RegistrationStates.trainer_phone)


@router.message(StateFilter(RegistrationStates.trainer_phone))
async def process_trainer_phone(message: Message, state: FSMContext):
    await state.update_data(phone=message.text)
    await message.answer("🏢 Введите название вашей студии:")
    await state.set_state(RegistrationStates.trainer_studio)


@router.message(StateFilter(RegistrationStates.trainer_studio))
async def process_trainer_studio(message: Message, state: FSMContext):
    data = await state.get_data()
    user = await db.create_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username or f"user_{message.from_user.id}",
        full_name=data['full_name'],
        role=UserRole.TRAINER,
        phone=data['phone'],
        studio_name=message.text
    )
    await message.answer(
        f"✅ Профиль тренера создан!\n\n"
        f"Имя: {user.full_name}\n"
        f"Телефон: {user.phone}\n"
        f"Студия: {user.studio_name}",
        reply_markup=trainer_menu_keyboard()
    )
    await state.clear()


@router.message(StateFilter(RegistrationStates.client_name))
async def process_client_name(message: Message, state: FSMContext):
    await state.update_data(full_name=message.text)
    await message.answer("🎂 Введите ваш возраст:")
    await state.set_state(RegistrationStates.client_age)


@router.message(StateFilter(RegistrationStates.client_age))
async def process_client_age(message: Message, state: FSMContext):
    try:
        await state.update_data(age=int(message.text))
        await message.answer("📏 Введите ваш рост (в см):")
        await state.set_state(RegistrationStates.client_height)
    except ValueError:
        await message.answer("❌ Пожалуйста, введите корректное число.")


@router.message(StateFilter(RegistrationStates.client_height))
async def process_client_height(message: Message, state: FSMContext):
    try:
        await state.update_data(height=float(message.text.replace(',', '.')))
        await message.answer(
            "🎯 Выберите вашу цель:\n\n"
            "Отправьте одно из слов:\n"
            "• похудение\n"
            "• набор\n"
            "• поддержание"
        )
        await state.set_state(RegistrationStates.client_goal)
    except ValueError:
        await message.answer("❌ Пожалуйста, введите корректное число.")


@router.message(StateFilter(RegistrationStates.client_goal))
async def process_client_goal(message: Message, state: FSMContext):
    goal_map = {
        "похудение": "weight_loss",
        "набор": "muscle_gain",
        "поддержание": "maintain"
    }
    
    goal = goal_map.get(message.text.lower())
    if not goal:
        await message.answer(
            "❌ Пожалуйста, выберите одну из целей:\n"
            "похудение, набор, поддержание"
        )
        return
    
    data = await state.get_data()
    user = await db.create_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username or f"user_{message.from_user.id}",
        full_name=data['full_name'],
        role=UserRole.CLIENT,
        age=data['age'],
        height=data['height'],
        goal=goal
    )
    await message.answer(
        f"✅ Профиль ученика создан!\n\n"
        f"Имя: {user.full_name}\n"
        f"Возраст: {user.age}\n"
        f"Рост: {user.height} см\n"
        f"Цель: {message.text.capitalize()}",
        reply_markup=client_menu_keyboard()
    )
    await state.clear()