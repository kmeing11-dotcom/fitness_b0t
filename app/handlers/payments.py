# app/handlers/payments.py
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, PreCheckoutQuery, LabeledPrice
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.enums import ParseMode
from datetime import datetime, timedelta
import traceback

from app.services.db_service import DatabaseService
from app.models import UserRole
from app.keyboards.inline import get_back_inline_keyboard
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = Router()
db = DatabaseService()

# ============================================================
#  НАСТРОЙКИ ПОДПИСКИ
# ============================================================
PRO_PRICE_STARS = 100  # 100 Stars в месяц
PRO_DURATION_DAYS = 30
FREE_CLIENT_LIMIT = 3  # Бесплатно — до 3 учеников


class PaymentStates(StatesGroup):
    confirming = State()


# ============================================================
#  МЕНЮ ПОДПИСКИ
# ============================================================

@router.message(Command("pro"))
async def cmd_pro(message: Message):
    """Показать информацию о Pro-подписке."""
    try:
        user = db.get_user_by_telegram(message.from_user.id)
        if not user:
            await message.answer("❌ Вы не зарегистрированы. Используйте /start.")
            return

        # Проверяем текущий статус
        sub = db.get_user_subscription(user['id'])
        is_pro = sub and sub['is_active'] and sub['expires_at'] > datetime.now()

        if is_pro:
            await message.answer(
                f"💎 <b>У вас активна Pro-подписка</b>\n\n"
                f"📅 Действует до: {sub['expires_at'].strftime('%d.%m.%Y')}\n"
                f"👥 Учеников без лимита\n"
                f"📄 PDF-отчёты, напоминания, статистика\n\n"
                f"<i>Подписка продлевается автоматически каждый месяц.</i>",
                parse_mode=ParseMode.HTML,
                reply_markup=get_back_inline_keyboard("back_to_menu")
            )
            return

        # Не Pro — показываем тариф
        text = (
            f"💎 <b>Pro-подписка</b>\n\n"
            f"<b>Что даёт:</b>\n"
            f"👥 Неограниченное количество учеников\n"
            f"📄 PDF-отчёты для клиентов\n"
            f"⏰ Автоматические напоминания\n"
            f"📊 Расширенная статистика и графики\n\n"
            f"<b>Цена:</b> {PRO_PRICE_STARS} ⭐️ в месяц\n\n"
            f"<i>Оплата через Telegram Stars."
            f"По окончании подписки бот напомнит вам о продлении.</i>"
        )

        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=f"💎 Оформить за {PRO_PRICE_STARS} ⭐️",
                        callback_data="buy_pro"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🔙 Назад",
                        callback_data="back_to_menu"
                    )
                ]
            ]
        )

        await message.answer(text, parse_mode=ParseMode.HTML, reply_markup=kb)

    except Exception as e:
        logger.error(f"Error in cmd_pro: {e}\n{traceback.format_exc()}")
        await message.answer("❌ Ошибка.")


# ============================================================
#  ОТПРАВКА ИНВОЙСА (Telegram Stars)
# ============================================================

@router.callback_query(F.data == "buy_pro")
async def buy_pro(callback: CallbackQuery):
    """Отправляем инвойс на оплату через Telegram Stars."""
    try:
        user = db.get_user_by_telegram(callback.from_user.id)
        if not user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return

        if user['role'] != UserRole.TRAINER.value:
            await callback.answer("❌ Pro-подписка доступна только тренерам", show_alert=True)
            return

        # Отправляем инвойс через Telegram Stars
        # currency="XTR", prices — один LabeledPrice
        await callback.bot.send_invoice(
            chat_id=callback.from_user.id,
            title="Pro-подписка",
            description=(
                f"Безлимитные ученики, PDF-отчёты, "
                f"напоминания и статистика на {PRO_DURATION_DAYS} дней."
            ),
            payload=f"pro_sub_{user['id']}_{int(datetime.now().timestamp())}",
            currency="XTR",  # Telegram Stars [citation:3][citation:9]
            prices=[
                LabeledPrice(label="Pro-подписка (1 месяц)", amount=PRO_PRICE_STARS)
            ],
            provider_token=""  # Пустая строка для Stars [citation:3]
        )

        await callback.answer()

    except Exception as e:
        logger.error(f"Error in buy_pro: {e}\n{traceback.format_exc()}")
        await callback.answer("❌ Ошибка при создании счёта", show_alert=True)


