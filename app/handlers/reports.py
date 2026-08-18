from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.filters import Command
from aiogram.enums import ParseMode
from datetime import datetime
from app.services.db_service import DatabaseService
from app.services.pdf_service import PDFService
from app.services.chart_service import ChartService
from app.models import UserRole
from app.keyboards.inline import get_back_keyboard, get_clients_list_keyboard
from app.utils.logger import get_logger
import traceback
import os

logger = get_logger(__name__)
router = Router()
db = DatabaseService()
pdf_service = PDFService()
chart_service = ChartService()


# ============================================================
#  КОМАНДА /report (для тренера)
# ============================================================

@router.message(Command("report"))
async def report_command(message: Message):
    """
    Команда /report @username — генерация PDF-отчёта для ученика (тренер).
    """
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
            clients = db.get_trainer_clients(user.id)
            if not clients:
                await message.answer(
                    "📭 У вас пока нет учеников.\n\n"
                    "Добавьте ученика: /add_client @username",
                    reply_markup=get_back_keyboard()
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

        username = args[1].lstrip('@')
        client = db.get_user_by_username(username)

        if not client:
            await message.answer(f"❌ Пользователь @{username} не найден.")
            return

        clients = db.get_trainer_clients(user.id)
        if client.id not in [c.id for c in clients]:
            await message.answer(f"❌ @{username} не является вашим учеником.")
            return

        await generate_report(message, client)

    except Exception as e:
        logger.error(f"Error in report_command: {e}\n{traceback.format_exc()}")
        await message.answer("❌ Ошибка при генерации отчёта.")


# ============================================================
#  КОМАНДА /my_report (для ученика)
# ============================================================

@router.message(Command("my_report"))
async def my_report_command(message: Message):
    """
    Команда /my_report — генерация собственного отчёта (ученик).
    """
    try:
        user = db.get_user_by_telegram(message.from_user.id)
        if not user:
            await message.answer("❌ Вы не зарегистрированы. Используйте /start.")
            return

        if user.role != UserRole.CLIENT:
            await message.answer("❌ Эта команда доступна только ученикам.")
            return

        await generate_report(message, user)

    except Exception as e:
        logger.error(f"Error in my_report_command: {e}\n{traceback.format_exc()}")
        await message.answer("❌ Ошибка при генерации отчёта.")


# ============================================================
#  ОБРАБОТЧИКИ INLINE-КНОПОК
# ============================================================

@router.callback_query(F.data.startswith("report_select_"))
async def report_select_client(callback: CallbackQuery):
    """
    Выбор клиента для отчёта из списка.
    Callback: report_select_{client_id}
    """
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

        clients = db.get_trainer_clients(trainer.id)
        if client.id not in [c.id for c in clients]:
            await callback.answer("❌ Это не ваш ученик.", show_alert=True)
            return

        await callback.message.edit_text(
            f"⏳ Генерация отчёта для <b>{client.full_name}</b>...",
            parse_mode=ParseMode.HTML
        )

        await generate_report(callback.message, client)
        await callback.answer()

    except ValueError:
        await callback.answer("❌ Неверный ID", show_alert=True)
    except Exception as e:
        logger.error(f"Error in report_select_client: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@router.callback_query(F.data.startswith("report_pdf_"))
async def report_pdf_callback(callback: CallbackQuery):
    """
    Генерация PDF-отчёта для ученика (для ученика).
    Callback: report_pdf_{client_id}
    """
    try:
        client_id = int(callback.data.split("_")[2])
        client = db.get_user(client_id)

        if not client:
            await callback.answer("❌ Ученик не найден.", show_alert=True)
            return

        await callback.message.edit_text(
            f"⏳ Генерация отчёта...",
            parse_mode=ParseMode.HTML
        )

        await generate_report(callback.message, client)
        await callback.answer()

    except ValueError:
        await callback.answer("❌ Неверный ID", show_alert=True)
    except Exception as e:
        logger.error(f"Error in report_pdf_callback: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


# ============================================================
#  ОСНОВНАЯ ФУНКЦИЯ ГЕНЕРАЦИИ ОТЧЁТА
# ============================================================

async def generate_report(message: Message, client):
    """
    Генерирует PDF-отчёт и отправляет пользователю.
    """
    try:
        measurements = db.get_measurements(client.id, days=90)

        if len(measurements) < 2:
            await message.answer(
                f"❌ Недостаточно данных для отчёта.\n"
                f"У {client.full_name} всего {len(measurements)} замеров.\n"
                f"Нужно минимум 2 замера.",
                reply_markup=get_back_keyboard()
            )
            return

        chart_path = await chart_service.generate_report_chart(client.id, measurements)

        pdf_path = await pdf_service.generate_client_report(
            user_id=client.id,
            client=client,
            measurements=measurements,
            chart_path=chart_path
        )

        if not pdf_path:
            await message.answer(
                "❌ Не удалось сгенерировать отчёт. Попробуйте позже.",
                reply_markup=get_back_keyboard()
            )
            return

        document = FSInputFile(pdf_path)

        first = measurements[0]
        last = measurements[-1]
        weight_change = ""
        if first.weight and last.weight:
            change = last.weight - first.weight
            emoji = "⬇️" if change < 0 else "⬆️" if change > 0 else "➡️"
            weight_change = f"{emoji} Изменение веса: {change:+.1f} кг"

        caption = (
            f"📄 <b>Отчёт о прогрессе</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 <b>Ученик:</b> {client.full_name or client.username}\n"
            f"📅 <b>Дата:</b> {datetime.now().strftime('%d.%m.%Y')}\n"
            f"📊 <b>Замеров:</b> {len(measurements)}\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"{weight_change}\n"
        )

        await message.answer_document(
            document=document,
            caption=caption,
            parse_mode=ParseMode.HTML,
            reply_markup=get_back_keyboard()
        )

        try:
            os.remove(pdf_path)
            if chart_path:
                os.remove(chart_path)
        except Exception as e:
            logger.warning(f"Could not delete temp files: {e}")

        logger.info(f"📄 Report generated for client {client.id} by {message.from_user.id}")

    except Exception as e:
        logger.error(f"Error in generate_report: {e}\n{traceback.format_exc()}")
        await message.answer(
            "❌ Ошибка при генерации отчёта.",
            reply_markup=get_back_keyboard()
        )


@router.message(Command("report_help"))
async def report_help(message: Message):
    """Помощь по командам отчётов."""
    user = db.get_user_by_telegram(message.from_user.id)
    if not user:
        await message.answer("❌ Вы не зарегистрированы. Используйте /start.")
        return

    if user.role == UserRole.TRAINER:
        help_text = (
            "📄 <b>Помощь по отчётам (тренер)</b>\n\n"
            "📌 <b>Команды:</b>\n"
            "• /report @username — сгенерировать PDF-отчёт для ученика\n"
            "• /report — показать список учеников для выбора\n\n"
            "📌 <b>Что включает отчёт:</b>\n"
            "• Информация о клиенте\n"
            "• Таблица замеров (последние 4 недели)\n"
            "• График веса\n"
            "• Сводка изменений\n"
            "• Рекомендации"
        )
    else:
        help_text = (
            "📄 <b>Помощь по отчётам (ученик)</b>\n\n"
            "📌 <b>Команды:</b>\n"
            "• /my_report — сгенерировать ваш PDF-отчёт\n\n"
            "📌 <b>Что включает отчёт:</b>\n"
            "• Ваша информация\n"
            "• Таблица замеров\n"
            "• График веса\n"
            "• Сводка изменений"
        )

    await message.answer(help_text, parse_mode=ParseMode.HTML, reply_markup=get_back_keyboard())
