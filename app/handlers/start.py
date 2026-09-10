from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.enums import ParseMode
from app.models import UserRole
from app.services.db_service import DatabaseService
from app.keyboards.inline import (
    get_role_keyboard,
    get_trainer_menu_keyboard,
    get_client_menu_keyboard,
    get_cancel_keyboard,
    get_back_keyboard,
    get_goal_inline_keyboard
)
from app.utils.logger import get_logger
import re
import traceback

logger = get_logger(__name__)
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


# ============================================================
#  КОМАНДА /start
# ============================================================

@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    try:
        user = db.get_user_by_telegram(message.from_user.id)
        
        if user:
            await state.clear()
            if user['role'] == UserRole.TRAINER.value:
                await message.answer(
                    f"👋 С возвращением, {user['full_name'] or 'Тренер'}!",
                    reply_markup=get_trainer_menu_keyboard()
                )
            else:
                await message.answer(
                    f"👋 С возвращением, {user['full_name'] or 'Ученик'}!",
                    reply_markup=get_client_menu_keyboard()
                )
            return

        await message.answer(
            "👋 Добро пожаловать в Fitness CRM Bot!\n\n"
            "👇 Выберите вашу роль:",
            reply_markup=get_role_keyboard()
        )
        await state.set_state(RegistrationStates.choosing_role)

    except Exception as e:
        logger.error(f"Error in cmd_start: {e}\n{traceback.format_exc()}")
        await message.answer(f"❌ Ошибка: {str(e)[:200]}")


# ============================================================
#  ВЫБОР РОЛИ
# ============================================================

@router.message(StateFilter(RegistrationStates.choosing_role), F.text == "👨‍🏫 Тренер")
async def register_trainer(message: Message, state: FSMContext):
    try:
        await state.update_data(role=UserRole.TRAINER)
        await message.answer(
            "📝 Введите ваше полное имя:",
            reply_markup=get_cancel_keyboard()
        )
        await state.set_state(RegistrationStates.trainer_name)
    except Exception as e:
        logger.error(f"Error in register_trainer: {e}")
        await message.answer("❌ Ошибка. Попробуйте ещё раз.")


@router.message(StateFilter(RegistrationStates.choosing_role), F.text == "👤 Ученик")
async def register_client(message: Message, state: FSMContext):
    try:
        await state.update_data(role=UserRole.CLIENT)
        await message.answer(
            "📝 Введите ваше полное имя:",
            reply_markup=get_cancel_keyboard()
        )
        await state.set_state(RegistrationStates.client_name)
    except Exception as e:
        logger.error(f"Error in register_client: {e}")
        await message.answer("❌ Ошибка. Попробуйте ещё раз.")


# ============================================================
#  РЕГИСТРАЦИЯ ТРЕНЕРА
# ============================================================

@router.message(StateFilter(RegistrationStates.trainer_name))
async def process_trainer_name(message: Message, state: FSMContext):
    try:
        if not message.text or len(message.text.strip()) < 2:
            await message.answer("❌ Имя должно содержать минимум 2 символа:")
            return

        await state.update_data(full_name=message.text.strip())
        await message.answer(
            "📱 Введите номер телефона (пример: +79991234567):",
            reply_markup=get_cancel_keyboard()
        )
        await state.set_state(RegistrationStates.trainer_phone)
    except Exception as e:
        logger.error(f"Error in process_trainer_name: {e}")
        await message.answer("❌ Ошибка. Попробуйте ещё раз.")


@router.message(StateFilter(RegistrationStates.trainer_phone))
async def process_trainer_phone(message: Message, state: FSMContext):
    try:
        phone = message.text.strip()
        phone_clean = re.sub(r'[\s\-()]', '', phone)
        if not re.match(r'^\+?\d{10,15}$', phone_clean):
            await message.answer(
                "❌ Неверный формат телефона. Пример: +79991234567",
                reply_markup=get_cancel_keyboard()
            )
            return

        await state.update_data(phone=phone)
        await message.answer(
            "🏢 Введите название студии (или 'Нет'):",
            reply_markup=get_cancel_keyboard()
        )
        await state.set_state(RegistrationStates.trainer_studio)
    except Exception as e:
        logger.error(f"Error in process_trainer_phone: {e}")
        await message.answer("❌ Ошибка. Попробуйте ещё раз.")


@router.message(StateFilter(RegistrationStates.trainer_studio))
async def process_trainer_studio(message: Message, state: FSMContext):
    try:
        data = await state.get_data()
        studio = message.text.strip()

        user = db.create_user(
            telegram_id=message.from_user.id,
            username=message.from_user.username or f"user_{message.from_user.id}",
            full_name=data.get('full_name', 'Тренер'),
            role=UserRole.TRAINER,
            phone=data.get('phone', ''),
            studio_name=studio if studio.lower() != 'нет' else None
        )

        if not user:
            await message.answer("❌ Не удалось создать профиль.")
            return

        await message.answer(
            f"✅ Профиль тренера создан!\n\n"
            f"👤 Имя: {user['full_name']}\n"
            f"📱 Телефон: {user['phone'] or 'Не указан'}\n"
            f"🏢 Студия: {user['studio_name'] or 'Не указана'}",
            reply_markup=get_trainer_menu_keyboard()
        )
        await state.clear()

    except Exception as e:
        logger.error(f"Error in process_trainer_studio: {e}\n{traceback.format_exc()}")
        await message.answer(f"❌ Ошибка: {str(e)[:200]}", reply_markup=get_cancel_keyboard())
        await state.clear()


