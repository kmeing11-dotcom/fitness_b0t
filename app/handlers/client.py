from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, BufferedInputFile
from aiogram.filters import Command
from aiogram.enums import ParseMode
from app.services.db_service import DatabaseService
from app.models import UserRole
from app.keyboards.inline import (
    get_clients_list_keyboard,
    get_client_action_keyboard,
    get_confirm_delete_keyboard,
    get_client_info_keyboard,
    get_back_keyboard,
    get_cancel_keyboard
)
from app.utils.logger import get_logger
import traceback

logger = get_logger(__name__)
router = Router()
db = DatabaseService()


# ============================================================
#  КОМАНДА /add_client
# ============================================================

@router.message(Command("add_client"))
async def add_client(message: Message):
    try:
        user = db.get_user_by_telegram(message.from_user.id)
        if not user:
            await message.answer("❌ Вы не зарегистрированы. Используйте /start.")
            return

        if user.role != UserRole.TRAINER:
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

        if client.telegram_id == user.telegram_id:
            await message.answer("❌ Вы не можете добавить самого себя.")
            return

        if client.role != UserRole.CLIENT:
            await message.answer(
                f"❌ @{username} не является учеником.\n"
                "Пользователь должен зарегистрироваться как ученик через /start."
            )
            return

        existing_clients = db.get_trainer_clients(user.id)
        if client.id in [c.id for c in existing_clients]:
            await message.answer(
                f"⚠️ @{username} уже является вашим учеником.\n"
                "Используйте /my_clients для просмотра списка."
            )
            return

        await message.bot.send_message(
            chat_id=client.telegram_id,
            text=(
                f"🏋️ <b>Приглашение от тренера!</b>\n\n"
                f"👨‍🏫 Тренер <b>{user.full_name}</b> хочет добавить вас в список учеников.\n\n"
                f"✅ Нажмите «Принять», чтобы стать учеником этого тренера.\n"
                f"❌ Нажмите «Отклонить», чтобы отказаться."
            ),
            parse_mode=ParseMode.HTML,
            reply_markup=get_client_action_keyboard("accept_invite", user.id)
        )

        await message.answer(
            f"✅ Приглашение отправлено пользователю @{username}.\n"
            f"⏳ Ожидайте подтверждения."
        )

        logger.info(f"📨 Invite sent from trainer {user.id} to client {client.id}")

    except Exception as e:
        logger.error(f"Error in add_client: {e}\n{traceback.format_exc()}")
        await message.answer("❌ Ошибка при отправке приглашения.")


# ============================================================
#  ПРИНЯТИЕ ПРИГЛАШЕНИЯ
# ============================================================

@router.callback_query(F.data.startswith("accept_invite:"))
async def accept_invite(callback: CallbackQuery):
    try:
        _, trainer_id = callback.data.split(":")
        trainer_id = int(trainer_id)

        client = db.get_user_by_telegram(callback.from_user.id)
        if not client:
            await callback.message.edit_text(
                "❌ Сначала зарегистрируйтесь через /start",
                reply_markup=get_cancel_keyboard()
            )
            await callback.answer()
            return

        if client.role != UserRole.CLIENT:
            await callback.message.edit_text(
                "❌ Вы должны быть учеником для принятия приглашения.\n"
                "Используйте /start для регистрации.",
                reply_markup=get_cancel_keyboard()
            )
            await callback.answer()
            return

        existing_clients = db.get_trainer_clients(trainer_id)
        if client.id in [c.id for c in existing_clients]:
            await callback.message.edit_text(
                "⚠️ Вы уже являетесь учеником этого тренера.",
                reply_markup=get_back_keyboard()
            )
            await callback.answer()
            return

        success = db.add_client_to_trainer(trainer_id, client.id)

        if success:
            await callback.message.edit_text(
                "✅ <b>Вы приняли приглашение!</b>\n\n"
                "Теперь вы ученик этого тренера.\n"
                "Вы можете начать вносить замеры через /set_measurements.",
                parse_mode=ParseMode.HTML,
                reply_markup=get_back_keyboard()
            )

            trainer = db.get_user(trainer_id)
            if trainer:
                await callback.bot.send_message(
                    chat_id=trainer.telegram_id,
                    text=(
                        f"✅ <b>Пользователь принял приглашение!</b>\n\n"
                        f"👤 Ученик: <b>{client.full_name}</b>\n"
                        f"📱 Username: @{client.username or 'Не указан'}\n\n"
                        f"📊 Теперь вы можете отслеживать его прогресс."
                    ),
                    parse_mode=ParseMode.HTML
                )
                logger.info(f"✅ Client {client.id} accepted invite from trainer {trainer_id}")
        else:
            await callback.message.edit_text(
                "❌ Не удалось добавить ученика. Попробуйте позже.",
                reply_markup=get_back_keyboard()
            )

        await callback.answer()

    except ValueError:
        await callback.answer("❌ Неверный формат данных", show_alert=True)
    except Exception as e:
        logger.error(f"Error in accept_invite: {e}")
        await callback.message.edit_text("❌ Ошибка при принятии приглашения.")
        await callback.answer()


