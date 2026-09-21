# app/handlers/client.py
from aiogram import Router, F
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton,
    BufferedInputFile, FSInputFile
)
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.enums import ParseMode
from datetime import datetime
import traceback

from app.services.db_service import DatabaseService
from app.models import UserRole
from app.keyboards.inline import (
    get_clients_list_keyboard,
    get_client_actions_keyboard,
    get_confirm_delete_keyboard,
    get_back_inline_keyboard,
    get_trainer_menu_keyboard,
    get_cancel_keyboard
)
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = Router()
db = DatabaseService()


class MessageStates(StatesGroup):
    waiting_for_message = State()


# ============================================================
#  /add_client
# ============================================================

@router.message(Command("add_client"))
async def add_client(message: Message):
    try:
        user = db.get_user_by_telegram(message.from_user.id)
        if not user:
            await message.answer("❌ Вы не зарегистрированы. Используйте /start.")
            return

        if user['role'] != UserRole.TRAINER.value:
            await message.answer("❌ Эта команда доступна только тренерам.")
            return

        args = message.text.split()
        if len(args) < 2:
            await message.answer(
                "❌ <b>Использование:</b> /add_client @username\n\n"
                "📌 <b>Пример:</b> /add_client @john_doe\n\n"
                "<i>Ученик получит приглашение и должен будет его подтвердить.</i>",
                parse_mode=ParseMode.HTML
            )
            return

        username = args[1].lstrip('@')
        client = db.get_user_by_username(username)

        if not client:
            await message.answer(f"❌ Пользователь @{username} не найден.")
            return

        if client['telegram_id'] == user['telegram_id']:
            await message.answer("❌ Вы не можете добавить самого себя.")
            return

        if client['role'] != UserRole.CLIENT.value:
            await message.answer(
                f"❌ @{username} не является учеником.\n"
                "Пользователь должен зарегистрироваться как ученик через /start."
            )
            return

        existing_clients = db.get_trainer_clients(user['id'])
        if client['id'] in [c['id'] for c in existing_clients]:
            await message.answer(
                f"⚠️ @{username} уже является вашим учеником.\n"
                "Используйте /my_clients для просмотра списка."
            )
            return

        from app.keyboards.inline import get_client_action_keyboard

        await message.bot.send_message(
            chat_id=client['telegram_id'],
            text=(
                f"🏋️ <b>Приглашение от тренера!</b>\n\n"
                f"👨‍🏫 Тренер <b>{user['full_name']}</b> хочет добавить вас "
                f"в список учеников.\n\n"
                f"✅ Нажмите «Принять», чтобы стать учеником этого тренера.\n"
                f"❌ Нажмите «Отклонить», чтобы отказаться."
            ),
            parse_mode=ParseMode.HTML,
            reply_markup=get_client_action_keyboard("accept_invite", user['id'])
        )

        await message.answer(
            f"✅ Приглашение отправлено пользователю @{username}.\n"
            f"⏳ Ожидайте подтверждения."
        )

        logger.info(f"📨 Invite sent from trainer {user['id']} to client {client['id']}")

    except Exception as e:
        logger.error(f"Error in add_client: {e}\n{traceback.format_exc()}")
        await message.answer("❌ Ошибка при отправке приглашения.")


# ============================================================
#  ПРИНЯТИЕ ПРИГЛАШЕНИЯ
# ============================================================

