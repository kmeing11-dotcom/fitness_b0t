from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.enums import ParseMode
from datetime import datetime
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

logger = get_logger(__name__)
router = Router()
db = DatabaseService()


# ============================================================
#  FSM ДЛЯ ОТПРАВКИ СООБЩЕНИЙ
# ============================================================

class MessageStates(StatesGroup):
    waiting_for_message = State()


# ============================================================
#  ВСПОМОГАТЕЛЬНАЯ ФУНКЦИЯ
# ============================================================

def get_client_id_from_callback(callback_data: str) -> int:
    """Универсальный парсинг ID из callback_data"""
    parts = callback_data.split("_")
    if len(parts) < 2:
        raise ValueError(f"Invalid format: {callback_data}")
    if not parts[1].isdigit():
        raise ValueError(f"ID is not a number: {parts[1]}")
    return int(parts[1])


# ============================================================
#  ОБРАБОТЧИКИ
# ============================================================

@router.callback_query(F.data.startswith("info_"))
async def show_client_info(callback: CallbackQuery):
    try:
        logger.info(f"📥 [info_] data: {callback.data}")
        client_id = get_client_id_from_callback(callback.data)
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

        measurements = db.get_measurements(client_id, days=365)
        text += f"📊 Замеров: {len(measurements)}\n"

        keyboard = get_client_actions_keyboard(client_id)

        await callback.message.edit_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard
        )
        await callback.answer()

    except ValueError as e:
        logger.error(f"❌ ValueError in show_client_info: {e}")
        await callback.answer("❌ Неверный ID", show_alert=True)
    except Exception as e:
        logger.error(f"❌ Error in show_client_info: {e}\n{traceback.format_exc()}")
        await callback.answer("❌ Ошибка", show_alert=True)