@router.callback_query(F.data == "reject_invite")
async def reject_invite(callback: CallbackQuery):
    try:
        await callback.message.edit_text(
            "❌ Вы отклонили приглашение тренера.",
            reply_markup=get_back_keyboard()
        )
        await callback.answer()
    except Exception as e:
        logger.error(f"Error in reject_invite: {e}")
        await callback.answer("❌ Ошибка")


# ============================================================
#  КОМАНДА /my_clients
# ============================================================

@router.message(Command("my_clients"))
async def my_clients(message: Message):
    try:
        user = db.get_user_by_telegram(message.from_user.id)
        if not user:
            await message.answer("❌ Вы не зарегистрированы. Используйте /start.")
            return

        if user.role != UserRole.TRAINER:
            await message.answer("❌ Эта команда доступна только тренерам.")
            return

        clients = db.get_trainer_clients(user.id)

        if not clients:
            await message.answer(
                "📋 <b>У вас пока нет учеников.</b>\n\n"
                "Добавьте ученика: /add_client @username",
                parse_mode=ParseMode.HTML,
                reply_markup=get_back_keyboard()
            )
            return

        keyboard = get_clients_list_keyboard(clients, action="info")
        await message.answer(
            f"👥 <b>Ваши ученики</b> ({len(clients)} чел.):\n\n"
            f"<i>Нажмите на ученика для просмотра информации.</i>",
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard
        )

        logger.info(f"📋 Trainer {user.id} viewed clients list: {len(clients)} clients")

    except Exception as e:
        logger.error(f"Error in my_clients: {e}")
        await message.answer("❌ Ошибка при загрузке списка учеников.")


# ============================================================
#  ОБРАБОТКА ДЕЙСТВИЙ С КЛИЕНТОМ
# ============================================================