@router.callback_query(F.data.startswith("accept_invite:"))
async def accept_invite(callback: CallbackQuery):
    try:
        parts = callback.data.split(":")
        if len(parts) < 2:
            await callback.answer("❌ Неверный формат данных", show_alert=True)
            return

        trainer_id = int(parts[1])

        client = db.get_user_by_telegram(callback.from_user.id)
        if not client:
            await callback.message.edit_text(
                "❌ Сначала зарегистрируйтесь через /start",
                reply_markup=get_cancel_keyboard()
            )
            await callback.answer()
            return

        if client['role'] != UserRole.CLIENT.value:
            await callback.message.edit_text(
                "❌ Вы должны быть учеником для принятия приглашения.\n"
                "Используйте /start для регистрации.",
                reply_markup=get_cancel_keyboard()
            )
            await callback.answer()
            return

        existing_clients = db.get_trainer_clients(trainer_id)
        if client['id'] in [c['id'] for c in existing_clients]:
            await callback.message.edit_text(
                "⚠️ Вы уже являетесь учеником этого тренера.",
                reply_markup=get_back_inline_keyboard("back_to_menu")
            )
            await callback.answer()
            return

        success = db.add_client_to_trainer(trainer_id, client['id'])

        if success:
            await callback.message.edit_text(
                "✅ <b>Вы приняли приглашение!</b>\n\n"
                "Теперь вы ученик этого тренера.\n"
                "Вы можете начать вносить замеры через /set_measurements.",
                parse_mode=ParseMode.HTML
            )

            trainer = db.get_user(trainer_id)
            if trainer:
                await callback.bot.send_message(
                    chat_id=trainer['telegram_id'],
                    text=(
                        f"✅ <b>Пользователь принял приглашение!</b>\n\n"
                        f"👤 Ученик: <b>{client['full_name']}</b>\n"
                        f"📱 Username: @{client['username'] or 'Не указан'}\n\n"
                        f"📊 Теперь вы можете отслеживать его прогресс."
                    ),
                    parse_mode=ParseMode.HTML
                )
                logger.info(f"✅ Client {client['id']} accepted invite from trainer {trainer_id}")
        else:
            await callback.message.edit_text(
                "❌ Не удалось добавить ученика. Попробуйте позже.",
                reply_markup=get_back_inline_keyboard("back_to_menu")
            )

        await callback.answer()

    except ValueError as e:
        logger.error(f"ValueError in accept_invite: {e}")
        await callback.answer("❌ Неверный ID", show_alert=True)
    except Exception as e:
        logger.error(f"Error in accept_invite: {e}\n{traceback.format_exc()}")
        await callback.message.edit_text("❌ Ошибка при принятии приглашения.")
        await callback.answer()


@router.callback_query(F.data == "reject_invite")
async def reject_invite(callback: CallbackQuery):
    try:
        await callback.message.edit_text(
            "❌ Вы отклонили приглашение тренера.",
            reply_markup=get_back_inline_keyboard("back_to_menu")
        )
        await callback.answer()
    except Exception as e:
        logger.error(f"Error in reject_invite: {e}")
        await callback.answer("❌ Ошибка")


# ============================================================
#  /my_clients
# ============================================================

@router.message(Command("my_clients"))
async def my_clients(message: Message):
    try:
        user = db.get_user_by_telegram(message.from_user.id)
        if not user:
            await message.answer("❌ Вы не зарегистрированы. Используйте /start.")
            return

        if user['role'] != UserRole.TRAINER.value:
            await message.answer("❌ Эта команда доступна только тренерам.")
            return

        clients = db.get_trainer_clients(user['id'])

        if not clients:
            await message.answer(
                "📋 <b>У вас пока нет учеников.</b>\n\n"
                "Добавьте ученика: /add_client @username",
                parse_mode=ParseMode.HTML
            )
            return

        keyboard = get_clients_list_keyboard(clients, action="info")
        await message.answer(
            f"👥 <b>Ваши ученики</b> ({len(clients)} чел.):\n\n"
            f"<i>Нажмите на ученика для просмотра информации.</i>",
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard
        )

        logger.info(f"📋 Trainer {user['id']} viewed clients list: {len(clients)} clients")

    except Exception as e:
        logger.error(f"Error in my_clients: {e}\n{traceback.format_exc()}")
        await message.answer("❌ Ошибка при загрузке списка учеников.")


# ============================================================
#  НАВИГАЦИЯ ПО СПИСКУ
# ============================================================

