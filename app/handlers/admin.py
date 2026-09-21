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
        await message.answer("❌ Ошибка при загрузке админ-панели.")


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
            f"💎 <b>Активных подписок (Pro):</b> {active_subscriptions}\n"
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
#  СПИСОК ПОЛЬЗОВАТЕЛЕЙ
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

        response = "👥 <b>Список всех пользователей</b>\n"
        response += "━━━━━━━━━━━━━━━━━━━━━\n\n"

        response += f"👨‍🏫 <b>Тренеры ({len(trainers)}):</b>\n"
        for trainer in trainers[:10]:
            response += (
                f"  • {trainer['full_name'] or 'Без имени'} "
                f"(@{trainer['username'] or 'no_username'})\n"
            )
        if len(trainers) > 10:
            response += f"  ... и ещё {len(trainers) - 10} тренеров\n"

        response += f"\n👨‍🎓 <b>Ученики ({len(clients)}):</b>\n"
        for client in clients[:10]:
            response += (
                f"  • {client['full_name'] or 'Без имени'} "
                f"(@{client['username'] or 'no_username'})\n"
            )
        if len(clients) > 10:
            response += f"  ... и ещё {len(clients) - 10} учеников\n"

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
                subscriptions.append({
                    'user': user,
                    'subscription': sub
                })

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
            status = "🟢 Активна" if sub['expires_at'] > datetime.now() else "🔴 Истекла"
            response += (
                f"• {user['full_name'] or user['username']} "
                f"(@{user['username'] or 'no_username'})\n"
                f"  📅 До: {sub['expires_at'].strftime('%d.%m.%Y')} {status}\n"
            )

        if len(subscriptions) > 20:
            response += f"\n... и ещё {len(subscriptions) - 20} подписок"

        await callback.message.edit_text(
            response,
            parse_mode=ParseMode.HTML,
            reply_markup=get_admin_keyboard()
        )
        await callback.answer()

    except Exception as e:
        logger.error(f"Error in admin_subscriptions_callback: {e}\n{traceback.format_exc()}")
        await callback.answer("❌ Ошибка", show_alert=True)


# ============================================================
#  РАССЫЛКА — СТАРТ
# ============================================================

@router.callback_query(F.data == "admin_broadcast")
async def admin_broadcast_callback(callback: CallbackQuery, state: FSMContext):
    try:
        if not is_admin(callback.from_user.id):
            await callback.answer("❌ Доступ запрещён.", show_alert=True)
            return

        await callback.message.edit_text(
            "📨 <b>Создание рассылки</b>\n\n"
            "Введите текст сообщения для рассылки всем пользователям:\n"
            "<i>(Можно использовать HTML-разметку)</i>",
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
                "❌ Не удалось создать бэкап.\n\n"
                "<i>Для PostgreSQL файловый бэкап не поддерживается.</i>",
                parse_mode=ParseMode.HTML,
                reply_markup=get_admin_keyboard()
            )
            return

        await callback.message.delete()
        await callback.message.answer_document(
            document=FSInputFile(backup_path),
            caption=(
                f"💾 <b>Бэкап базы данных</b>\n"
                f"📅 {datetime.now().strftime('%d.%m.%Y %H:%M')}"
            ),
            parse_mode=ParseMode.HTML
        )

        logger.info(
            f"💾 Backup created by admin {callback.from_user.id}: {backup_path}"
        )

    except Exception as e:
        logger.error(f"Error in admin_backup_callback: {e}")
        try:
            await callback.message.edit_text(
                "❌ Ошибка при создании бэкапа.",
                reply_markup=get_admin_keyboard()
            )
        except Exception:
            pass
        await callback.answer()


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
                caption=(
                    f"📋 <b>Логи системы</b>\n"
                    f"📅 {datetime.now().strftime('%d.%m.%Y %H:%M')}"
                ),
                parse_mode=ParseMode.HTML
            )
        else:
            await callback.message.edit_text(
                f"📋 <b>Последние логи:</b>\n\n"
                f"<code>{log_text}</code>",
                parse_mode=ParseMode.HTML,
                reply_markup=get_admin_keyboard()
            )

        logger.info(f"📋 Logs viewed by admin {callback.from_user.id}")
        await callback.answer()

    except Exception as e:
        logger.error(f"Error in admin_logs_callback: {e}")
        try:
            await callback.message.edit_text(
                "❌ Ошибка при загрузке логов.",
                reply_markup=get_admin_keyboard()
            )
        except Exception:
            pass
        await callback.answer()