@router.callback_query(F.data.startswith("info_"))
async def handle_client_info(callback: CallbackQuery):
    try:
        client_id = int(callback.data.split("_")[1])
        await view_client_info(callback, client_id)

    except ValueError:
        await callback.answer("❌ Неверный ID", show_alert=True)
    except Exception as e:
        logger.error(f"Error in handle_client_info: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@router.callback_query(F.data.startswith("measurements_"))
async def handle_client_measurements(callback: CallbackQuery):
    try:
        client_id = int(callback.data.split("_")[1])
        await view_client_measurements(callback, client_id)

    except ValueError:
        await callback.answer("❌ Неверный ID", show_alert=True)
    except Exception as e:
        logger.error(f"Error in handle_client_measurements: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@router.callback_query(F.data.startswith("chart_"))
async def handle_client_chart(callback: CallbackQuery):
    try:
        client_id = int(callback.data.split("_")[1])
        await view_client_chart(callback, client_id)

    except ValueError:
        await callback.answer("❌ Неверный ID", show_alert=True)
    except Exception as e:
        logger.error(f"Error in handle_client_chart: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@router.callback_query(F.data.startswith("report_"))
async def handle_client_report(callback: CallbackQuery):
    try:
        client_id = int(callback.data.split("_")[1])
        await generate_client_report(callback, client_id)

    except ValueError:
        await callback.answer("❌ Неверный ID", show_alert=True)
    except Exception as e:
        logger.error(f"Error in handle_client_report: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@router.callback_query(F.data.startswith("delete_"))
async def handle_delete_client(callback: CallbackQuery):
    try:
        client_id = int(callback.data.split("_")[1])
        await confirm_delete_client(callback, client_id)

    except ValueError:
        await callback.answer("❌ Неверный ID", show_alert=True)
    except Exception as e:
        logger.error(f"Error in handle_delete_client: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@router.callback_query(F.data == "back_to_client")
async def back_to_client(callback: CallbackQuery):
    try:
        await callback.message.edit_text(
            "👥 <b>Ваши ученики</b>",
            parse_mode=ParseMode.HTML,
            reply_markup=get_back_keyboard()
        )
        await callback.answer()

    except Exception as e:
        logger.error(f"Error in back_to_client: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


# ============================================================
#  ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================

async def view_client_info(callback: CallbackQuery, client_id: int):
    client = db.get_user(client_id)
    if not client:
        await callback.message.edit_text(
            "❌ Ученик не найден.",
            reply_markup=get_back_keyboard()
        )
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

    keyboard = get_client_info_keyboard(client_id)
    await callback.message.edit_text(
        text,
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard
    )
    await callback.answer()


async def view_client_measurements(callback: CallbackQuery, client_id: int):
    client = db.get_user(client_id)
    if not client:
        await callback.message.edit_text(
            "❌ Ученик не найден.",
            reply_markup=get_back_keyboard()
        )
        await callback.answer()
        return

    measurements = db.get_measurements(client_id, days=30)

    if not measurements:
        await callback.message.edit_text(
            f"📊 У ученика <b>{client.full_name}</b> пока нет замеров.\n\n"
            "Попросите его внести замеры через /set_measurements.",
            parse_mode=ParseMode.HTML,
            reply_markup=get_back_keyboard()
        )
        await callback.answer()
        return

    sorted_measurements = sorted(measurements, key=lambda m: m.measured_at, reverse=True)
    last = sorted_measurements[0]

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

    if len(measurements) >= 2:
        first = measurements[0]
        text += "\n📈 <b>Изменения (за месяц):</b>\n"
        if first.weight and last.weight:
            change = last.weight - first.weight
            emoji = "⬇️" if change < 0 else "⬆️" if change > 0 else "➡️"
            text += f"{emoji} Вес: <b>{change:+.1f}</b> кг\n"

    await callback.message.edit_text(
        text,
        parse_mode=ParseMode.HTML,
        reply_markup=get_back_keyboard()
    )
    await callback.answer()


async def view_client_chart(callback: CallbackQuery, client_id: int):
    from app.services.chart_service import ChartService

    client = db.get_user(client_id)
    if not client:
        await callback.message.edit_text(
            "❌ Ученик не найден.",
            reply_markup=get_back_keyboard()
        )
        await callback.answer()
        return

    measurements = db.get_measurements(client_id, days=30)

    if len(measurements) < 2:
        await callback.message.edit_text(
            "❌ Недостаточно данных для построения графика.\n"
            "Нужно минимум 2 замера.",
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
        caption=f"📊 <b>График прогресса</b>\n👤 {client.full_name}\n📅 Последние 30 дней",
        parse_mode=ParseMode.HTML,
        reply_markup=get_back_keyboard()
    )
    await callback.answer()


async def generate_client_report(callback: CallbackQuery, client_id: int):
    from app.services.pdf_service import PDFService
    from app.services.chart_service import ChartService

    client = db.get_user(client_id)
    if not client:
        await callback.message.edit_text(
            "❌ Ученик не найден.",
            reply_markup=get_back_keyboard()
        )
        await callback.answer()
        return

    measurements = db.get_measurements(client_id, days=28)

    if len(measurements) < 2:
        await callback.message.edit_text(
            "❌ Недостаточно данных для отчёта.\n"
            "Нужно минимум 2 замера.",
            reply_markup=get_back_keyboard()
        )
        await callback.answer()
        return

    chart_service = ChartService()
    chart_path = await chart_service.generate_report_chart(client_id, measurements)

    pdf_service = PDFService()
    pdf_path = await pdf_service.generate_client_report(
        client_id, client, measurements, chart_path
    )

    if not pdf_path:
        await callback.message.edit_text(
            "❌ Ошибка при генерации отчёта.",
            reply_markup=get_back_keyboard()
        )
        await callback.answer()
        return

    from aiogram.types import FSInputFile
    await callback.message.delete()
    await callback.message.answer_document(
        document=FSInputFile(pdf_path),
        caption=(
            f"📄 <b>Отчёт о прогрессе</b>\n"
            f"👤 {client.full_name}\n"
            f"📅 {datetime.now().strftime('%d.%m.%Y')}\n"
            f"📊 Замеров: {len(measurements)}"
        ),
        parse_mode=ParseMode.HTML,
        reply_markup=get_back_keyboard()
    )
    await callback.answer()


async def confirm_delete_client(callback: CallbackQuery, client_id: int):
    client = db.get_user(client_id)
    if not client:
        await callback.message.edit_text(
            "❌ Ученик не найден.",
            reply_markup=get_back_keyboard()
        )
        await callback.answer()
        return

    text = (
        f"⚠️ <b>Подтверждение удаления</b>\n\n"
        f"Вы уверены, что хотите удалить ученика\n"
        f"<b>{client.full_name}</b> (@{client.username})?\n\n"
        f"<i>Все данные ученика будут сохранены в истории.</i>"
    )

    keyboard = get_confirm_delete_keyboard(client_id)

    await callback.message.edit_text(
