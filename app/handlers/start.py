# app/handlers/start.py
from aiogram import Router, F
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
)
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.enums import ParseMode
import re
import traceback

from app.models import UserRole
from app.services.db_service import DatabaseService
from app.keyboards.inline import (
    get_role_keyboard,
    get_trainer_menu_keyboard,
    get_client_menu_keyboard,
    get_cancel_keyboard,
    get_goal_inline_keyboard,
    get_back_inline_keyboard
)
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = Router()
db = DatabaseService()


# ============================================================
#  СПИСОК РЕГИОНОВ
# ============================================================

TIMEZONE_CHOICES = [
    ("Europe/Kaliningrad", "Калининград (UTC+2)"),
    ("Europe/Moscow", "Москва (UTC+3)"),
    ("Europe/Samara", "Самара (UTC+4)"),
    ("Asia/Yekaterinburg", "Екатеринбург (UTC+5)"),
    ("Asia/Omsk", "Омск (UTC+6)"),
    ("Asia/Novosibirsk", "Новосибирск (UTC+7)"),
    ("Asia/Irkutsk", "Иркутск (UTC+8)"),
    ("Asia/Yakutsk", "Якутск (UTC+9)"),
    ("Asia/Vladivostok", "Владивосток (UTC+10)"),
    ("Asia/Magadan", "Магадан (UTC+11)"),
    ("Asia/Kamchatka", "Камчатка (UTC+12)"),
]


def get_timezone_keyboard(page: int = 0) -> InlineKeyboardMarkup:
    """Клавиатура с выбором таймзоны (пагинация по 5)."""
    per_page = 5
    total = len(TIMEZONE_CHOICES)
    start = page * per_page
    end = min(start + per_page, total)

    kb = []
    for tz_code, tz_label in TIMEZONE_CHOICES[start:end]:
        kb.append([
            InlineKeyboardButton(
                text=tz_label,
                callback_data=f"tz_{tz_code}"
            )
        ])

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"tzpage_{page - 1}"))
    if end < total:
        nav.append(InlineKeyboardButton(text="➡️", callback_data=f"tzpage_{page + 1}"))
    if nav:
        kb.append(nav)

    kb.append([
        InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_registration")
    ])

    return InlineKeyboardMarkup(inline_keyboard=kb)


# ============================================================
#  FSM
# ============================================================

class RegistrationStates(StatesGroup):
    choosing_role = State()
    trainer_name = State()
    trainer_phone = State()
    trainer_studio = State()
    trainer_timezone = State()
    client_name = State()
    client_age = State()
    client_height = State()
    client_goal = State()


# ============================================================
#  /start
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
#  ОБЩАЯ ОТМЕНА РЕГИСТРАЦИИ
# ============================================================

@router.message(
    StateFilter(
        RegistrationStates.trainer_name,
        RegistrationStates.trainer_phone,
        RegistrationStates.trainer_studio,
        RegistrationStates.client_name,
        RegistrationStates.client_age,
        RegistrationStates.client_height,
    ),
    F.text.in_({"🔙 Назад", "❌ Отмена"})
)
async def cancel_registration_any_step(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "❌ Регистрация отменена.\nИспользуйте /start заново."
    )


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
        await message.answer("❌ Ошибка.")


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
        await message.answer("❌ Ошибка.")


@router.message(StateFilter(RegistrationStates.trainer_studio))
async def process_trainer_studio(message: Message, state: FSMContext):
    try:
        studio = message.text.strip()
        await state.update_data(studio=studio)

        await message.answer(
            "🌍 <b>Выберите ваш часовой пояс</b>\n\n"
            "Это важно: напоминания ученикам будут приходить "
            "по выбранному вами времени.",
            parse_mode=ParseMode.HTML,
            reply_markup=get_timezone_keyboard(page=0)
        )
        await state.set_state(RegistrationStates.trainer_timezone)

    except Exception as e:
        logger.error(f"Error in process_trainer_studio: {e}\n{traceback.format_exc()}")
        await message.answer(f"❌ Ошибка: {str(e)[:200]}")


# ============================================================
#  ПАГИНАЦИЯ ТАЙМЗОН
# ============================================================

