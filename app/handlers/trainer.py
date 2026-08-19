from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, BufferedInputFile
from aiogram.enums import ParseMode
from app.services.db_service import DatabaseService
from app.keyboards.inline import (
    get_client_actions_keyboard,
    get_back_keyboard,
    get_clients_list_keyboard,
    get_confirm_delete_keyboard
)
from app.models import UserRole
from app.utils.logger import get_logger
import traceback
from datetime import datetime

logger = get_logger(__name__)
router = Router()
db = DatabaseService()


@router.callback_query(F.data.startswith("info_"))
async def show_client_info(callback: CallbackQuery):
    try:
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
        text += f"📛 Имя: <b>{client.full_name or 'Не указано'}</b>\n"
        text += f"📱 Username: @{client.username or 'Не указан'}\n"
        text += f"🆔 ID: {client.telegram_id}\n"
        text += f"🎂 Возраст: {client.age or 'Не указан'} лет\n"
        text += f"📏 Рост: {client.height or 'Не указан'} см\n"
        text += f"🎯 Цель: {goal_map.get(client.goal, client.goal or 'Не указана')}\n"

        if client.created_at:
            text += f"📅 Регистрация: {client.created_at.strftime('%d.%m.%Y')}\n"

        status = "✅ Активен" if client.is_active else "❌ Неактивен"
        text += f"📊 Статус: {status}\n"

        measurements = db.get_measurements(client_id, days=365)
        text += f"📊 Замеров: {len(measurements)}\n"

        keyboard = get_client_actions_keyboard(client_id)

        await callback.message.edit_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard
        )
        await callback.answer()

    except ValueError:
        await callback.answer("❌ Неверный ID пользователя", show_alert=True)
    except Exception as e:
        logger.error(f"Error in show_client_info: {e}")
        await callback.answer("❌ Произошла ошибка", show_alert=True)


@router.callback_query(F.data == "back_to_clients")
async def back_to_clients(callback: CallbackQuery):
    try:
        trainer = db.get_user_by_telegram(callback.from_user.id)
        if not trainer:
            await callback.answer("❌ Тренер не найден", show_alert=True)
            return

        clients = db.get_trainer_clients(trainer.id)

        if not clients:
            await callback.message.edit_text(
                "👥 У вас пока нет учеников.\n"
                "Чтобы добавить ученика, используйте /add_client.",
                reply_markup=get_back_keyboard()
            )
            await callback.answer()
            return

        keyboard = get_clients_list_keyboard(clients)
        await callback.message.edit_text(
            f"👥 Ваши ученики ({len(clients)} чел.):",
            reply_markup=keyboard
        )
        await callback.answer()

    except Exception as e:
        logger.error(f"Error in back_to_clients: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@router.callback_query(F.data.startswith("page_clients_"))
async def page_clients(callback: CallbackQuery):
    try:
        page = int(callback.data.split("_")[2])

        trainer = db.get_user_by_telegram(callback.from_user.id)
        if not trainer:
            await callback.answer("❌ Тренер не найден", show_alert=True)
            return

        clients = db.get_trainer_clients(trainer.id)
        keyboard = get_clients_list_keyboard(clients, page=page)

        await callback.message.edit_reply_markup(reply_markup=keyboard)
        await callback.answer()

    except Exception as e:
        logger.error(f"Error in page_clients: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@router.callback_query(F.data.startswith("delete_"))
async def confirm_delete_client(callback: CallbackQuery):
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

        is_my_client = db.is_trainer_of_client(trainer.id, client_id)
        if not is_my_client:
            await callback.answer("❌ Это не ваш ученик", show_alert=True)
            return

        text = f"⚠️ <b>Подтверждение удаления</b>\n\n"
        text += f"Вы уверены, что хотите удалить ученика <b>{client.full_name or client.username}</b>?\n"
        text += "\n<i>Все данные ученика будут сохранены в истории.</i>"

        keyboard = get_confirm_delete_keyboard(client_id)

        await callback.message.edit_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard
        )
        await callback.answer()

    except Exception as e:
        logger.error(f"Error in confirm_delete_client: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@router.callback_query(F.data.startswith("confirm_delete_"))
async def delete_client(callback: CallbackQuery):
    try:
        client_id = int(callback.data.split("_")[2])

        trainer = db.get_user_by_telegram(callback.from_user.id)
        if not trainer:
            await callback.answer("❌ Тренер не найден", show_alert=True)
            return

        is_my_client = db.is_trainer_of_client(trainer.id, client_id)
        if not is_my_client:
            await callback.answer("❌ Это не ваш ученик", show_alert=True)
            return

        db.remove_client_from_trainer(trainer.id, client_id)

        client = db.get_user(client_id)
        name = client.full_name or client.username or "Ученик"

        await callback.message.edit_text(
            f"✅ Ученик <b>{name}</b> успешно удалён.",
            parse_mode=ParseMode.HTML,
            reply_markup=get_back_keyboard()
        )

        try:
            await callback.bot.send_message(
                chat_id=client.telegram_id,
                text=f"⚠️ Тренер <b>{trainer.full_name}</b> удалил вас из списка учеников.",
                parse_mode=ParseMode.HTML
            )
        except Exception as e:
            logger.warning(f"Could not notify client: {e}")

        logger.info(f"🗑️ Trainer {trainer.id} deleted client {client_id}")
        await callback.answer()

    except Exception as e:
        logger.error(f"Error in delete_client: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@router.callback_query(F.data == "cancel_delete")
async def cancel_delete(callback: CallbackQuery):
    try:
        trainer = db.get_user_by_telegram(callback.from_user.id)
        if not trainer:
            await callback.answer("❌ Тренер не найден", show_alert=True)
            return

        clients = db.get_trainer_clients(trainer.id)
        keyboard = get_clients_list_keyboard(clients)

        await callback.message.edit_text(
            f"👥 Ваши ученики ({len(clients)} чел.):",
            reply_markup=keyboard
        )
        await callback.answer()

    except Exception as e:
        logger.error(f"Error in cancel_delete: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@router.callback_query(F.data.startswith("msg_"))
async def prompt_message_to_client(callback: CallbackQuery):
    try:
        # Проверяем, что это не "msg_select"
        if callback.data == "msg_select" or callback.data.startswith("msg_select_"):
            await callback.answer("❌ Выберите ученика из списка.", show_alert=True)
            return

        client_id = int(callback.data.split("_")[1])
        client = db.get_user(client_id)

        if not client:
            await callback.answer("❌ Ученик не найден", show_alert=True)
            return

        trainer = db.get_user_by_telegram(callback.from_user.id)
        if not trainer:
            await callback.answer("❌ Тренер не найден", show_alert=True)
            return

        is_my_client = db.is_trainer_of_client(trainer.id, client_id)
        if not is_my_client:
            await callback.answer("❌ Это не ваш ученик", show_alert=True)
            return

        text = f"✏️ Напишите сообщение для <b>{client.full_name or client.username}</b>:\n\n"
        text += "<i>Сообщение будет отправлено в личные сообщения ученику.</i>"

        from app.keyboards.inline import get_cancel_keyboard

        await callback.message.edit_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=get_cancel_keyboard()
        )

        # Сохраняем client_id в состоянии для дальнейшей обработки
        # TODO: Добавить FSM для ожидания сообщения

        await callback.answer()

    except ValueError:
        await callback.answer("❌ Неверный ID", show_alert=True)
    except Exception as e:
        logger.error(f"Error in prompt_message_to_client: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)
