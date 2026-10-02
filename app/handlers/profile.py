# app/handlers/profile.py
from aiogram import Router, F
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.enums import ParseMode
import re
import traceback

from app.services.db_service import DatabaseService
from app.models import UserRole
from app.keyboards.inline import (
    get_cancel_keyboard,
    get_back_inline_keyboard,
    get_trainer_menu_keyboard,
    get_client_menu_keyboard,
    get_goal_inline_keyboard
)
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = Router()
db = DatabaseService()

CANCEL_TEXTS = ("🔙 Назад", "❌ Отмена")


# ============================================================
#  СОСТОЯНИЯ
# ============================================================

class EditProfileStates(StatesGroup):
    # тренер
    trainer_name = State()
    trainer_phone = State()
    trainer_studio = State()
    # ученик
    client_name = State()
    client_age = State()
    client_height = State()


class DeleteAccountStates(StatesGroup):
    confirming = State()


# ============================================================
#  /edit_profile
# ============================================================

@router.message(Command("edit_profile"))
async def edit_profile(message: Message, state: FSMContext):
    try:
        user = db.get_user_by_telegram(message.from_user.id)
        if not user:
            await message.answer("❌ Вы не зарегистрированы. Используйте /start.")
            return

        await state.clear()

        if user['role'] == UserRole.TRAINER.value:
            await message.answer(
                f"✏️ <b>Редактирование профиля тренера</b>\n\n"
                f"Текущее имя: <b>{user['full_name'] or '—'}</b>\n\n"
                f"Введите новое имя (или «🔙 Назад» для отмены):",
                parse_mode=ParseMode.HTML,
                reply_markup=get_cancel_keyboard()
            )
            await state.set_state(EditProfileStates.trainer_name)
        else:
            await message.answer(
                f"✏️ <b>Редактирование профиля ученика</b>\n\n"
                f"Текущее имя: <b>{user['full_name'] or '—'}</b>\n\n"
                f"Введите новое имя (или «🔙 Назад» для отмены):",
                parse_mode=ParseMode.HTML,
                reply_markup=get_cancel_keyboard()
            )
            await state.set_state(EditProfileStates.client_name)

    except Exception as e:
        logger.error(f"Error in edit_profile: {e}\n{traceback.format_exc()}")
        await message.answer("❌ Ошибка при запуске редактирования.")


# ============================================================
#  ТРЕНЕР — ШАГ 1: ИМЯ
# ============================================================

@router.message(StateFilter(EditProfileStates.trainer_name))
async def edit_trainer_name(message: Message, state: FSMContext):
    try:
        if message.text in CANCEL_TEXTS:
            await state.clear()
            await message.answer("❌ Редактирование отменено.")
            return

        if not message.text or len(message.text.strip()) < 2:
            await message.answer("❌ Имя должно содержать минимум 2 символа:")
            return

        await state.update_data(full_name=message.text.strip())
        await message.answer(
            "📱 Введите новый телефон (или введите «-», чтобы оставить текущий):",
            reply_markup=get_cancel_keyboard()
        )
        await state.set_state(EditProfileStates.trainer_phone)

    except Exception as e:
        logger.error(f"Error in edit_trainer_name: {e}")
        await message.answer("❌ Ошибка.")


@router.message(StateFilter(EditProfileStates.trainer_phone))
async def edit_trainer_phone(message: Message, state: FSMContext):
    try:
        if message.text in CANCEL_TEXTS:
            await state.clear()
            await message.answer("❌ Редактирование отменено.")
            return

        if message.text.strip() != "-":
            phone = message.text.strip()
            phone_clean = re.sub(r'[\s\-()]', '', phone)
            if not re.match(r'^\+?\d{10,15}$', phone_clean):
                await message.answer(
                    "❌ Неверный формат телефона. Пример: +79991234567\n"
                    "Или введите «-», чтобы оставить текущий.",
                    reply_markup=get_cancel_keyboard()
                )
                return
            await state.update_data(phone=phone)

        await message.answer(
            "🏢 Введите новое название студии (или «-», чтобы оставить текущее):",
            reply_markup=get_cancel_keyboard()
        )
        await state.set_state(EditProfileStates.trainer_studio)

    except Exception as e:
        logger.error(f"Error in edit_trainer_phone: {e}")
        await message.answer("❌ Ошибка.")