@router.callback_query(
    StateFilter(RegistrationStates.trainer_timezone),
    F.data.startswith("tzpage_")
)
async def process_timezone_page(callback: CallbackQuery, state: FSMContext):
    try:
        page = int(callback.data.split("_")[1])
        await callback.message.edit_reply_markup(
            reply_markup=get_timezone_keyboard(page=page)
        )
        await callback.answer()
    except Exception as e:
        logger.error(f"Error in process_timezone_page: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


# ============================================================
#  ВЫБОР ТАЙМЗОНЫ → СОЗДАНИЕ ТРЕНЕРА
# ============================================================

@router.callback_query(
    StateFilter(RegistrationStates.trainer_timezone),
    F.data.startswith("tz_")
)
async def process_trainer_timezone(callback: CallbackQuery, state: FSMContext):
    try:
        # FIX: tz_Europe/Moscow → Europe/Moscow
        timezone = callback.data.replace("tz_", "", 1)

        data = await state.get_data()
        studio = data.get('studio', 'Нет')

        user = db.create_user(
            telegram_id=callback.from_user.id,
            username=callback.from_user.username or f"user_{callback.from_user.id}",
            full_name=data.get('full_name', 'Тренер'),
            role=UserRole.TRAINER,
            phone=data.get('phone', ''),
            studio_name=studio if studio.lower() != 'нет' else None,
            timezone=timezone
        )

        if not user:
            await callback.message.edit_text("❌ Не удалось создать профиль.")
            await callback.answer()
            await state.clear()
            return

        # Находим человекочитаемое название таймзоны
        tz_label = dict(TIMEZONE_CHOICES).get(timezone, timezone)

        # Редактируем сообщение с выбором → убираем кнопки
        await callback.message.edit_text(
            f"✅ <b>Профиль тренера создан!</b>\n\n"
            f"👤 Имя: {user['full_name']}\n"
            f"📱 Телефон: {user['phone'] or 'Не указан'}\n"
            f"🏢 Студия: {user['studio_name'] or 'Не указана'}\n"
            f"🌍 Регион: {tz_label}",
            parse_mode=ParseMode.HTML
        )

        # Отправляем Reply-меню
        await callback.message.answer(
            "👇 Используйте меню ниже:",
            reply_markup=get_trainer_menu_keyboard()
        )

        await state.clear()
        await callback.answer("✅ Регистрация завершена!")

        logger.info(
            f"✅ Trainer registered: id={user['id']}, tz={timezone}"
        )

    except Exception as e:
        logger.error(f"Error in process_trainer_timezone: {e}\n{traceback.format_exc()}")
        await callback.answer("❌ Ошибка", show_alert=True)
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
        await message.answer("❌ Ошибка.")


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
#  ВЫБОР ЦЕЛИ УЧЕНИКА
# ============================================================

@router.callback_query(F.data.startswith("goal_"))
async def process_client_goal_callback(callback: CallbackQuery, state: FSMContext):
    try:
        goal = callback.data.replace("goal_", "", 1)
        logger.info(f"📥 [goal_] goal='{goal}'")

        await _finish_client_registration(
            callback=callback,
            state=state,
            goal=goal,
            user_id=callback.from_user.id,
            username=callback.from_user.username or f"user_{callback.from_user.id}"
        )

    except Exception as e:
        logger.error(f"Error in process_client_goal_callback: {e}\n{traceback.format_exc()}")
        await callback.answer("❌ Ошибка", show_alert=True)


@router.callback_query(F.data == "cancel_registration")
async def cancel_registration_callback(callback: CallbackQuery, state: FSMContext):
    try:
        await state.clear()
        await callback.message.edit_text(
            "❌ Регистрация отменена.\n"
            "Если захотите зарегистрироваться позже, используйте /start."
        )
        await callback.answer()
    except Exception as e:
        logger.error(f"Error in cancel_registration_callback: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


async def _finish_client_registration(
    callback: CallbackQuery,
    state: FSMContext,
    goal: str,
    user_id: int,
    username: str
):
    try:
        valid_goals = ["weight_loss", "muscle_gain", "maintain"]
        if goal not in valid_goals:
            await callback.message.edit_text(
                "❌ Неверная цель. Попробуйте ещё раз.",
                reply_markup=get_goal_inline_keyboard()
            )
            return

        data = await state.get_data()

        user = db.create_user(
            telegram_id=user_id,
            username=username,
            full_name=data.get('full_name', 'Ученик'),
            role=UserRole.CLIENT,
            age=data.get('age', 0),
            height=data.get('height', 0),
            goal=goal
        )

        if not user:
            await callback.message.edit_text("❌ Не удалось создать профиль.")
            await callback.answer()
            return

        goal_ru = {
            "weight_loss": "Похудение",
            "muscle_gain": "Набор массы",
            "maintain": "Поддержание"
        }.get(goal, goal)

        await callback.message.edit_text(
            f"✅ Профиль ученика создан!\n\n"
            f"👤 Имя: {user['full_name']}\n"
            f"🎂 Возраст: {user['age']} лет\n"
            f"📏 Рост: {user['height']} см\n"
            f"🎯 Цель: {goal_ru}"
        )

        await callback.message.answer(
            "👇 Используйте меню ниже:",
            reply_markup=get_client_menu_keyboard()
        )

        await state.clear()
        await callback.answer("✅ Регистрация завершена!")

    except Exception as e:
        logger.error(f"Error in _finish_client_registration: {e}\n{traceback.format_exc()}")
        await callback.message.answer(f"❌ Ошибка: {str(e)[:200]}")
        await state.clear()
        await callback.answer("❌ Ошибка", show_alert=True)


# ============================================================
#  /myid
# ============================================================

@router.message(Command("myid"))
async def cmd_myid(message: Message):
    try:
        user = db.get_user_by_telegram(message.from_user.id)

        text = f"🆔 <b>Твой Telegram ID:</b> <code>{message.from_user.id}</code>\n"
        text += f"👤 Username: @{message.from_user.username or 'не указан'}\n"
        text += f"📛 Имя: {message.from_user.full_name}\n"

        if user:
            text += f"\n✅ <b>Ты зарегистрирован в боте</b>\n"
            text += f"🎯 Роль: {user['role']}\n"
            text += f"📛 Имя в профиле: {user['full_name']}\n"
            if user.get('timezone'):
                text += f"🌍 Регион: {user['timezone']}\n"
        else:
            text += f"\n❌ <b>Ты НЕ зарегистрирован в боте</b>\n"
            text += f"Используй /start для регистрации"

        await message.answer(text, parse_mode=ParseMode.HTML)

    except Exception as e:
        logger.error(f"Error in cmd_myid: {e}\n{traceback.format_exc()}")
        await message.answer(
            f"🆔 Твой Telegram ID: <code>{message.from_user.id}</code>",
            parse_mode=ParseMode.HTML
        )
