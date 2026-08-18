from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.enums import ParseMode
from datetime import datetime
from app.config import Config
from app.services.db_service import DatabaseService
from app.services.backup_service import BackupService
from app.models import UserRole
from app.keyboards.inline import get_cancel_keyboard, get_back_keyboard, get_admin_keyboard
from app.utils.logger import get_logger
import traceback

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


def get_broadcast_confirm_keyboard():
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    kb = [
        [
            InlineKeyboardButton(text="✅ Отправить", callback_data="broadcast_confirm"),
            InlineKeyboardButton(text="❌ Отмена", callback_data="broadcast_cancel")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)


# ============================================================
#  АДМИН-МЕНЮ
# ============================================================

@router.message(Command("admin"))
async def admin_panel(message: Message):
    try:
        if not is_admin(message.from_user.id):
            await message.answer("❌ Доступ запрещён.")
            return

        keyboard = get_admin_keyboard()

        await message.answer(
            "🔐 <b>Административная панель</b>\n\n"
            "Выберите действие:",
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard
        )

        logger.info(f"🔐 Admin panel opened by {message.from_user.id}")

    except Exception as e:
        logger.error(f"Error in admin_panel: {e}")
        await message.answer("❌ Ошибка при загрузке админ-панели.")


# ============================================================
#  СТАТИСТИКА
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

        await message.answer(
            response,
            parse_mode=ParseMode.HTML,
            reply_markup=get_back_keyboard()
        )

        logger.info(f"📊 Admin stats viewed by {message.from_user.id}")

    except Exception as e:
        logger.error(f"Error in admin_stats: {e}\n{traceback.format_exc()}")
        await message.answer("❌ Ошибка при загрузке статистики.")


@router.message(Command("admin_users"))
async def admin_users(message: Message):
    try:
        if not is_admin(message.from_user.id):
            await message.answer("❌ Доступ запрещён.")
            return

        users = db.get_all_users()

        if not users:
            await message.answer("📭 В системе нет пользователей.")
            return

        response = "👥 <b>Список всех пользователей</b>\n"
        response += f"━━━━━━━━━━━━━━━━━━━━━\n\n"

        trainers = [u for u in users if u.role == UserRole.TRAINER]
        clients = [u for u in users if u.role == UserRole.CLIENT]

        response += f"👨‍🏫 <b>Тренеры ({len(trainers)}):</b>\n"
        for trainer in trainers[:10]:
            response += f"  • {trainer.full_name or 'Без имени'} (@{trainer.username or 'no_username'})\n"
        if len(trainers) > 10:
            response += f"  ... и ещё {len(trainers) - 10} тренеров\n"

        response += f"\n👨‍🎓 <b>Ученики ({len(clients)}):</b>\n"
        for client in clients[:10]:
            response += f"  • {client.full_name or 'Без имени'} (@{client.username or 'no_username'})\n"
        if len(clients) > 10:
            response += f"  ... и ещё {len(clients) - 10} учеников\n"

        await message.answer(
            response,
            parse_mode=ParseMode.HTML,
            reply_markup=get_back_keyboard()
        )

    except Exception as e:
        logger.error(f"Error in admin_users: {e}")
        await message.answer("❌ Ошибка при загрузке списка пользователей.")


# ============================================================
#  УПРАВЛЕНИЕ ПОДПИСКАМИ
# ============================================================

@router.message(Command("set_trial"))
async def set_trial(message: Message):
    try:
        if not is_admin(message.from_user.id):
            await message.answer("❌ Доступ запрещён.")
            return

        args = message.text.split()
        if len(args) < 3:
            await message.answer(
                "❌ <b>Использование:</b> /set_trial @username 7 (дней)\n\n"
                "📌 <b>Пример:</b> /set_trial @john_doe 7",
                parse_mode=ParseMode.HTML
            )
            return

        username = args[1].lstrip('@')
        user = db.get_user_by_username(username)

        if not user:
            await message.answer(f"❌ Пользователь @{username} не найден.")
            return

        try:
            days = int(args[2])
            if days <= 0:
                await message.answer("❌ Количество дней должно быть больше 0.")
                return
        except ValueError:
            await message.answer("❌ Укажите количество дней числом.")
            return

        subscription = db.set_trial_subscription(user.id, days)

        if subscription:
            await message.answer(
                f"✅ <b>Пробный период выдан!</b>\n\n"
                f"👤 Пользователь: @{username}\n"
                f"📅 Дней: {days}\n"
                f"⏳ До: {subscription.expires_at.strftime('%d.%m.%Y')}",
                parse_mode=ParseMode.HTML,
                reply_markup=get_back_keyboard()
            )

            try:
                await message.bot.send_message(
                    chat_id=user.telegram_id,
                    text=(
                        f"🎉 <b>Поздравляем!</b>\n\n"
                        f"Вам выдан пробный период <b>Pro</b> на {days} дней!\n\n"
                        f"⏳ Действует до: {subscription.expires_at.strftime('%d.%m.%Y')}"
                    ),
                    parse_mode=ParseMode.HTML
                )
            except Exception as e:
                logger.warning(f"Could not notify user {user.id}: {e}")

            logger.info(f"✅ Trial subscription granted to {user.id} for {days} days by admin {message.from_user.id}")
        else:
            await message.answer("❌ Не удалось выдать пробный период.")

    except Exception as e:
        logger.error(f"Error in set_trial: {e}")
        await message.answer("❌ Ошибка при выдаче пробного периода.")


@router.message(Command("cancel_subscription"))
async def cancel_subscription(message: Message):
    try:
        if not is_admin(message.from_user.id):
            await message.answer("❌ Доступ запрещён.")
            return

        args = message.text.split()
        if len(args) < 2:
            await message.answer(
                "❌ <b>Использование:</b> /cancel_subscription @username",
                parse_mode=ParseMode.HTML
            )
            return

        username = args[1].lstrip('@')
        user = db.get_user_by_username(username)

        if not user:
            await message.answer(f"❌ Пользователь @{username} не найден.")
            return

        result = db.cancel_subscription(user.id)

        if result:
            await message.answer(
                f"✅ Подписка пользователя @{username} отключена.",
                reply_markup=get_back_keyboard()
            )

            try:
                await message.bot.send_message(
                    chat_id=user.telegram_id,
                    text="ℹ️ Ваша подписка <b>Pro</b> была отключена администратором.",
                    parse_mode=ParseMode.HTML
                )
            except Exception:
                pass

            logger.info(f"❌ Subscription cancelled for {user.id} by admin {message.from_user.id}")
        else:
            await message.answer(f"❌ У пользователя @{username} не было активной подписки.")

    except Exception as e:
        logger.error(f"Error in cancel_subscription: {e}")
        await message.answer("❌ Ошибка при отмене подписки.")


@router.message(Command("admin_subscriptions"))
async def admin_subscriptions(message: Message):
    try:
        if not is_admin(message.from_user.id):
            await message.answer("❌ Доступ запрещён.")
            return

        users = db.get_all_users()
        subscriptions = []

        for user in users:
            sub = db.get_user_subscription(user.id)
            if sub and sub.is_active:
                subscriptions.append({
                    'user': user,
                    'subscription': sub
                })

        if not subscriptions:
            await message.answer(
                "📭 Нет активных подписок.",
                reply_markup=get_back_keyboard()
            )
            return

        response = "💎 <b>Активные подписки</b>\n"
        response += f"━━━━━━━━━━━━━━━━━━━━━\n\n"

        for item in subscriptions[:20]:
            user = item['user']
            sub = item['subscription']
            status = "🟢 Активна" if sub.expires_at > datetime.now() else "🔴 Истекла"
            response += (
                f"• {user.full_name or user.username} "
                f"(@{user.username or 'no_username'})\n"
                f"  📅 До: {sub.expires_at.strftime('%d.%m.%Y')} {status}\n"
            )

        if len(subscriptions) > 20:
            response += f"\n... и ещё {len(subscriptions) - 20} подписок"

        await message.answer(
            response,
            parse_mode=ParseMode.HTML,
            reply_markup=get_back_keyboard()
        )

    except Exception as e:
        logger.error(f"Error in admin_subscriptions: {e}")
        await message.answer("❌ Ошибка при загрузке подписок.")


# ============================================================
#  РАССЫЛКА
# ============================================================

@router.message(Command("broadcast"))
async def start_broadcast(message: Message, state: FSMContext):
    try:
        if not is_admin(message.from_user.id):
            await message.answer("❌ Доступ запрещён.")
            return

        await message.answer(
            "📨 <b>Создание рассылки</b>\n\n"
            "Введите текст сообщения для рассылки всем пользователям:\n"
            "<i>(Можно использовать HTML-разметку)</i>",
            parse_mode=ParseMode.HTML,
            reply_markup=get_cancel_keyboard()
        )
        await state.set_state(BroadcastStates.entering_message)

    except Exception as e:
        logger.error(f"Error in start_broadcast: {e}")
        await message.answer("❌ Ошибка при начале рассылки.")


@router.message(StateFilter(BroadcastStates.entering_message))
async def process_broadcast_message(message: Message, state: FSMContext):
    try:
        if message.text == "❌ Отмена":
            await state.clear()
            await message.answer(
                "❌ Рассылка отменена.",
                reply_markup=get_back_keyboard()
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


@router.callback_query(StateFilter(BroadcastStates.confirming), F.data == "broadcast_confirm")
async def confirm_broadcast(callback: CallbackQuery, state: FSMContext):
    try:
        data = await state.get_data()
        text = data.get('broadcast_text')

        if not text:
            await callback.message.edit_text(
                "❌ Текст сообщения не найден.",
                reply_markup=get_back_keyboard()
            )
            await callback.answer()
            await state.clear()
            return

        users = db.get_all_users()
        total_users = len(users)

        if total_users == 0:
            await callback.message.edit_text(
                "❌ Нет пользователей для рассылки.",
                reply_markup=get_back_keyboard()
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
                    chat_id=user.telegram_id,
                    text=text,
                    parse_mode=ParseMode.HTML
                )
                sent_count += 1
            except Exception as e:
                failed_count += 1
                logger.warning(f"Broadcast failed for user {user.id}: {e}")

        db.broadcast_message(text, callback.from_user.id)

        await callback.message.edit_text(
            f"✅ <b>Рассылка завершена!</b>\n\n"
            f"✅ Отправлено: {sent_count}\n"
            f"❌ Не доставлено: {failed_count}\n"
            f"👥 Всего: {total_users}",
            parse_mode=ParseMode.HTML,
            reply_markup=get_back_keyboard()
        )

        logger.info(f"📨 Broadcast sent by admin {callback.from_user.id}: {sent_count} delivered, {failed_count} failed")
        await state.clear()
        await callback.answer()

    except Exception as e:
        logger.error(f"Error in confirm_broadcast: {e}")
        await callback.message.edit_text(
            "❌ Ошибка при отправке рассылки.",
            reply_markup=get_back_keyboard()
        )
        await callback.answer()
        await state.clear()


@router.callback_query(StateFilter(BroadcastStates.confirming), F.data == "broadcast_cancel")
async def cancel_broadcast(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "❌ Рассылка отменена.",
        reply_markup=get_back_keyboard()
    )
    await state.clear()
    await callback.answer()


# ============================================================
#  БЭКАП
# ============================================================

@router.message(Command("admin_backup"))
async def admin_backup(message: Message):
    try:
        if not is_admin(message.from_user.id):
            await message.answer("❌ Доступ запрещён.")
            return

        await message.answer("⏳ Создание бэкапа...")

        backup_path = await backup_service.backup_database(compress=True)

        if not backup_path:
            await message.answer("❌ Не удалось создать бэкап.")
            return

        await message.answer_document(
            document=FSInputFile(backup_path),
            caption=f"💾 <b>Бэкап базы данных</b>\n"
                    f"📅 {datetime.now().strftime('%d.%m.%Y %H:%M')}",
            parse_mode=ParseMode.HTML,
            reply_markup=get_back_keyboard()
        )

        logger.info(f"💾 Backup created by admin {message.from_user.id}: {backup_path}")

    except Exception as e:
        logger.error(f"Error in admin_backup: {e}")
        await message.answer("❌ Ошибка при создании бэкапа.")


# ============================================================
#  ЛОГИ
# ============================================================

@router.message(Command("admin_logs"))
async def admin_logs(message: Message):
    try:
        if not is_admin(message.from_user.id):
            await message.answer("❌ Доступ запрещён.")
            return

        from pathlib import Path

        log_path = Path(Config.LOG_FILE)
        if not log_path.exists():
            await message.answer("❌ Файл логов не найден.")
            return

        with open(log_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            last_lines = lines[-100:] if len(lines) > 100 else lines

        log_text = "".join(last_lines)

        if len(log_text) > 4000:
            await message.answer_document(
                document=FSInputFile(log_path),
                caption=f"📋 <b>Логи системы</b>\n"
                        f"📅 {datetime.now().strftime('%d.%m.%Y %H:%M')}",
                parse_mode=ParseMode.HTML,
                reply_markup=get_back_keyboard()
            )
        else:
            await message.answer(
                f"📋 <b>Последние логи:</b>\n\n"
                f"<code>{log_text}</code>",
                parse_mode=ParseMode.HTML,
                reply_markup=get_back_keyboard()
            )

        logger.info(f"📋 Logs viewed by admin {message.from_user.id}")

    except Exception as e:
        logger.error(f"Error in admin_logs: {e}")
        await message.answer("❌ Ошибка при загрузке логов.")
