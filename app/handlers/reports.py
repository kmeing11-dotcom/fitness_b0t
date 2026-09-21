# app/handlers/reports.py
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.filters import Command
from aiogram.enums import ParseMode
from datetime import datetime
import os
import traceback

from app.services.db_service import DatabaseService
from app.services.pdf_service import PDFService
from app.services.chart_service import ChartService
from app.models import UserRole
from app.keyboards.inline import (
    get_clients_list_keyboard,
    get_back_inline_keyboard
)
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = Router()
db = DatabaseService()
pdf_service = PDFService()
chart_service = ChartService()


# ============================================================
#  /report — для тренера
# ============================================================

@router.message(Command("report"))
async def report_command(message: Message):
    try:
        user = db.get_user_by_telegram(message.from_user.id)
        if not user:
            await message.answer("❌ Вы не зарегистрированы. Используйте /start.")
            return

        if user['role'] != UserRole.TRAINER.value:
            await message.answer("❌ Эта команда доступна только тренерам.")
            return

        args = message.text.split()

        # Без аргумента — список учеников
        if len(args) < 2:
            clients = db.get_trainer_clients(user['id'])
            if not clients:
                await message.answer(
                    "📭 У вас пока нет учеников.\n\n"
                    "Добавьте ученика: /add_client @username",
                    reply_markup=get_back_inline_keyboard("back_to_menu")
                )
                return

            keyboard = get_clients_list_keyboard(clients, action="report_select")
            await message.answer(
                "📄 <b>Выберите ученика для отчёта:</b>\n\n"
                "<i>Будет сгенерирован PDF-отчёт с графиком и статистикой.</i>",
                parse_mode=ParseMode.HTML,
                reply_markup=keyboard
            )
            return

        # С аргументом @username
        username = args[1].lstrip('@')
        client = db.get_user_by_username(username)

        if not client:
            await message.answer(f"❌ Пользователь @{username} не найден.")
            return

        clients = db.get_trainer_clients(user['id'])
        if client['id'] not in [c['id'] for c in clients]:
            await message.answer(f"❌ @{username} не является вашим учеником.")
            return

        # FIX: передаём user_id явно, а не через message.from_user
        await generate_report(
            message=message,
            client=client,
            requester_id=message.from_user.id
        )

    except Exception as e:
        logger.error(f"Error in report_command: {e}\n{traceback.format_exc()}")
        await message.answer("❌ Ошибка при генерации отчёта.")


# ============================================================
#  /my_report — для ученика
# ============================================================

@router.message(Command("my_report"))
async def my_report_command(message: Message):
    try:
        user = db.get_user_by_telegram(message.from_user.id)
        if not user:
            await message.answer("❌ Вы не зарегистрированы. Используйте /start.")
            return

        if user['role'] != UserRole.CLIENT.value:
            await message.answer("❌ Эта команда доступна только ученикам.")
            return

        await generate_report(
            message=message,
            client=user,
            requester_id=message.from_user.id
        )

    except Exception as e:
        logger.error(f"Error in my_report_command: {e}\n{traceback.format_exc()}")
        await message.answer("❌ Ошибка при генерации отчёта.")


# ============================================================
#  CALLBACK — выбор ученика из списка
# ============================================================

@router.callback_query(F.data.startswith("report_select_"))
async def report_select_client(callback: CallbackQuery):
    try:
        client_id = int(callback.data.split("_")[2])
        client = db.get_user(client_id)

        if not client:
            await callback.answer("❌ Ученик не найден.", show_alert=True)
            return

        trainer = db.get_user_by_telegram(callback.from_user.id)
        if not trainer:
            await callback.answer("❌ Тренер не найден.", show_alert=True)
            return

        clients = db.get_trainer_clients(trainer['id'])
        if client['id'] not in [c['id'] for c in clients]:
            await callback.answer("❌ Это не ваш ученик.", show_alert=True)
            return

        await callback.message.edit_text(
            f"⏳ Генерация отчёта для <b>{client['full_name']}</b>...",
            parse_mode=ParseMode.HTML
        )

        # FIX: передаём requester_id = callback.from_user.id
        await generate_report(
            message=callback.message,
            client=client,
            requester_id=callback.from_user.id
        )
        await callback.answer()

    except ValueError:
        await callback.answer("❌ Неверный ID", show_alert=True)
    except Exception as e:
        logger.error(f"Error in report_select_client: {e}\n{traceback.format_exc()}")
        await callback.answer("❌ Ошибка", show_alert=True)


# ============================================================
#  ГЕНЕРАЦИЯ ОТЧЁТА
# ============================================================

async def generate_report(message: Message, client, requester_id: int):
    """
    FIX: requester_id передаётся явно, потому что
    callback.message.from_user = БОТ, а не пользователь.
    """
    try:
        measurements = db.get_measurements(client['id'], days=90)

        if len(measurements) < 2:
            await message.answer(
                f"❌ Недостаточно данных для отчёта.\n"
                f"У {client['full_name']} всего {len(measurements)} замеров.\n"
                f"Нужно минимум 2 замера.",
                reply_markup=get_back_inline_keyboard("back_to_menu")
            )
            return

        chart_path = await chart_service.generate_report_chart(
            client['id'], measurements
        )

        pdf_path = await pdf_service.generate_client_report(
            user_id=client['id'],
            client=client,
            measurements=measurements,
            chart_path=chart_path
        )

        if not pdf_path:
            await message.answer(
                "❌ Не удалось сгенерировать отчёт. Попробуйте позже.",
                reply_markup=get_back_inline_keyboard("back_to_menu")
            )
            return

        document = FSInputFile(pdf_path)

        # FIX: dict-style
        first = measurements[0]
        last = measurements[-1]
        weight_change = ""
        if first.get('weight') and last.get('weight'):
            change = last['weight'] - first['weight']
            emoji = "⬇️" if change < 0 else "⬆️" if change > 0 else "➡️"
            weight_change = f"{emoji} Изменение веса: {change:+.1f} кг"

        caption = (
            f"📄 <b>Отчёт о прогрессе</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 <b>Ученик:</b> {client['full_name'] or client['username']}\n"
            f"📅 <b>Дата:</b> {datetime.now().strftime('%d.%m.%Y')}\n"
            f"📊 <b>Замеров:</b> {len(measurements)}\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"{weight_change}\n"
        )

        await message.answer_document(
            document=document,
            caption=caption,
            parse_mode=ParseMode.HTML
        )

        # Удаляем временные файлы
        try:
            os.remove(pdf_path)
            if chart_path and os.path.exists(chart_path):
                os.remove(chart_path)
        except Exception as e:
            logger.warning(f"Could not delete temp files: {e}")

        logger.info(
            f"📄 Report generated for client {client['id']} "
            f"by {requester_id}"
        )

    except Exception as e:
        logger.error(f"Error in generate_report: {e}\n{traceback.format_exc()}")
        await message.answer(
            "❌ Ошибка при генерации отчёта.",
            reply_markup=get_back_inline_keyboard("back_to_menu")
        )