# ============================================================
#  РЕГИСТРАЦИЯ УЧЕНИКА
# ============================================================

@router.message(StateFilter(RegistrationStates.client_name))
async def process_client_name(message: Message, state: FSMContext):
    try:
        if not message.text or len(message.text.strip()) < 2:
            await message.answer("❌ Имя должно содержать минимум 2 символа:")
            return

        await state.update_data(full_name=message.text.strip())
        await message.answer(
            "🎂 Введите ваш возраст:",
            reply_markup=get_cancel_keyboard()
        )
        await state.set_state(RegistrationStates.client_age)
    except Exception as e:
        logger.error(f"Error in process_client_name: {e}")
        await message.answer("❌ Ошибка. Попробуйте ещё раз.")


@router.message(StateFilter(RegistrationStates.client_age))
async def process_client_age(message: Message, state: FSMContext):
    try:
        age = int(message.text.strip())
        if age < 10 or age > 120:
            await message.answer(
                "❌ Возраст должен быть от 10 до 120 лет.",
                reply_markup=get_cancel_keyboard()
            )
            return

        await state.update_data(age=age)
        await message.answer(
            "📏 Введите ваш рост (в см):",
            reply_markup=get_cancel_keyboard()
        )
        await state.set_state(RegistrationStates.client_height)

    except ValueError:
        await message.answer("❌ Введите число.", reply_markup=get_cancel_keyboard())


@router.message(StateFilter(RegistrationStates.client_height))
async def process_client_height(message: Message, state: FSMContext):
    try:
        height = float(message.text.strip().replace(',', '.'))
        if height < 50 or height > 300:
            await message.answer(
                "❌ Рост должен быть от 50 до 300 см.",
                reply_markup=get_cancel_keyboard()
            )
            return

        await state.update_data(height=height)
        await message.answer(
            "🎯 Выберите цель:",
            reply_markup=get_goal_inline_keyboard()
        )
        await state.set_state(RegistrationStates.client_goal)

    except ValueError:
        await message.answer("❌ Введите число.", reply_markup=get_cancel_keyboard())


# ============================================================
#  ОБРАБОТКА ВЫБОРА ЦЕЛИ
# ============================================================

@router.callback_query(F.data.startswith("goal_"))
async def process_client_goal_callback(callback: CallbackQuery, state: FSMContext):
    try:
        logger.info(f"📥 [process_client_goal_callback] data: {callback.data}")
        
        # Правильный парсинг: убираем "goal_" из callback_data
        # goal_weight_loss -> weight_loss
        # goal_muscle_gain -> muscle_gain
        # goal_maintain -> maintain
        goal = callback.data[5:]  # отрезаем "goal_"
        logger.info(f"📥 Goal after slice: '{goal}'")
        
        await _finish_client_registration(callback.message, state, goal, callback=callback)
    except Exception as e:
        logger.error(f"Error in process_client_goal_callback: {e}\n{traceback.format_exc()}")
        await callback.answer("❌ Ошибка", show_alert=True)


@router.callback_query(F.data == "cancel_registration")
async def cancel_registration_callback(callback: CallbackQuery, state: FSMContext):
    try:
        await state.clear()
        await callback.message.edit_text(
            "❌ Регистрация отменена.\n"
            "Если захотите зарегистрироваться позже, используйте /start.",
            reply_markup=get_back_keyboard()
        )
        await callback.answer()
    except Exception as e:
        logger.error(f"Error in cancel_registration_callback: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


async def _finish_client_registration(
    message: Message,
    state: FSMContext,
    goal: str,
    callback: CallbackQuery = None
):
    try:
        logger.info(f"🔍 [_finish_client_registration] goal received: '{goal}'")

        # Простая проверка — если goal один из трёх, всё ок
        valid_goals = ["weight_loss", "muscle_gain", "maintain"]
        
        if goal not in valid_goals:
            logger.error(f"❌ Invalid goal: '{goal}'. Valid: {valid_goals}")
            await message.answer("❌ Неверная цель.", reply_markup=get_goal_inline_keyboard())
            return

        logger.info(f"✅ Goal '{goal}' is valid")

        data = await state.get_data()

        user = db.create_user(
            telegram_id=message.from_user.id,
            username=message.from_user.username or f"user_{message.from_user.id}",
            full_name=data.get('full_name', 'Ученик'),
            role=UserRole.CLIENT,
            age=data.get('age', 0),
            height=data.get('height', 0),
            goal=goal
        )

        if not user:
            await message.answer("❌ Не удалось создать профиль.")
            return

        goal_ru = {
            "weight_loss": "Похудение",
            "muscle_gain": "Набор массы",
            "maintain": "Поддержание"
        }.get(goal, goal)

        await message.answer(
            f"✅ Профиль ученика создан!\n\n"
            f"👤 Имя: {user['full_name']}\n"
            f"🎂 Возраст: {user['age']} лет\n"
            f"📏 Рост: {user['height']} см\n"
            f"🎯 Цель: {goal_ru}",
            reply_markup=get_client_menu_keyboard()
        )
        await state.clear()

        if callback:
            await callback.answer()

    except Exception as e:
        logger.error(f"Error in _finish_client_registration: {e}\n{traceback.format_exc()}")
        await message.answer(f"❌ Ошибка: {str(e)[:200]}", reply_markup=get_cancel_keyboard())
        await state.clear()
        if callback:
            await callback.answer("❌ Ошибка", show_alert=True)
