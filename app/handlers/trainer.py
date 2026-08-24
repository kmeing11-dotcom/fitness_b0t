from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.enums import ParseMode
from app.services.db_service import DatabaseService
from app.keyboards.inline import (
    get_client_actions_keyboard,
    get_back_keyboard,
    get_clients_list_keyboard,
    get_confirm_delete_keyboard,
    get_cancel_keyboard
)
from app.models import UserRole
from app.utils.logger import get_logger
import traceback

logger = get_logger(__name__)
router = Router()
db = DatabaseService()

@router.callback_query()
async def log_all_callbacks(callback: CallbackQuery):
    """Логирует все callback запросы для отладки"""
    logger.info(f"📥 [ALL] Callback data: {callback.data}")
    logger.info(f"📥 [ALL] From user: {callback.from_user.id}")
    # Пропускаем дальше, чтобы другие обработчики тоже сработали
    await callback.continue_propagation()
    
@router.callback_query(F.data.startswith("info_"))
async def show_client_info(callback: CallbackQuery):
    try:
        # Парсим ID из формата "info_2"
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
        await callback.answer("❌ Неверный ID", show_alert=True)
    except Exception as e:
        logger.error(f"Error in show_client_info: {e}\n{traceback.format_exc()}")
        await callback.answer("❌ Ошибка", show_alert=True)


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

        keyboard = get_clients_list_keyboard(clients, action="info")
        await callback.message.edit_text(
            f"👥 Ваши ученики ({len(clients)} чел.):",
            reply_markup=keyboard
        )
        await callback.answer()

    except Exception as e:
        logger.error(f"Error in back_to_clients: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@router.callback_query(F.data.startswith("page_"))
async def page_clients(callback: CallbackQuery):
    try:
        # Формат: page_info_1
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

    except ValueError:
        await callback.answer("❌ Неверный ID", show_alert=True)
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

    except ValueError:
        await callback.answer("❌ Неверный ID", show_alert=True)
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
        keyboard = get_clients_list_keyboard(clients, action="info")

        await callback.message.edit_text(
            f"👥 Ваши ученики ({len(clients)} чел.):",
            reply_markup=keyboard
        )
        await callback.answer()

    except Exception as e:
        logger.error(f"Error in cancel_delete: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@router.callback_query(F.data.startswith("measurements_"))
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

    except ValueError:
        await callback.answer("❌ Неверный ID", show_alert=True)
    except Exception as e:
        logger.error(f"Error in view_client_measurements: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@router.callback_query(F.data.startswith("chart_"))
async def view_client_chart(callback: CallbackQuery):
    try:
        from app.services.chart_service import ChartService
        from aiogram.types import BufferedInputFile

        client_id = int(callback.data.split("_")[1])
        client = db.get_user(client_id)

        if not client:
            await callback.answer("❌ Ученик не найден", show_alert=True)
            return

        measurements = db.get_measurements(client_id, days=30)

        if len(measurements) < 2:
            await callback.message.edit_text(
                "❌ Недостаточно данных для графика.\nНужно минимум 2 замера.",
                reply_markup=get_back_keyboard()
            )
            await callback.answer()
            return

        chart_service = ChartService()
        chart_data = await chart_service.generate_stats_chart_bytes(client_id, measurements)

        if not chart_data:
            await callback.message.edit_text(
                "❌ Ошибка при генерации графика.",
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

    except ValueError:
        await callback.answer("❌ Неверный ID", show_alert=True)
    except Exception as e:
        logger.error(f"Error in view_client_chart: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@router.callback_query(F.data.startswith("report_"))
async def generate_client_report(callback: CallbackQuery):
    try:
        from app.services.pdf_service import PDFService
        from app.services.chart_service import ChartService
        from aiogram.types import FSInputFile

        client_id = int(callback.data.split("_")[1])
        client = db.get_user(client_id)

        if not client:
            await callback.answer("❌ Ученик не найден", show_alert=True)
            return

        measurements = db.get_measurements(client_id, days=28)

        if len(measurements) < 2:
            await callback.message.edit_text(
                "❌ Недостаточно данных для отчёта.\nНужно минимум 2 замера.",
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

    except ValueError:
        await callback.answer("❌ Неверный ID", show_alert=True)
    except Exception as e:
        logger.error(f"Error in generate_client_report: {e}")
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

        await callback.message.edit_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=get_cancel_keyboard()
        )

        # TODO: Добавить FSM для ожидания сообщения
        await callback.answer()

    except ValueError:
        await callback.answer("❌ Неверный ID", show_alert=True)
    except Exception as e:
        logger.error(f"Error in prompt_message_to_client: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)
