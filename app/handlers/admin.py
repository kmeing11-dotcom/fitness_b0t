# app/handlers/admin.py
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.enums import ParseMode
from datetime import datetime
import traceback

from app.config import Config
from app.services.db_service import DatabaseService
from app.services.backup_service import BackupService
from app.models import UserRole
from app.keyboards.inline import (
    get_cancel_keyboard,
    get_admin_keyboard,
    get_back_inline_keyboard,
    get_broadcast_confirm_keyboard
)
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = Router()
db = DatabaseService()
backup_service = BackupService()


class BroadcastStates(StatesGroup):
    entering_message = State()
    confirming = State()


def is_admin(user_id: int) -> bool:
    admin_ids = Config.get_admin_ids()
    return user_id in admin_ids if admin_ids else False


# ============================================================
#  /admin
# ============================================================

@router.message(Command("admin"))
async def admin_panel(message: Message):
    try:
        if not is_admin(message.from_user.id):
            await message.answer("❌ Доступ запрещён.")
            return

        await message.answer(
            "🔐 <b>Административная панель</b>\n\n"
            "Выберите действие:",
            parse_mode=ParseMode.HTML,
            reply_markup=get_admin_keyboard()
        )
        logger.info(f"🔐 Admin panel opened by {message.from_user.id}")

    except Exception as e:
        logger.error(f"Error in admin_panel: {e}")
        await message.answer("❌ Ошибка.")


# ============================================================
#  СТАТИСТИКА
# ============================================================

