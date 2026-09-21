# app/handlers/stats.py
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, BufferedInputFile
from aiogram.filters import Command
from aiogram.enums import ParseMode
import traceback

from app.services.db_service import DatabaseService
from app.services.chart_service import ChartService
from app.models import UserRole
from app.keyboards.inline import (
    get_clients_list_keyboard,
    get_stats_period_keyboard,
    get_back_inline_keyboard
)
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = Router()
db = DatabaseService()
chart_service = ChartService()


# ============================================================
#  /stats
# ============================================================

@router.message(Command("stats"))
async def stats_command(message: Message):
    try:
        user = db.get_user_by_telegram(message.from_user.id)
        if not user:
            await message.answer("❌ Вы не зарегистрированы. Используйте /start.")
            return

        if user['role'] != UserRole.TRAINER.value:
            await message.answer("❌ Эта команда доступна только тренерам.")
            return

        args = message.text.split()

        # /stats @username — сразу к выбору периода
        if len(args) >= 2:
            username = args[1].lstrip('@')
            client = db.get_user_by_username(username)

            if not client:
                await message.answer(f"❌ Пользователь @{username} не найден.")
                return

            clients = db.get_trainer_clients(user['id'])
            client_ids = {c['id'] for c in clients}

            if client['id'] not in client_ids:
                await message.answer(f"❌ @{username} не является вашим учеником.")
                return

            await message.answer(
                f"📊 <b>Статистика для {client['full_name']}</b>\n\n"
                f"Выберите период:",
                parse_mode=ParseMode.HTML,
                reply_markup=get_stats_period_keyboard(client['id'])
            )
            return

        # /stats — выбор ученика
        clients = db.get_trainer_clients(user['id'])

        if not clients:
            await message.answer(
                "👥 У вас пока нет учеников.\n"
                "Чтобы добавить ученика, используйте /add_client.",
                reply_markup=get_back_inline_keyboard("back_to_menu")
            )
            return

        keyboard = get_clients_list_keyboard(clients, action="stats_select")

        await message.answer(
            f"👥 <b>Выберите ученика для просмотра статистики:</b>",
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard
        )

    except Exception as e:
        logger.error(f"Error in stats_command: {e}\n{traceback.format_exc()}")
        await message.answer("❌ Произошла ошибка при загрузке статистики.")


# ============================================================
#  ВЫБОР УЧЕНИКА → ПЕРИОД
# ============================================================

@router.callback_query(F.data.startswith("stats_select_"))
async def stats_select_client(callback: CallbackQuery):
    try:
        client_id = int(callback.data.split("_")[2])
        client = db.get_user(client_id)

        if not client:
            await callback.answer("❌ Ученик не найден", show_alert=True)
            return

        trainer = db.get_user_by_telegram(callback.from_user.id)
        if not trainer:
            await callback.answer("❌ Тренер не найден", show_alert=True)
            return

        clients = db.get_trainer_clients(trainer['id'])
        client_ids = {c['id'] for c in clients}

        if client['id'] not in client_ids:
            await callback.answer("❌ Это не ваш ученик", show_alert=True)
            return

        await callback.message.edit_text(
            f"📊 <b>Статистика для {client['full_name']}</b>\n\n"
            f"Выберите период для отображения:",
            parse_mode=ParseMode.HTML,
            reply_markup=get_stats_period_keyboard(client['id'])
        )
        await callback.answer()

    except Exception as e:
        logger.error(f"Error in stats_select_client: {e}\n{traceback.format_exc()}")
        await callback.answer("❌ Ошибка", show_alert=True)


# ============================================================
#  ВЫБОР ПЕРИОДА → ГЕНЕРАЦИЯ ГРАФИКА
# ============================================================

@router.callback_query(F.data.startswith("stats_period_"))
async def stats_period_selected(callback: CallbackQuery):
    try:
        logger.info(f"📥 [stats_period_] data: {callback.data}")

        # FIX: формат stats_period_{days}_{client_id} или stats_period_{days}
        parts = callback.data.split("_")
        if len(parts) < 3:
            await callback.answer("❌ Неверный формат", show_alert=True)
            return

        days_str = parts[2]

        # FIX: client_id опционален
        if len(parts) >= 4 and parts[3].isdigit():
            client_id = int(parts[3])
        else:
            # Если client_id не передан — берём из FSM? Нет FSM. Игнор.
            client_id = None

        if client_id is None:
            await callback.answer(
                "❌ Не указан ID ученика. Используйте /stats заново.",
                show_alert=True
            )
            return

        if days_str == "all":
            days = 365
        else:
            try:
                days = int(days_str)
            except ValueError:
                await callback.answer("❌ Неверный период", show_alert=True)
                return

        client = db.get_user(client_id)
        if not client:
            await callback.answer("❌ Ученик не найден", show_alert=True)
            return

        measurements = db.get_measurements(client['id'], days=days)

        if len(measurements) < 2:
            await callback.message.edit_text(
                f"❌ Недостаточно данных для периода в {days} дней.\n"
                f"Найдено {len(measurements)} замеров, нужно минимум 2.\n\n"
                "Попробуйте выбрать больший период.",
                reply_markup=get_back_inline_keyboard("back_to_stats")
            )
            await callback.answer()
            return

        await callback.message.edit_text("⏳ Генерация графика...")
        await callback.answer()

        chart_data = await chart_service.generate_stats_chart_bytes(
            client['id'],
            measurements
        )

        if not chart_data:
            await callback.message.edit_text(
                "❌ Не удалось сгенерировать график. Попробуйте позже.",
                reply_markup=get_back_inline_keyboard("back_to_stats")
            )
            return

        period_text = f"последние {days} дней" if days != 365 else "всё время"

        photo = BufferedInputFile(
            chart_data,
            filename=f"stats_{client['id']}_{days}.png"
        )

        await callback.message.delete()
        await callback.message.answer_photo(
            photo=photo,
            caption=(
                f"📊 <b>Статистика прогресса</b>\n"
                f"👤 {client['full_name'] or client['username']}\n"
                f"📅 Период: {period_text}\n"
                f"📊 Замеров: {len(measurements)}"
            ),
            parse_mode=ParseMode.HTML
        )

    except ValueError:
        await callback.answer("❌ Неверный формат данных", show_alert=True)
    except Exception as e:
        logger.error(f"Error in stats_period_selected: {e}\n{traceback.format_exc()}")
        await callback.answer("❌ Ошибка при генерации графика", show_alert=True)


# ============================================================
#  НАЗАД К СПИСКУ УЧЕНИКОВ
# ============================================================

@router.callback_query(F.data == "back_to_stats")
async def back_to_stats(callback: CallbackQuery):
    try:
        trainer = db.get_user_by_telegram(callback.from_user.id)
        if not trainer:
            await callback.answer("❌ Тренер не найден", show_alert=True)
            return

        clients = db.get_trainer_clients(trainer['id'])

        if not clients:
            await callback.message.edit_text(
                "👥 У вас пока нет учеников.\n"
                "Чтобы добавить ученика, используйте /add_client.",
                reply_markup=get_back_inline_keyboard("back_to_menu")
            )
            await callback.answer()
            return

        keyboard = get_clients_list_keyboard(clients, action="stats_select")
        await callback.message.edit_text(
            f"👥 <b>Выберите ученика для просмотра статистики:</b>",
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard
        )
        await callback.answer()

    except Exception as e:
        logger.error(f"Error in back_to_stats: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)