# ============================================================
#  РАССЫЛКА — FSM
# ============================================================

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
        total_users = len(users)

        await message.answer(
            f"📨 <b>Подтверждение рассылки</b>\n\n"
            f"Получателей: <b>{total_users}</b> пользователей\n\n"
            f"📝 <b>Текст сообщения:</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"{message.text}\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"<i>Отправить рассылку всем пользователям?</i>",
            parse_mode=ParseMode.HTML,
            reply_markup=get_broadcast_confirm_keyboard()
        )
        await state.set_state(BroadcastStates.confirming)

    except Exception as e:
        logger.error(f"Error in process_broadcast_message: {e}")
        await message.answer("❌ Ошибка при обработке текста.")


@router.callback_query(StateFilter(BroadcastStates.confirming),
                       F.data == "broadcast_confirm")
async def confirm_broadcast(callback: CallbackQuery, state: FSMContext):
    try:
        data = await state.get_data()
        text = data.get('broadcast_text')

        if not text:
            await callback.message.edit_text(
                "❌ Текст сообщения не найден.",
                reply_markup=get_admin_keyboard()
            )
            await callback.answer()
            await state.clear()
            return

        users = db.get_all_users()
        total_users = len(users)

        if total_users == 0:
            await callback.message.edit_text(
                "❌ Нет пользователей для рассылки.",
                reply_markup=get_admin_keyboard()
            )
            await callback.answer()
            await state.clear()
            return

        sent_count = 0
        failed_count = 0

        await callback.message.edit_text(
            "⏳ <b>Отправка рассылки...</b>\n"
            f"Всего: {total_users} пользователей",
            parse_mode=ParseMode.HTML
        )

        for user in users:
            try:
                await callback.bot.send_message(
                    chat_id=user['telegram_id'],
                    text=text,
                    parse_mode=ParseMode.HTML
                )
                sent_count += 1
            except Exception as e:
                failed_count += 1
                logger.warning(f"Broadcast failed for user {user['id']}: {e}")

        db.broadcast_message(text, callback.from_user.id)

        await callback.message.edit_text(
            f"✅ <b>Рассылка завершена!</b>\n\n"
            f"✅ Отправлено: {sent_count}\n"
            f"❌ Не доставлено: {failed_count}\n"
            f"👥 Всего: {total_users}",
            parse_mode=ParseMode.HTML,
            reply_markup=get_admin_keyboard()
        )

        logger.info(
            f"📨 Broadcast sent by admin {callback.from_user.id}: "
            f"{sent_count} delivered, {failed_count} failed"
        )
        await state.clear()
        await callback.answer()

    except Exception as e:
        logger.error(f"Error in confirm_broadcast: {e}\n{traceback.format_exc()}")
        try:
            await callback.message.edit_text(
                "❌ Ошибка при отправке рассылки.",
                reply_markup=get_admin_keyboard()
            )
        except Exception:
            pass
        await callback.answer()
        await state.clear()


@router.callback_query(StateFilter(BroadcastStates.confirming),
                       F.data == "broadcast_cancel")
async def cancel_broadcast(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "❌ Рассылка отменена.",
        reply_markup=get_admin_keyboard()
    )
    await state.clear()
    await callback.answer()


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
            f"👨‍🏫 <b>Тренеры:</b> {len(trainers)}\n"
            f"👨‍🎓 <b>Ученики:</b> {len(clients)}\n"
            f"👥 <b>Всего пользователей:</b> {len(all_users)}\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            f"💎 <b>Активных подписок (Pro):</b> {active_subscriptions}\n"
            f"📊 <b>Замеров сегодня:</b> {today_measurements}\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            f"📅 <b>Дата:</b> {datetime.now().strftime('%d.%m.%Y %H:%M')}"
        )

        await message.answer(response, parse_mode=ParseMode.HTML)

        logger.info(f"📊 Admin stats viewed by {message.from_user.id}")

    except Exception as e:
        logger.error(f"Error in admin_stats: {e}\n{traceback.format_exc()}")
        await message.answer("❌ Ошибка при загрузке статистики.")