@router.callback_query(F.data.startswith("page_"))
async def page_clients(callback: CallbackQuery):
    try:
        logger.info(f"📥 [page_] data: {callback.data}")
        # FIX: новый формат page_{page}_{action}
        parts = callback.data.split("_")
        if len(parts) < 3:
            await callback.answer("❌ Неверный формат", show_alert=True)
            return

        page = int(parts[1])
        action = parts[2]

        trainer = db.get_user_by_telegram(callback.from_user.id)
        if not trainer:
            await callback.answer("❌ Тренер не найден", show_alert=True)
            return

        clients = db.get_trainer_clients(trainer['id'])
        keyboard = get_clients_list_keyboard(clients, action=action, page=page)

        await callback.message.edit_reply_markup(reply_markup=keyboard)
        await callback.answer()

    except ValueError:
        await callback.answer("❌ Неверный номер страницы", show_alert=True)
    except Exception as e:
        logger.error(f"❌ Error in page_clients: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@router.callback_query(F.data == "back_to_clients")
async def back_to_clients(callback: CallbackQuery, state: FSMContext):
    try:
        await state.clear()
        trainer = db.get_user_by_telegram(callback.from_user.id)
        if not trainer:
            await callback.answer("❌ Тренер не найден", show_alert=True)
            return

        clients = db.get_trainer_clients(trainer['id'])

        if not clients:
            await callback.message.edit_text(
                "📋 У вас пока нет учеников.\n\nДобавьте: /add_client @username",
                reply_markup=get_back_inline_keyboard("back_to_menu")
            )
            await callback.answer()
            return

        keyboard = get_clients_list_keyboard(clients, action="info")
        await callback.message.edit_text(
            f"👥 <b>Ваши ученики</b> ({len(clients)} чел.):",
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard
        )
        await callback.answer()

    except Exception as e:
        logger.error(f"❌ Error in back_to_clients: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


# ============================================================
#  КАРТОЧКА УЧЕНИКА
# ============================================================

@router.callback_query(F.data.regexp(r"^info_\d+$"))
async def show_client_info(callback: CallbackQuery):
    try:
        logger.info(f"📥 [info_] data: {callback.data}")
        client_id = int(callback.data.split("_")[1])
        client = db.get_user(client_id)

        if not client:
            await callback.answer("❌ Ученик не найден.", show_alert=True)
            return

        goal_map = {
            "weight_loss": "📉 Похудение",
            "muscle_gain": "💪 Набор массы",
            "maintain": "⚖️ Поддержание"
        }

        text = f"👤 <b>Информация об ученике</b>\n\n"
        text += f"📛 Имя: <b>{client['full_name'] or 'Не указано'}</b>\n"
        text += f"📱 Username: @{client['username'] or 'Не указан'}\n"
        text += f"🆔 ID: {client['telegram_id']}\n"
        text += f"🎂 Возраст: {client['age'] or 'Не указан'} лет\n"
        text += f"📏 Рост: {client['height'] or 'Не указан'} см\n"
        text += f"🎯 Цель: {goal_map.get(client['goal'], client['goal'] or 'Не указана')}\n"

        if client['created_at']:
            text += f"📅 Регистрация: {client['created_at'].strftime('%d.%m.%Y')}\n"

        measurements = db.get_measurements(client_id, days=365)
        text += f"📊 Замеров: {len(measurements)}\n"

        await callback.message.edit_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=get_client_actions_keyboard(client_id)
        )
        await callback.answer()

    except ValueError as e:
        logger.error(f"❌ ValueError in show_client_info: {e}")
        await callback.answer("❌ Неверный ID", show_alert=True)
    except Exception as e:
        logger.error(f"❌ Error in show_client_info: {e}\n{traceback.format_exc()}")
        await callback.answer("❌ Ошибка", show_alert=True)


# ============================================================
#  ЗАМЕРЫ УЧЕНИКА
# ============================================================

@router.callback_query(F.data.regexp(r"^measurements_\d+$"))
async def view_client_measurements(callback: CallbackQuery):
    try:
        client_id = int(callback.data.split("_")[1])
        client = db.get_user(client_id)

        if not client:
            await callback.answer("❌ Ученик не найден", show_alert=True)
            return

        measurements = db.get_measurements(client_id, days=30)

        if not measurements:
            await callback.message.edit_text(
                f"📊 У ученика <b>{client['full_name']}</b> пока нет замеров.",
                parse_mode=ParseMode.HTML,
                reply_markup=get_back_inline_keyboard("back_to_clients")
            )
            await callback.answer()
            return

        last = measurements[-1]

        text = f"📊 <b>Последние замеры</b>\n"
        text += f"👤 {client['full_name']}\n\n"
        text += f"📅 Дата: {last['measured_at'].strftime('%d.%m.%Y %H:%M')}\n"
        text += f"📊 Всего замеров: {len(measurements)}\n\n"

        text += "📝 <b>Текущие значения:</b>\n"
        if last['weight']:
            text += f"⚖️ Вес: <b>{last['weight']:.1f}</b> кг\n"
        if last['waist']:
            text += f"📏 Талия: <b>{last['waist']:.1f}</b> см\n"
        if last['hips']:
            text += f"📏 Бедра: <b>{last['hips']:.1f}</b> см\n"
        if last['chest']:
            text += f"📏 Грудь: <b>{last['chest']:.1f}</b> см\n"
        if last['biceps']:
            text += f"💪 Бицепс: <b>{last['biceps']:.1f}</b> см\n"

        await callback.message.edit_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=get_back_inline_keyboard("back_to_clients")
        )
        await callback.answer()

    except ValueError as e:
        logger.error(f"❌ ValueError in view_client_measurements: {e}")
        await callback.answer("❌ Неверный ID", show_alert=True)
    except Exception as e:
        logger.error(f"❌ Error in view_client_measurements: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


# ============================================================
#  ГРАФИК
# ============================================================

@router.callback_query(F.data.regexp(r"^chart_\d+$"))
async def view_client_chart(callback: CallbackQuery):
    try:
        from app.services.chart_service import ChartService

        client_id = int(callback.data.split("_")[1])
        client = db.get_user(client_id)

        if not client:
            await callback.answer("❌ Ученик не найден", show_alert=True)
            return

        measurements = db.get_measurements(client_id, days=30)

        if len(measurements) < 2:
            await callback.message.edit_text(
                "❌ Недостаточно данных для графика.\nНужно минимум 2 замера.",
                reply_markup=get_back_inline_keyboard("back_to_clients")
            )
            await callback.answer()
            return

        await callback.message.edit_text("⏳ Генерация графика...")
        await callback.answer()

        chart_service = ChartService()
        chart_data = await chart_service.generate_stats_chart_bytes(
            client_id, measurements
        )

        if not chart_data:
            await callback.message.edit_text(
                "❌ Ошибка при генерации графика.",
                reply_markup=get_back_inline_keyboard("back_to_clients")
            )
            return

        photo = BufferedInputFile(chart_data, filename=f"chart_{client_id}.png")
        await callback.message.delete()
        await callback.message.answer_photo(
            photo=photo,
            caption=f"📊 <b>График прогресса</b>\n👤 {client['full_name']}",
            parse_mode=ParseMode.HTML
        )

    except ValueError as e:
        logger.error(f"❌ ValueError in view_client_chart: {e}")
        await callback.answer("❌ Неверный ID", show_alert=True)
    except Exception as e:
        logger.error(f"❌ Error in view_client_chart: {e}\n{traceback.format_exc()}")
        await callback.answer("❌ Ошибка", show_alert=True)


# ============================================================
#  УДАЛЕНИЕ
# ============================================================

@router.callback_query(F.data.regexp(r"^delete_\d+$"))
async def confirm_delete_client(callback: CallbackQuery):
    try:
        # FIX: regexp ^delete_\d+$ — не перехватит delete_reminder_5
        client_id = int(callback.data.split("_")[1])
        client = db.get_user(client_id)

        if not client:
            await callback.answer("❌ Ученик не найден", show_alert=True)
            return

        trainer = db.get_user_by_telegram(callback.from_user.id)
        if not trainer:
            await callback.answer("❌ Тренер не найден", show_alert=True)
            return

        if not db.is_trainer_of_client(trainer['id'], client_id):
            await callback.answer("❌ Это не ваш ученик", show_alert=True)
            return

        text = (
            f"⚠️ <b>Подтверждение удаления</b>\n\n"
            f"Вы уверены, что хотите удалить ученика\n"
            f"<b>{client['full_name'] or client['username']}</b>?\n\n"
            f"<i>Все данные ученика будут сохранены в истории.</i>"
        )

        await callback.message.edit_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=get_confirm_delete_keyboard(client_id)
        )
        await callback.answer()

    except ValueError as e:
        logger.error(f"❌ ValueError in confirm_delete_client: {e}")
        await callback.answer("❌ Неверный ID", show_alert=True)
    except Exception as e:
        logger.error(f"❌ Error in confirm_delete_client: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@router.callback_query(F.data.startswith("confirm_delete_"))
async def delete_client_confirm(callback: CallbackQuery):
    try:
        client_id = int(callback.data.split("_")[2])

        trainer = db.get_user_by_telegram(callback.from_user.id)
        if not trainer:
            await callback.answer("❌ Тренер не найден", show_alert=True)
            return

        if not db.is_trainer_of_client(trainer['id'], client_id):
            await callback.answer("❌ Это не ваш ученик", show_alert=True)
            return

        client = db.get_user(client_id)
        name = (client['full_name'] or client['username'] or "Ученик") if client else "Ученик"

        db.remove_client_from_trainer(trainer['id'], client_id)

        await callback.message.edit_text(
            f"✅ Ученик <b>{name}</b> успешно удалён.",
            parse_mode=ParseMode.HTML,
            reply_markup=get_back_inline_keyboard("back_to_menu")
        )

        if client:
            try:
                await callback.bot.send_message(
                    chat_id=client['telegram_id'],
                    text=f"⚠️ Тренер <b>{trainer['full_name']}</b> удалил вас из списка учеников.",
                    parse_mode=ParseMode.HTML
                )
            except Exception as e:
                logger.warning(f"Could not notify client: {e}")

        logger.info(f"🗑️ Trainer {trainer['id']} deleted client {client_id}")
        await callback.answer()

    except ValueError as e:
        logger.error(f"❌ ValueError in delete_client_confirm: {e}")
        await callback.answer("❌ Неверный ID", show_alert=True)
    except Exception as e:
        logger.error(f"❌ Error in delete_client_confirm: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@router.callback_query(F.data == "cancel_delete")
async def cancel_delete(callback: CallbackQuery):
    try:
        trainer = db.get_user_by_telegram(callback.from_user.id)
        if not trainer:
            await callback.answer("❌ Тренер не найден", show_alert=True)
            return

        clients = db.get_trainer_clients(trainer['id'])
        keyboard = get_clients_list_keyboard(clients, action="info")

        await callback.message.edit_text(
            f"👥 Ваши ученики ({len(clients)} чел.):",
            reply_markup=keyboard
        )
        await callback.answer()

    except Exception as e:
        logger.error(f"❌ Error in cancel_delete: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


# ============================================================
#  /delete_client
# ============================================================

@router.message(Command("delete_client"))
async def delete_client_cmd(message: Message):
    try:
        user = db.get_user_by_telegram(message.from_user.id)
        if not user or user['role'] != UserRole.TRAINER.value:
            await message.answer("❌ Эта команда доступна только тренерам.")
            return

        args = message.text.split()
        if len(args) < 2:
            await message.answer(
                "❌ <b>Использование:</b> /delete_client @username\n\n"
                "📌 <b>Пример:</b> /delete_client @john_doe",
                parse_mode=ParseMode.HTML
            )
            return

        username = args[1].lstrip('@')
        client = db.get_user_by_username(username)

        if not client:
            await message.answer(f"❌ Пользователь @{username} не найден.")
            return

        clients = db.get_trainer_clients(user['id'])
        if client['id'] not in [c['id'] for c in clients]:
            await message.answer(f"❌ @{username} не является вашим учеником.")
            return

        db.remove_client_from_trainer(user['id'], client['id'])

        await message.answer(f"✅ Ученик @{username} удалён из вашего списка.")

        try:
            await message.bot.send_message(
                chat_id=client['telegram_id'],
                text=f"ℹ️ Тренер {user['full_name']} удалил вас из списка учеников."
            )
        except Exception:
            pass

        logger.info(f"🗑️ Trainer {user['id']} deleted client {client['id']} via command")

    except Exception as e:
        logger.error(f"Error in delete_client_cmd: {e}")
        await message.answer("❌ Ошибка при удалении ученика.")


# ============================================================
#  ОТПРАВКА СООБЩЕНИЯ УЧЕНИКУ (FSM)
# ============================================================

@router.callback_query(F.data.regexp(r"^msg_\d+$"))
async def prompt_message_to_client(callback: CallbackQuery, state: FSMContext):
    try:
        client_id = int(callback.data.split("_")[1])
        client = db.get_user(client_id)

        if not client:
            await callback.answer("❌ Ученик не найден", show_alert=True)
            return

        trainer = db.get_user_by_telegram(callback.from_user.id)
        if not trainer:
            await callback.answer("❌ Тренер не найден", show_alert=True)
            return

        if not db.is_trainer_of_client(trainer['id'], client_id):
            await callback.answer("❌ Это не ваш ученик", show_alert=True)
            return

        await state.update_data(
            client_id=client_id,
            client_name=client['full_name'] or client['username']
        )

        text = (
            f"✏️ Напишите сообщение для "
            f"<b>{client['full_name'] or client['username']}</b>:\n\n"
            f"<i>Отправьте текст сообщения. Чтобы отменить, нажмите кнопку ниже.</i>"
        )

        cancel_keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_message")]
            ]
        )

        await callback.message.edit_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=cancel_keyboard
        )

        await state.set_state(MessageStates.waiting_for_message)
        await callback.answer()

    except ValueError as e:
        logger.error(f"❌ ValueError in prompt_message_to_client: {e}")
        await callback.answer("❌ Неверный ID", show_alert=True)
    except Exception as e:
        logger.error(f"❌ Error in prompt_message_to_client: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@router.message(StateFilter(MessageStates.waiting_for_message))
async def send_message_to_client(message: Message, state: FSMContext):
    try:
        data = await state.get_data()
        client_id = data.get('client_id')
        client_name = data.get('client_name', 'Ученик')

        if not client_id:
            await message.answer("❌ Ошибка: не найден ID ученика.")
            await state.clear()
            return

        client = db.get_user(client_id)
        if not client:
            await message.answer("❌ Ученик не найден.")
            await state.clear()
            return

        await message.bot.send_message(
            chat_id=client['telegram_id'],
            text=f"📨 <b>Сообщение от тренера</b>\n\n{message.text}",
            parse_mode=ParseMode.HTML
        )

        await message.answer(
            f"✅ Сообщение отправлено ученику <b>{client_name}</b>!",
            parse_mode=ParseMode.HTML
        )

        await state.clear()

    except Exception as e:
        logger.error(f"❌ Error in send_message_to_client: {e}")
        await message.answer("❌ Ошибка при отправке сообщения.")
        await state.clear()


@router.callback_query(F.data == "cancel_message")
async def cancel_message(callback: CallbackQuery, state: FSMContext):
    try:
        await state.clear()
        await callback.message.edit_text(
            "❌ Отправка сообщения отменена.",
            reply_markup=get_back_inline_keyboard("back_to_menu")
        )
        await callback.answer()
    except Exception as e:
        logger.error(f"Error in cancel_message: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)
# ============================================================
#  УНИВЕРСАЛЬНЫЙ ВОЗВРАТ В ГЛАВНОЕ МЕНЮ
# ============================================================

@router.callback_query(F.data == "back_to_menu")
async def back_to_menu_universal(callback: CallbackQuery, state: FSMContext):
    """Универсальный возврат в главное меню (тренер или ученик)."""
    try:
        await state.clear()

        user = db.get_user_by_telegram(callback.from_user.id)
        if not user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return

        from app.keyboards.inline import (
            get_trainer_menu_keyboard,
            get_client_menu_keyboard
        )

        # Удаляем inline-сообщение
        try:
            await callback.message.delete()
        except Exception:
            pass

        # Отправляем новое с Reply-меню
        if user['role'] == UserRole.TRAINER.value:
            await callback.message.answer(
                f"👋 <b>Главное меню тренера</b>\n\n"
                f"Добро пожаловать, {user['full_name'] or 'Тренер'}!",
                parse_mode=ParseMode.HTML,
                reply_markup=get_trainer_menu_keyboard()
            )
        else:
            await callback.message.answer(
                f"👋 <b>Главное меню ученика</b>\n\n"
                f"Добро пожаловать, {user['full_name'] or 'Ученик'}!",
                parse_mode=ParseMode.HTML,
                reply_markup=get_client_menu_keyboard()
            )

        await callback.answer()

    except Exception as e:
        logger.error(f"Error in back_to_menu_universal: {e}\n{traceback.format_exc()}")
        await callback.answer("❌ Ошибка", show_alert=True)


# ============================================================
#  ВОЗВРАТ В АДМИН-ПАНЕЛЬ
# ============================================================

@router.callback_query(F.data == "back_to_admin")
async def back_to_admin_universal(callback: CallbackQuery):
    """Возврат в админ-панель."""
    try:
        from app.config import Config
        admin_ids = Config.get_admin_ids()
        if not admin_ids or callback.from_user.id not in admin_ids:
            await callback.answer("❌ Доступ запрещён.", show_alert=True)
            return

        from app.keyboards.inline import get_admin_keyboard

        await callback.message.edit_text(
            "🔐 <b>Административная панель</b>\n\n"
            "Выберите действие:",
            parse_mode=ParseMode.HTML,
            reply_markup=get_admin_keyboard()
        )
        await callback.answer()

    except Exception as e:
        logger.error(f"Error in back_to_admin_universal: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)