# ============================================================
#  PRE_CHECKOUT (обязательное подтверждение)
# ============================================================

@router.pre_checkout_query()
async def process_pre_checkout(pre_checkout_q: PreCheckoutQuery):
    """
    Telegram требует подтвердить pre_checkout перед оплатой.
    Всегда отвечаем OK, если payload валидный.
    """
    try:
        # Проверяем, что payload начинается с pro_sub_
        if pre_checkout_q.invoice_payload.startswith("pro_sub_"):
            await pre_checkout_q.answer(ok=True)
        else:
            await pre_checkout_q.answer(ok=False, error_message="Неверный товар")

    except Exception as e:
        logger.error(f"Error in process_pre_checkout: {e}")
        await pre_checkout_q.answer(ok=False, error_message="Ошибка")


# ============================================================
#  SUCCESSFUL_PAYMENT (активация подписки)
# ============================================================

@router.message(F.successful_payment)
async def process_successful_payment(message: Message):
    """Активируем Pro-подписку после успешной оплаты."""
    try:
        payment = message.successful_payment
        payload = payment.invoice_payload
        telegram_payment_charge_id = payment.telegram_payment_charge_id

        logger.info(
            f"💰 Successful payment: payload={payload}, "
            f"charge_id={telegram_payment_charge_id}, "
            f"amount={payment.total_amount} Stars"
        )

        # Парсим payload: pro_sub_{user_id}_{timestamp}
        parts = payload.split("_")
        if len(parts) < 3 or parts[0] != "pro" or parts[1] != "sub":
            logger.warning(f"Unknown payload: {payload}")
            return

        user_id = int(parts[2])

        # Активируем подписку
        db.set_subscription(
            user_id=user_id,
            plan="pro",
            days=PRO_DURATION_DAYS
        )

        sub = db.get_user_subscription(user_id)

        await message.answer(
            f"✅ <b>Оплата получена!</b>\n\n"
            f"💎 Pro-подписка активирована\n"
            f"📅 Действует до: {sub['expires_at'].strftime('%d.%m.%Y')}\n\n"
            f"Теперь вы можете:\n"
            f"• Добавлять неограниченное количество учеников\n"
            f"• Создавать PDF-отчёты\n"
            f"• Настраивать напоминания\n"
            f"• Смотреть расширенную статистику\n\n"
            f"<i>Подписка будет продлена автоматически.</i>",
            parse_mode=ParseMode.HTML,
            reply_markup=get_back_inline_keyboard("back_to_menu")
        )

        logger.info(f"✅ Pro subscription activated for user {user_id}")

    except Exception as e:
        logger.error(f"Error in process_successful_payment: {e}\n{traceback.format_exc()}")
        await message.answer("❌ Ошибка при активации подписки.")


# ============================================================
#  ПРОВЕРКА ЛИМИТА ДЛЯ FREE-ПЛАНА
# ============================================================

def can_add_client(trainer_id: int) -> tuple[bool, str]:
    """
    Проверяет, может ли тренер добавить ещё ученика.
    Возвращает (можно_ли, причина_если_нет).
    """
    sub = db.get_user_subscription(trainer_id)
    is_pro = sub and sub['is_active'] and sub['expires_at'] > datetime.now()

    if is_pro:
        return True, ""

    # Free-план — проверяем лимит
    clients = db.get_trainer_clients(trainer_id)
    if len(clients) >= FREE_CLIENT_LIMIT:
        return False, (
            f"❌ <b>Достигнут лимит бесплатных учеников ({FREE_CLIENT_LIMIT})</b>\n\n"
            f"Оформите Pro-подписку (/pro), чтобы добавлять "
            f"неограниченное количество учеников."
        )

    return True, ""