@router.message(StateFilter(EditProfileStates.trainer_studio))
async def edit_trainer_studio(message: Message, state: FSMContext):
    try:
        if message.text in CANCEL_TEXTS:
            await state.clear()
            await message.answer("❌ Редактирование отменено.")
            return

        data = await state.get_data()
        user = db.get_user_by_telegram(message.from_user.id)
        if not user:
            await message.answer("❌ Пользователь не найден.")
            await state.clear()
            return

        update_kwargs = {"full_name": data.get('full_name')}
        if "phone" in data:
            update_kwargs["phone"] = data["phone"]

        studio = message.text.strip()
        if studio != "-":
            update_kwargs["studio_name"] = studio if studio.lower() != 'нет' else None

        db.update_user(user['id'], **update_kwargs)
        updated = db.get_user(user['id'])

        await message.answer(
            f"✅ <b>Профиль обновлён!</b>\n\n"
            f"👤 Имя: {updated['full_name']}\n"
            f"📱 Телефон: {updated['phone'] or 'Не указан'}\n"
            f"🏢 Студия: {updated['studio_name'] or 'Не указана'}\n"
            f"🌍 Регион: {updated.get('timezone', 'Europe/Moscow')}",
            parse_mode=ParseMode.HTML,
            reply_markup=get_trainer_menu_keyboard()
        )
        await state.clear()
        logger.info(f"✏️ Trainer {user['id']} updated profile")

    except Exception as e:
        logger.error(f"Error in edit_trainer_studio: {e}\n{traceback.format_exc()}")
        await message.answer("❌ Ошибка при сохранении.")
        await state.clear()


# ============================================================
#  УЧЕНИК — ШАГ 1: ИМЯ
# ============================================================

@router.message(StateFilter(EditProfileStates.client_name))
async def edit_client_name(message: Message, state: FSMContext):
    try:
        if message.text in CANCEL_TEXTS:
            await state.clear()
            await message.answer("❌ Редактирование отменено.")
            return

        if not message.text or len(message.text.strip()) < 2:
            await message.answer("❌ Имя должно содержать минимум 2 символа:")
            return

        await state.update_data(full_name=message.text.strip())
        await message.answer(
            "🎂 Введите новый возраст (или «-», чтобы оставить текущий):",
            reply_markup=get_cancel_keyboard()
        )
        await state.set_state(EditProfileStates.client_age)

    except Exception as e:
        logger.error(f"Error in edit_client_name: {e}")
        await message.answer("❌ Ошибка.")


@router.message(StateFilter(EditProfileStates.client_age))
async def edit_client_age(message: Message, state: FSMContext):
    try:
        if message.text in CANCEL_TEXTS:
            await state.clear()
            await message.answer("❌ Редактирование отменено.")
            return

        if message.text.strip() != "-":
            try:
                age = int(message.text.strip())
            except ValueError:
                await message.answer(
                    "❌ Введите число от 10 до 120, или «-»:",
                    reply_markup=get_cancel_keyboard()
                )
                return

            if age < 10 or age > 120:
                await message.answer(
                    "❌ Возраст от 10 до 120 лет.",
                    reply_markup=get_cancel_keyboard()
                )
                return
            await state.update_data(age=age)

        await message.answer(
            "📏 Введите новый рост (или «-», чтобы оставить текущий):",
            reply_markup=get_cancel_keyboard()
        )
        await state.set_state(EditProfileStates.client_height)

    except Exception as e:
        logger.error(f"Error in edit_client_age: {e}")
        await message.answer("❌ Ошибка.")


@router.message(StateFilter(EditProfileStates.client_height))
async def edit_client_height(message: Message, state: FSMContext):
    try:
        if message.text in CANCEL_TEXTS:
            await state.clear()
            await message.answer("❌ Редактирование отменено.")
            return

        if message.text.strip() != "-":
            try:
                height = float(message.text.strip().replace(',', '.'))
            except ValueError:
                await message.answer(
                    "❌ Введите число от 50 до 300, или «-»:",
                    reply_markup=get_cancel_keyboard()
                )
                return

            if height < 50 or height > 300:
                await message.answer(
                    "❌ Рост от 50 до 300 см.",
                    reply_markup=get_cancel_keyboard()
                )
                return
            await state.update_data(height=height)

        data = await state.get_data()
        user = db.get_user_by_telegram(message.from_user.id)
        if not user:
            await message.answer("❌ Пользователь не найден.")
            await state.clear()
            return

        update_kwargs = {"full_name": data.get('full_name')}
        if "age" in data:
            update_kwargs["age"] = data["age"]
        if "height" in data:
            update_kwargs["height"] = data["height"]

        db.update_user(user['id'], **update_kwargs)
        updated = db.get_user(user['id'])

        await message.answer(
            f"✅ <b>Профиль обновлён!</b>\n\n"
            f"👤 Имя: {updated['full_name']}\n"
            f"🎂 Возраст: {updated['age'] or '—'} лет\n"
            f"📏 Рост: {updated['height'] or '—'} см\n"
            f"🎯 Цель: {updated['goal'] or '—'}",
            parse_mode=ParseMode.HTML,
            reply_markup=get_client_menu_keyboard()
        )
        await state.clear()
        logger.info(f"✏️ Client {user['id']} updated profile")

    except Exception as e:
        logger.error(f"Error in edit_client_height: {e}\n{traceback.format_exc()}")
        await message.answer("❌ Ошибка при сохранении.")
        await state.clear()