@router.callback_query(F.data == "admin_stats")
async def admin_stats_callback(callback: CallbackQuery):
    try:
        if not is_admin(callback.from_user.id):
            await callback.answer("❌ Доступ запрещён.", show_alert=True)
            return

        trainers = db.get_users_by_role(UserRole.TRAINER)
        clients = db.get_users_by_role(UserRole.CLIENT)
        all_users = db.get_all_users()
        active_subscriptions = db.get_all_active_subscriptions()
        today_measurements = db.get_daily_measurements_count()

        response = (
            "📊 <b>Статистика системы</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"👨‍🏫 <b>Тренеры:</b> {len(trainers)}\n"
            f"👨‍🎓 <b>Ученики:</b> {len(clients)}\n"
            f"👥 <b>Всего пользователей:</b> {len(all_users)}\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            f"💎 <b>Активных подписок:</b> {active_subscriptions}\n"
            f"📊 <b>Замеров сегодня:</b> {today_measurements}\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            f"📅 <b>Дата:</b> {datetime.now().strftime('%d.%m.%Y %H:%M')}"
        )

        await callback.message.edit_text(
            response,
            parse_mode=ParseMode.HTML,
            reply_markup=get_admin_keyboard()
        )
        await callback.answer()

    except Exception as e:
        logger.error(f"Error in admin_stats_callback: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


# ============================================================
#  ПОЛЬЗОВАТЕЛИ
# ============================================================

@router.callback_query(F.data == "admin_users")
async def admin_users_callback(callback: CallbackQuery):
    try:
        if not is_admin(callback.from_user.id):
            await callback.answer("❌ Доступ запрещён.", show_alert=True)
            return

        users = db.get_all_users()
        if not users:
            await callback.message.edit_text(
                "📭 В системе нет пользователей.",
                reply_markup=get_admin_keyboard()
            )
            await callback.answer()
            return

        trainers = [u for u in users if u['role'] == UserRole.TRAINER.value]
        clients = [u for u in users if u['role'] == UserRole.CLIENT.value]

        response = "👥 <b>Список пользователей</b>\n"
        response += "━━━━━━━━━━━━━━━━━━━━━\n\n"
        response += f"👨‍🏫 <b>Тренеры ({len(trainers)}):</b>\n"
        for t in trainers[:10]:
            response += f"  • {t['full_name'] or 'Без имени'} (@{t['username'] or 'no_username'})\n"
        if len(trainers) > 10:
            response += f"  ... и ещё {len(trainers) - 10}\n"

        response += f"\n👨‍🎓 <b>Ученики ({len(clients)}):</b>\n"
        for c in clients[:10]:
            response += f"  • {c['full_name'] or 'Без имени'} (@{c['username'] or 'no_username'})\n"
        if len(clients) > 10:
            response += f"  ... и ещё {len(clients) - 10}\n"

        await callback.message.edit_text(
            response,
            parse_mode=ParseMode.HTML,
            reply_markup=get_admin_keyboard()
        )
        await callback.answer()

    except Exception as e:
        logger.error(f"Error in admin_users_callback: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


# ============================================================
#  ПОДПИСКИ
# ============================================================

@router.callback_query(F.data == "admin_subscriptions")
async def admin_subscriptions_callback(callback: CallbackQuery):
    try:
        if not is_admin(callback.from_user.id):
            await callback.answer("❌ Доступ запрещён.", show_alert=True)
            return

        users = db.get_all_users()
        subscriptions = []
        for user in users:
            sub = db.get_user_subscription(user['id'])
            if sub and sub['is_active']:
                subscriptions.append({'user': user, 'subscription': sub})

        if not subscriptions:
            await callback.message.edit_text(
                "📭 Нет активных подписок.",
                reply_markup=get_admin_keyboard()
            )
            await callback.answer()
            return

        response = "💎 <b>Активные подписки</b>\n"
        response += "━━━━━━━━━━━━━━━━━━━━━\n\n"

        for item in subscriptions[:20]:
            user = item['user']
            sub = item['subscription']
            status = "🟢" if sub['expires_at'] > datetime.now() else "🔴"
            response += (
                f"• {user['full_name'] or user['username']} "
                f"(@{user['username'] or 'no_username'})\n"
                f"  📅 До: {sub['expires_at'].strftime('%d.%m.%Y')} {status}\n"
            )

        if len(subscriptions) > 20:
            response += f"\n... и ещё {len(subscriptions) - 20}"

        await callback.message.edit_text(
            response,
            parse_mode=ParseMode.HTML,
            reply_markup=get_admin_keyboard()
        )
        await callback.answer()

    except Exception as e:
        logger.error(f"Error in admin_subscriptions_callback: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


# ============================================================
#  РАССЫЛКА
# ============================================================

@router.callback_query(F.data == "admin_broadcast")
async def admin_broadcast_callback(callback: CallbackQuery, state: FSMContext):
    try:
        if not is_admin(callback.from_user.id):
            await callback.answer("❌ Доступ запрещён.", show_alert=True)
            return

        await callback.message.edit_text(
            "📨 <b>Создание рассылки</b>\n\n"
            "Введите текст сообщения:",
            parse_mode=ParseMode.HTML,
            reply_markup=get_admin_keyboard()
        )
        await callback.message.answer(
            "👇 Или нажмите «Отмена»:",
            reply_markup=get_cancel_keyboard()
        )
        await state.set_state(BroadcastStates.entering_message)
        await callback.answer()

    except Exception as e:
        logger.error(f"Error in admin_broadcast_callback: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@router.message(StateFilter(BroadcastStates.entering_message))
async def process_broadcast_message(message: Message, state: FSMContext):
    try:
        if message.text == "❌ Отмена":
            await state.clear()
            await message.answer(
                "❌ Рассылка отменена.",
                reply_markup=get_admin_keyboard()
            )
            return

        await state.update_data(broadcast_text=message.text)
        users = db.get_all_users()

        await message.answer(
            f"📨 <b>Подтверждение</b>\n\n"
            f"Получателей: <b>{len(users)}</b>\n\n"
            f"📝 Текст:\n{message.text}\n\n"
            f"Отправить?",
            parse_mode=ParseMode.HTML,
            reply_markup=get_broadcast_confirm_keyboard()
        )
        await state.set_state(BroadcastStates.confirming)

    except Exception as e:
        logger.error(f"Error in process_broadcast_message: {e}")
        await message.answer("❌ Ошибка.")


@router.callback_query(StateFilter(BroadcastStates.confirming), F.data == "broadcast_confirm")
async def confirm_broadcast(callback: CallbackQuery, state: FSMContext):
    try:
        data = await state.get_data()
        text = data.get('broadcast_text')

        if not text:
            await callback.message.edit_text("❌ Текст не найден.")
            await callback.answer()
            await state.clear()
            return

        users = db.get_all_users()
        sent = 0
        failed = 0

        await callback.message.edit_text("⏳ Отправка...")

        for user in users:
            try:
                await callback.bot.send_message(
                    chat_id=user['telegram_id'],
                    text=text,
                    parse_mode=ParseMode.HTML
                )
                sent += 1
            except Exception as e:
                failed += 1
                logger.warning(f"Broadcast failed for {user['id']}: {e}")

        db.broadcast_message(text, callback.from_user.id)

        await callback.message.edit_text(
            f"✅ <b>Рассылка завершена</b>\n\n"
            f"✅ Отправлено: {sent}\n"
            f"❌ Ошибок: {failed}",
            parse_mode=ParseMode.HTML,
            reply_markup=get_admin_keyboard()
        )
        await state.clear()
        await callback.answer()

    except Exception as e:
        logger.error(f"Error in confirm_broadcast: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)
        await state.clear()


@router.callback_query(StateFilter(BroadcastStates.confirming), F.data == "broadcast_cancel")
async def cancel_broadcast(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "❌ Рассылка отменена.",
        reply_markup=get_admin_keyboard()
    )
    await state.clear()
    await callback.answer()


# ============================================================
#  БЭКАП
# ============================================================

@router.callback_query(F.data == "admin_backup")
async def admin_backup_callback(callback: CallbackQuery):
    try:
        if not is_admin(callback.from_user.id):
            await callback.answer("❌ Доступ запрещён.", show_alert=True)
            return

        await callback.message.edit_text("⏳ Создание бэкапа...")
        await callback.answer()

        backup_path = await backup_service.backup_database(compress=True)

        if not backup_path:
            await callback.message.edit_text(
                "❌ Не удалось создать бэкап.\n"
                "<i>Для PostgreSQL файловый бэкап недоступен.</i>",
                parse_mode=ParseMode.HTML,
                reply_markup=get_admin_keyboard()
            )
            return

        await callback.message.delete()
        await callback.message.answer_document(
            document=FSInputFile(backup_path),
            caption=f"💾 Бэкап от {datetime.now().strftime('%d.%m.%Y %H:%M')}"
        )

    except Exception as e:
        logger.error(f"Error in admin_backup_callback: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


# ============================================================
#  ЛОГИ
# ============================================================

@router.callback_query(F.data == "admin_logs")
async def admin_logs_callback(callback: CallbackQuery):
    try:
        if not is_admin(callback.from_user.id):
            await callback.answer("❌ Доступ запрещён.", show_alert=True)
            return

        from pathlib import Path
        from collections import deque

        log_path = Path(Config.LOG_FILE)
        if not log_path.exists():
            await callback.message.edit_text(
                "❌ Файл логов не найден.",
                reply_markup=get_admin_keyboard()
            )
            await callback.answer()
            return

        with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
            last_lines = list(deque(f, maxlen=100))

        log_text = "".join(last_lines)

        if len(log_text) > 4000:
            await callback.message.delete()
            await callback.message.answer_document(
                document=FSInputFile(log_path),
                caption=f"📋 Логи от {datetime.now().strftime('%d.%m.%Y %H:%M')}"
            )
        else:
            await callback.message.edit_text(
                f"📋 <b>Последние логи:</b>\n\n<code>{log_text}</code>",
                parse_mode=ParseMode.HTML,
                reply_markup=get_admin_keyboard()
            )

        await callback.answer()

    except Exception as e:
        logger.error(f"Error in admin_logs_callback: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


# ============================================================
#  /admin_stats — команда
# ============================================================

@router.message(Command("admin_stats"))
async def admin_stats(message: Message):
    try:
        if not is_admin(message.from_user.id):
            await message.answer("❌ Доступ запрещён.")
            return

        trainers = db.get_users_by_role(UserRole.TRAINER)
        clients = db.get_users_by_role(UserRole.CLIENT)
        all_users = db.get_all_users()
        active_subscriptions = db.get_all_active_subscriptions()
        today_measurements = db.get_daily_measurements_count()

        response = (
            "📊 <b>Статистика системы</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"👨‍🏫 Тренеры: {len(trainers)}\n"
            f"👨‍🎓 Ученики: {len(clients)}\n"
            f"👥 Всего: {len(all_users)}\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            f"💎 Активных подписок: {active_subscriptions}\n"
            f"📊 Замеров сегодня: {today_measurements}"
        )

        await message.answer(response, parse_mode=ParseMode.HTML)

    except Exception as e:
        logger.error(f"Error in admin_stats: {e}")
        await message.answer("❌ Ошибка.")


# ============================================================
#  ТЕСТ: WEEKLY ДАЙДЖЕСТ
# ============================================================

@router.message(Command("test_digest"))
async def test_digest(message: Message):
    """Отправляет дайджест СЕЙЧАС (для проверки). Только для админа."""
    try:
        if not is_admin(message.from_user.id):
            await message.answer("❌ Только для админов.")
            return

        from app.services.digest_service import DigestService

        await message.answer("⏳ Формирую дайджест...")

        user = db.get_user_by_telegram(message.from_user.id)
        if not user or user['role'] != UserRole.TRAINER.value:
            await message.answer(
                "❌ Вы не тренер. Используйте /test_digest_all чтобы разослать всем."
            )
            return

        text = DigestService.build_digest_for_trainer(user['id'])

        if not text:
            await message.answer(
                "📭 Нет данных для дайджеста (нет учеников или замеров)."
            )
            return

        await message.answer(text, parse_mode=ParseMode.HTML)

    except Exception as e:
        logger.error(f"Error in test_digest: {e}\n{traceback.format_exc()}")
        await message.answer(f"❌ Ошибка: {str(e)[:200]}")


@router.message(Command("test_digest_all"))
async def test_digest_all(message: Message):
    """Рассылает дайджест ВСЕМ тренерам прямо сейчас. Только для админа."""
    try:
        if not is_admin(message.from_user.id):
            await message.answer("❌ Только для админов.")
            return

        from app.services.digest_service import DigestService

        await message.answer("⏳ Рассылаю дайджесты всем тренерам...")

        await DigestService.send_digests_to_all_trainers(message.bot)

        await message.answer("✅ Готово. Проверьте уведомления.")

    except Exception as e:
        logger.error(f"Error in test_digest_all: {e}\n{traceback.format_exc()}")
        await message.answer(f"❌ Ошибка: {str(e)[:200]}")


# ============================================================
#  РАСШИРЕННАЯ АНАЛИТИКА
# ============================================================

@router.callback_query(F.data == "admin_analytics")
async def admin_analytics_callback(callback: CallbackQuery):
    """Расширенная аналитика."""
    try:
        if not is_admin(callback.from_user.id):
            await callback.answer("❌ Доступ запрещён.", show_alert=True)
            return

        from app.services.analytics_service import AnalyticsService

        stats = AnalyticsService.get_full_stats()

        if not stats:
            await callback.message.edit_text(
                "❌ Не удалось получить статистику.",
                reply_markup=get_admin_keyboard()
            )
            await callback.answer()
            return

        text = AnalyticsService.format_stats_for_telegram(stats)

        await callback.message.edit_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=get_admin_keyboard()
        )
        await callback.answer()

        logger.info(f"📈 Analytics viewed by {callback.from_user.id}")

    except Exception as e:
        logger.error(f"Error in admin_analytics_callback: {e}\n{traceback.format_exc()}")
        await callback.answer("❌ Ошибка", show_alert=True)


# ============================================================
#  КОМАНДА /analytics
# ============================================================

@router.message(Command("analytics"))
async def cmd_analytics(message: Message):
    """Аналитика по команде."""
    try:
        if not is_admin(message.from_user.id):
            await message.answer("❌ Доступ запрещён.")
            return

        from app.services.analytics_service import AnalyticsService

        stats = AnalyticsService.get_full_stats()

        if not stats:
            await message.answer("❌ Не удалось получить статистику.")
            return

        text = AnalyticsService.format_stats_for_telegram(stats)

        await message.answer(text, parse_mode=ParseMode.HTML)

        logger.info(f"📈 Analytics command by {message.from_user.id}")

    except Exception as e:
        logger.error(f"Error in cmd_analytics: {e}\n{traceback.format_exc()}")
        await message.answer("❌ Ошибка.")