@router.callback_query(F.data == "back_to_clients")
async def back_to_clients(callback: CallbackQuery, state: FSMContext):
    try:
        await state.clear()  # Очищаем состояние
        logger.info(f"📥 [back_to_clients]")
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

        keyboard = get_clients_list_keyboard(clients, action="info")
        await callback.message.edit_text(
            f"👥 Ваши ученики ({len(clients)} чел.):",
            reply_markup=keyboard
        )
        await callback.answer()

    except Exception as e:
        logger.error(f"❌ Error in back_to_clients: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@router.callback_query(F.data.startswith("page_"))
async def page_clients(callback: CallbackQuery):
    try:
        logger.info(f"📥 [page_] data: {callback.data}")
        parts = callback.data.split("_")
        if len(parts) < 3:
            await callback.answer("❌ Неверный формат", show_alert=True)
            return

        page = int(parts[2])

        trainer = db.get_user_by_telegram(callback.from_user.id)
        if not trainer:
            await callback.answer("❌ Тренер не найден", show_alert=True)
            return

        clients = db.get_trainer_clients(trainer.id)
        keyboard = get_clients_list_keyboard(clients, action="info", page=page)

        await callback.message.edit_reply_markup(reply_markup=keyboard)
        await callback.answer()

    except ValueError:
        await callback.answer("❌ Неверный номер страницы", show_alert=True)
    except Exception as e:
        logger.error(f"❌ Error in page_clients: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@router.callback_query(F.data.startswith("delete_"))
async def confirm_delete_client(callback: CallbackQuery):
    try:
        logger.info(f"📥 [delete_] data: {callback.data}")
        client_id = get_client_id_from_callback(callback.data)
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
        text += f"Вы уверены, что хотите удалить ученика\n"
        text += f"<b>{client.full_name or client.username}</b>?\n\n"
        text += "<i>Все данные ученика будут сохранены в истории.</i>"

        keyboard = get_confirm_delete_keyboard(client_id)

        await callback.message.edit_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard
        )
        await callback.answer()

    except ValueError as e:
        logger.error(f"❌ ValueError in confirm_delete_client: {e}")
        await callback.answer("❌ Неверный ID", show_alert=True)
    except Exception as e:
        logger.error(f"❌ Error in confirm_delete_client: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@router.callback_query(F.data.startswith("confirm_delete_"))
async def delete_client(callback: CallbackQuery):
    try:
        logger.info(f"📥 [confirm_delete_] data: {callback.data}")
        parts = callback.data.split("_")
        if len(parts) < 3:
            await callback.answer("❌ Неверный формат", show_alert=True)
            return
        client_id = int(parts[2])

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

    except ValueError as e:
        logger.error(f"❌ ValueError in delete_client: {e}")
        await callback.answer("❌ Неверный ID", show_alert=True)
    except Exception as e:
        logger.error(f"❌ Error in delete_client: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@router.callback_query(F.data == "cancel_delete")
async def cancel_delete(callback: CallbackQuery):
    try:
        logger.info(f"📥 [cancel_delete]")
        trainer = db.get_user_by_telegram(callback.from_user.id)
        if not trainer:
            await callback.answer("❌ Тренер не найден", show_alert=True)
            return

        clients = db.get_trainer_clients(trainer.id)
        keyboard = get_clients_list_keyboard(clients, action="info")

        await callback.message.edit_text(
            f"👥 Ваши ученики ({len(clients)} чел.):",
            reply_markup=keyboard
        )
        await callback.answer()

    except Exception as e:
        logger.error(f"❌ Error in cancel_delete: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@router.callback_query(F.data.startswith("measurements_"))
async def view_client_measurements(callback: CallbackQuery):
    try:
        logger.info(f"📥 [measurements_] data: {callback.data}")
        client_id = get_client_id_from_callback(callback.data)
        client = db.get_user(client_id)

        if not client:
            await callback.answer("❌ Ученик не найден", show_alert=True)
            return

        measurements = db.get_measurements(client_id, days=30)

        if not measurements:
            await callback.message.edit_text(
                f"📊 У ученика <b>{client.full_name}</b> пока нет замеров.",
                parse_mode=ParseMode.HTML,
                reply_markup=get_back_keyboard()
            )
            await callback.answer()
            return

        last = measurements[-1]

        text = f"📊 <b>Последние замеры</b>\n"
        text += f"👤 {client.full_name}\n\n"
        text += f"📅 Дата: {last.measured_at.strftime('%d.%m.%Y %H:%M')}\n"
        text += f"📊 Всего замеров: {len(measurements)}\n\n"

        text += "📝 <b>Текущие значения:</b>\n"
        if last.weight:
            text += f"⚖️ Вес: <b>{last.weight:.1f}</b> кг\n"
        if last.waist:
            text += f"📏 Талия: <b>{last.waist:.1f}</b> см\n"
        if last.hips:
            text += f"📏 Бедра: <b>{last.hips:.1f}</b> см\n"
        if last.chest:
            text += f"📏 Грудь: <b>{last.chest:.1f}</b> см\n"
        if last.biceps:
            text += f"💪 Бицепс: <b>{last.biceps:.1f}</b> см\n"

        await callback.message.edit_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=get_back_keyboard()
        )
        await callback.answer()

    except ValueError as e:
        logger.error(f"❌ ValueError in view_client_measurements: {e}")
        await callback.answer("❌ Неверный ID", show_alert=True)
    except Exception as e:
        logger.error(f"❌ Error in view_client_measurements: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@router.callback_query(F.data.startswith("chart_"))
async def view_client_chart(callback: CallbackQuery):
    try:
        from app.services.chart_service import ChartService
        from aiogram.types import BufferedInputFile

        logger.info(f"📥 [chart_] data: {callback.data}")
        client_id = get_client_id_from_callback(callback.data)
        client = db.get_user(client_id)

        if not client:
            await callback.answer("❌ Ученик не найден", show_alert=True)
            return

        measurements = db.get_measurements(client_id, days=30)

        if len(measurements) < 2:
            await callback.message.edit_text(
                "❌ Недостаточно данных для графика.\nНужно минимум 2 замера.",
                parse_mode=ParseMode.HTML,
                reply_markup=get_back_keyboard()
            )
            await callback.answer()
            return

        chart_service = ChartService()
        chart_data = await chart_service.generate_stats_chart_bytes(client_id, measurements)

        if not chart_data:
            await callback.message.edit_text(
                "❌ Ошибка при генерации графика.",
                parse_mode=ParseMode.HTML,
                reply_markup=get_back_keyboard()
            )
            await callback.answer()
            return

        photo = BufferedInputFile(chart_data, filename=f"chart_{client_id}.png")
        await callback.message.delete()
        await callback.message.answer_photo(
            photo=photo,
            caption=f"📊 <b>График прогресса</b>\n👤 {client.full_name}",
            parse_mode=ParseMode.HTML,
            reply_markup=get_back_keyboard()
        )
        await callback.answer()

    except ValueError as e:
        logger.error(f"❌ ValueError in view_client_chart: {e}")
        await callback.answer("❌ Неверный ID", show_alert=True)
    except Exception as e:
        logger.error(f"❌ Error in view_client_chart: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@router.callback_query(F.data.startswith("report_"))
async def generate_client_report(callback: CallbackQuery):
    try:
        from app.services.pdf_service import PDFService
        from app.services.chart_service import ChartService
        from aiogram.types import FSInputFile

        logger.info(f"📥 [report_] data: {callback.data}")
        client_id = get_client_id_from_callback(callback.data)
        client = db.get_user(client_id)

        if not client:
            await callback.answer("❌ Ученик не найден", show_alert=True)
            return

        measurements = db.get_measurements(client_id, days=28)

        if len(measurements) < 2:
            await callback.message.edit_text(
                "❌ Недостаточно данных для отчёта.\nНужно минимум 2 замера.",
                parse_mode=ParseMode.HTML,
                reply_markup=get_back_keyboard()
            )
            await callback.answer()
            return

        chart_service = ChartService()
        chart_path = await chart_service.generate_report_chart(client_id, measurements)

        pdf_service = PDFService()
        pdf_path = await pdf_service.generate_client_report(
            user_id=client_id,
            client=client,
            measurements=measurements,
            chart_path=chart_path
        )

        if not pdf_path:
            await callback.message.edit_text(
                "❌ Ошибка при генерации отчёта.",
                parse_mode=ParseMode.HTML,
                reply_markup=get_back_keyboard()
            )
            await callback.answer()
            return

        await callback.message.delete()
        await callback.message.answer_document(
            document=FSInputFile(pdf_path),
            caption=(
                f"📄 <b>Отчёт о прогрессе</b>\n"
                f"👤 {client.full_name}\n"
                f"📅 {datetime.now().strftime('%d.%m.%Y')}"
            ),
            parse_mode=ParseMode.HTML,
            reply_markup=get_back_keyboard()
        )
        await callback.answer()

    except ValueError as e:
        logger.error(f"❌ ValueError in generate_client_report: {e}")
        await callback.answer("❌ Неверный ID", show_alert=True)
    except Exception as e:
        logger.error(f"❌ Error in generate_client_report: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


# ============================================================
#  ОТПРАВКА СООБЩЕНИЯ УЧЕНИКУ (С FSM)
# ============================================================

@router.callback_query(F.data.startswith("msg_"))
async def prompt_message_to_client(callback: CallbackQuery, state: FSMContext):
    try:
        # Проверяем, что это не "msg_select"
        if callback.data == "msg_select" or callback.data.startswith("msg_select_"):
            await callback.answer("❌ Выберите ученика из списка.", show_alert=True)
            return

        logger.info(f"📥 [msg_] data: {callback.data}")
        client_id = get_client_id_from_callback(callback.data)
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

        # Сохраняем client_id в состоянии
        await state.update_data(client_id=client_id, client_name=client.full_name or client.username)

        text = f"✏️ Напишите сообщение для <b>{client.full_name or client.username}</b>:\n\n"
        text += "<i>Отправьте текст сообщения. Чтобы отменить, нажмите кнопку ниже.</i>"

        # Inline-клавиатура для отмены
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
    """Отправляет сообщение ученику"""
    try:
        data = await state.get_data()
        client_id = data.get('client_id')
        client_name = data.get('client_name', 'Ученик')

        if not client_id:
            await message.answer("❌ Ошибка: не найден ID ученика. Попробуйте снова.")
            await state.clear()
            return

        client = db.get_user(client_id)
        if not client:
            await message.answer("❌ Ученик не найден.")
            await state.clear()
            return

        # Отправляем сообщение ученику
        await message.bot.send_message(
            chat_id=client.telegram_id,
            text=f"📨 <b>Сообщение от тренера</b>\n\n{message.text}",
            parse_mode=ParseMode.HTML
        )

        # Подтверждение тренеру
        await message.answer(
            f"✅ Сообщение отправлено ученику <b>{client_name}</b>!",
            parse_mode=ParseMode.HTML,
            reply_markup=get_back_keyboard()
        )

        # Очищаем состояние
        await state.clear()

    except Exception as e:
        logger.error(f"❌ Error in send_message_to_client: {e}")
        await message.answer("❌ Ошибка при отправке сообщения. Попробуйте позже.")
        await state.clear()


@router.callback_query(F.data == "cancel_message")
async def cancel_message(callback: CallbackQuery, state: FSMContext):
    """Отмена отправки сообщения"""
    try:
        await state.clear()
        await callback.message.edit_text(
            "❌ Отправка сообщения отменена.",
            reply_markup=get_back_keyboard()
        )
        await callback.answer()
    except Exception as e:
        logger.error(f"Error in cancel_message: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


# ============================================================
#  УНИВЕРСАЛЬНЫЙ ОБРАБОТЧИК ДЛЯ НЕИЗВЕСТНЫХ CALLBACK
# ============================================================

@router.callback_query()
async def catch_all_callbacks(callback: CallbackQuery):
    """Ловит все callback-запросы, которые не обработаны другими хендлерами"""
    logger.warning(f"⚠️ [UNHANDLED CALLBACK] data: {callback.data}")
    await callback.answer(f"❌ Неизвестная команда", show_alert=True)