# ============================================================
#  /delete_account
# ============================================================

@router.message(Command("delete_account"))
async def delete_account(message: Message, state: FSMContext):
    try:
        user = db.get_user_by_telegram(message.from_user.id)
        if not user:
            await message.answer("❌ Вы не зарегистрированы.")
            return

        await state.clear()

        text = (
            f"⚠️ <b>Удаление аккаунта</b>\n\n"
            f"Вы уверены, что хотите <b>удалить аккаунт</b>?\n\n"
            f"<b>Это действие:</b>\n"
            f"• Удалит ваш профиль\n"
            f"• Удалит все замеры\n"
            f"• Удалит напоминания и связи с тренерами/учениками\n\n"
            f"<i>Действие необратимо.</i>"
        )

        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="✅ Да, удалить аккаунт",
                        callback_data="confirm_delete_account"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="❌ Отмена",
                        callback_data="cancel_delete_account"
                    )
                ]
            ]
        )

        await message.answer(text, parse_mode=ParseMode.HTML, reply_markup=kb)
        await state.set_state(DeleteAccountStates.confirming)

    except Exception as e:
        logger.error(f"Error in delete_account: {e}\n{traceback.format_exc()}")
        await message.answer("❌ Ошибка.")


@router.callback_query(F.data == "confirm_delete_account")
async def confirm_delete_account(callback: CallbackQuery, state: FSMContext):
    try:
        user = db.get_user_by_telegram(callback.from_user.id)
        if not user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return

        user_id = user['id']

        # Удаляем связанные данные
        try:
            # Сначала снимем связи
            from app.db import Session
            from app.models import (
                TrainerClient, Measurement, Reminder, ReminderLog, Subscription
            )

            with Session() as session:
                # TrainerClient (trainer и/или client)
                session.query(TrainerClient).filter(
                    (TrainerClient.trainer_id == user_id) |
                    (TrainerClient.client_id == user_id)
                ).delete(synchronize_session=False)

                # Measurements
                session.query(Measurement).filter(
                    Measurement.user_id == user_id
                ).delete(synchronize_session=False)

                # ReminderLog
                session.query(ReminderLog).filter(
                    ReminderLog.client_id == user_id
                ).delete(synchronize_session=False)

                # Reminders (если тренер)
                session.query(Reminder).filter(
                    Reminder.trainer_id == user_id
                ).delete(synchronize_session=False)

                # Subscription
                session.query(Subscription).filter(
                    Subscription.user_id == user_id
                ).delete(synchronize_session=False)

                # User
                from app.models import User
                session.query(User).filter(User.id == user_id).delete(
                    synchronize_session=False
                )
                session.commit()
        except Exception as e:
            logger.error(f"DB delete error: {e}\n{traceback.format_exc()}")
            await callback.message.edit_text(
                "❌ Ошибка при удалении данных. Обратитесь в поддержку."
            )
            await callback.answer()
            await state.clear()
            return

        await callback.message.edit_text(
            "✅ <b>Аккаунт удалён.</b>\n\n"
            "Все ваши данные стёрты.\n"
            "Если захотите начать заново — используйте /start.",
            parse_mode=ParseMode.HTML
        )
        await callback.answer("✅ Аккаунт удалён")
        await state.clear()

        logger.info(f"🗑️ Account deleted: user_id={user_id}")

    except Exception as e:
        logger.error(f"Error in confirm_delete_account: {e}\n{traceback.format_exc()}")
        await callback.answer("❌ Ошибка", show_alert=True)
        await state.clear()


@router.callback_query(F.data == "cancel_delete_account")
async def cancel_delete_account(callback: CallbackQuery, state: FSMContext):
    try:
        await state.clear()
        await callback.message.edit_text(
            "❌ Удаление аккаунта отменено.",
            reply_markup=get_back_inline_keyboard("back_to_menu")
        )
        await callback.answer()
    except Exception as e:
        logger.error(f"Error in cancel_delete_account: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)
