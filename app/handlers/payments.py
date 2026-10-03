# app/handlers/payments.py
from aiogram import Router, F
from aiogram.types import (
    Message, CallbackQuery, PreCheckoutQuery, LabeledPrice,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.enums import ParseMode
from datetime import datetime, timedelta
import traceback

from app.services.db_service import DatabaseService
from app.services.subscription_service import (
    activate_pro, is_pro, get_subscription_info, FREE_CLIENT_LIMIT
)
from app.models import UserRole
from app.keyboards.inline import get_back_inline_keyboard
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = Router()
db = DatabaseService()


# ============================================================
#  НАСТРОЙКИ ТАРИФОВ
# ============================================================

PLANS = {
    "month": {
        "title": "Pro — 1 месяц",
        "price": 299,
        "days": 30,
        "label": "299 ⭐️ / месяц"
    },
    "year": {
        "title": "Pro — 1 год",
        "price": 2990,
        "days": 365,
        "label": "2990 ⭐️ / год (скидка 17%)"
    }
}


# ============================================================
#  /pro и кнопка "💎 Pro-подписка"
# ============================================================

@router.message(Command("pro"))
async def cmd_pro(message: Message):
    try:
        user = db.get_user_by_telegram(message.from_user.id)
        if not user:
            await message.answer("❌ Вы не зарегистрированы. /start")
            return

        if user['role'] != UserRole.TRAINER.value:
            await message.answer("❌ Pro-подписка доступна только тренерам.")
            return

        info = get_subscription_info(user['id'])

        # ============================================================
        #  ЕСЛИ PRO АКТИВНА — показываем статус + кнопку Продлить
        # ============================================================
        if info['is_pro']:
            sub = db.get_user_subscription(user['id'])

            kb = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text=f"🔄 Продлить на месяц — {PLANS['month']['price']} ⭐️",
                            callback_data="buy_plan_month"
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            text=f"🔄 Продлить на год — {PLANS['year']['price']} ⭐️",
                            callback_data="buy_plan_year"
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

            await message.answer(
                f"💎 <b>У вас активна Pro-подписка</b>\n\n"
                f"📅 Действует до: {sub['expires_at'].strftime('%d.%m.%Y')}\n"
                f"⏳ Осталось дней: {info['days_left']}\n\n"
                f"<b>Ваши возможности:</b>\n"
                f"✅ Безлимит учеников\n"
                f"✅ PDF-отчёты\n"
                f"✅ Напоминания\n"
                f"✅ Полная статистика\n\n"
                f"<i>Можете продлить подписку заранее — "
                f"дни добавятся к текущей дате.</i>",
                parse_mode=ParseMode.HTML,
                reply_markup=kb
            )
            return

        # ============================================================
        #  ЕСЛИ FREE — показываем тарифы
        # ============================================================
        clients_count = len(db.get_trainer_clients(user['id']))

        text = (
            f"💎 <b>Pro-подписка</b>\n\n"
            f"<b>Сейчас вы на Free-плане:</b>\n"
            f"• Учеников: {clients_count}/{FREE_CLIENT_LIMIT}\n"
            f"• PDF-отчёты: ❌ недоступны\n"
            f"• Напоминания: ❌ недоступны\n\n"
            f"<b>Что даёт Pro:</b>\n"
            f"✅ Неограниченное количество учеников\n"
            f"✅ PDF-отчёты с графиками\n"
            f"✅ Автоматические напоминания\n"
            f"✅ Полная статистика\n\n"
            f"<b>Выберите тариф:</b>"
        )

        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=f"📅 Месяц — {PLANS['month']['price']} ⭐️",
                        callback_data="buy_plan_month"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text=f"📅 Год — {PLANS['year']['price']} ⭐️ (выгоднее)",
                        callback_data="buy_plan_year"
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
#  ВЫБОР ТАРИФА → ИНВОЙС
# ============================================================

@router.callback_query(F.data.startswith("buy_plan_"))
async def buy_plan(callback: CallbackQuery):
    try:
        plan_key = callback.data.replace("buy_plan_", "")
        plan = PLANS.get(plan_key)

        if not plan:
            await callback.answer("❌ Неверный тариф", show_alert=True)
            return

        user = db.get_user_by_telegram(callback.from_user.id)
        if not user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return

        if user['role'] != UserRole.TRAINER.value:
            await callback.answer("❌ Только для тренеров", show_alert=True)
            return

        # Определяем тип: первая покупка или продление
        is_renewal = is_pro(user['id'])
        action = "Продление" if is_renewal else "Оформление"

        await callback.bot.send_invoice(
            chat_id=callback.from_user.id,
            title=f"{action}: {plan['title']}",
            description=(
                f"Pro-подписка на {plan['days']} дней.\n"
                f"Безлимит учеников, PDF-отчёты, напоминания."
            ),
            payload=f"pro_{plan_key}_{user['id']}_{int(datetime.now().timestamp())}",
            currency="XTR",
            prices=[
                LabeledPrice(
                    label=plan['title'],
                    amount=plan['price']
                )
            ],
            provider_token=""
        )

        await callback.answer()

    except Exception as e:
        logger.error(f"Error in buy_plan: {e}\n{traceback.format_exc()}")
        await callback.answer("❌ Ошибка при создании счёта", show_alert=True)


# ============================================================
#  PRE_CHECKOUT
# ============================================================

@router.pre_checkout_query()
async def process_pre_checkout(pre_checkout_q: PreCheckoutQuery):
    try:
        if pre_checkout_q.invoice_payload.startswith("pro_"):
            await pre_checkout_q.answer(ok=True)
        else:
            await pre_checkout_q.answer(ok=False, error_message="Неверный товар")
    except Exception as e:
        logger.error(f"Error in pre_checkout: {e}")
        await pre_checkout_q.answer(ok=False, error_message="Ошибка")


# ============================================================
#  SUCCESSFUL_PAYMENT → АКТИВАЦИЯ / ПРОДЛЕНИЕ
# ============================================================

@router.message(F.successful_payment)
async def process_successful_payment(message: Message):
    try:
        payment = message.successful_payment
        payload = payment.invoice_payload
        charge_id = payment.telegram_payment_charge_id
        amount = payment.total_amount

        logger.info(
            f"💰 Payment: payload={payload}, "
            f"charge_id={charge_id}, amount={amount} ⭐️"
        )

        # payload: pro_{plan_key}_{user_id}_{timestamp}
        parts = payload.split("_")
        if len(parts) < 4 or parts[0] != "pro":
            logger.warning(f"Unknown payload: {payload}")
            await message.answer("❌ Ошибка: неизвестный товар.")
            return

        plan_key = parts[1]
        user_id = int(parts[2])

        plan = PLANS.get(plan_key)
        if not plan:
            logger.warning(f"Unknown plan: {plan_key}")
            await message.answer("❌ Ошибка: неизвестный тариф.")
            return

        # ПРОВЕРЯЕМ: продление или новая подписка
        was_pro = is_pro(user_id)

        if was_pro:
            # ПРОДЛЕНИЕ: добавляем дни к текущей дате
            sub_before = db.get_user_subscription(user_id)
            current_expires = sub_before['expires_at']
            new_expires = current_expires + timedelta(days=plan['days'])

            # Обновляем через db_service
            # Используем set_subscription с новым количеством дней
            # Но set_subscription создаёт новую запись с now + days
            # Поэтому считаем дни от now до new_expires
            total_days = (new_expires - datetime.now()).days
            db.set_subscription(user_id=user_id, plan='pro', days=total_days)

            action = "продлена"
            extra_info = (
                f"📅 Было до: {current_expires.strftime('%d.%m.%Y')}\n"
                f"📅 Стало до: {new_expires.strftime('%d.%m.%Y')}\n"
            )
        else:
            # НОВАЯ ПОДПИСКА
            activate_pro(user_id=user_id, days=plan['days'])
            action = "активирована"
            extra_info = ""

        sub = db.get_user_subscription(user_id)

        await message.answer(
            f"✅ <b>Оплата получена!</b>\n\n"
            f"💎 Pro-подписка {action}\n"
            f"📅 Тариф: {plan['title']}\n"
            f"{extra_info}"
            f"📅 Действует до: {sub['expires_at'].strftime('%d.%m.%Y')}\n"
            f"💰 Оплачено: {amount} ⭐️\n\n"
            f"<b>Вам доступно:</b>\n"
            f"✅ Безлимит учеников\n"
            f"✅ PDF-отчёты\n"
            f"✅ Автонапоминания\n"
            f"✅ Полная статистика\n\n"
            f"Спасибо! 🚀",
            parse_mode=ParseMode.HTML,
            reply_markup=get_back_inline_keyboard("back_to_menu")
        )

        logger.info(
            f"✅ Pro {action}: user={user_id}, "
            f"plan={plan_key}, days={plan['days']}"
        )

    except Exception as e:
        logger.error(f"Error in successful_payment: {e}\n{traceback.format_exc()}")
        await message.answer("❌ Ошибка при активации подписки.")


# ============================================================
#  АДМИН: /give_pro
# ============================================================

@router.message(Command("give_pro"))
async def give_pro(message: Message):
    try:
        from app.config import Config
        if message.from_user.id not in Config.get_admin_ids():
            await message.answer("❌ Только для админов.")
            return

        args = message.text.split()
        if len(args) < 2:
            await message.answer("Использование: /give_pro @username [дни]")
            return

        username = args[1].lstrip('@')
        days = int(args[2]) if len(args) >= 3 else 30

        user = db.get_user_by_username(username)
        if not user:
            await message.answer(f"❌ @{username} не найден.")
            return

        activate_pro(user['id'], days=days)

        await message.answer(f"✅ Pro активирован для @{username} на {days} дней.")

        try:
            await message.bot.send_message(
                chat_id=user['telegram_id'],
                text=(
                    f"🎁 <b>Вам активирован Pro-доступ на {days} дней!</b>\n\n"
                    f"Проверить: /pro"
                ),
                parse_mode=ParseMode.HTML
            )
        except Exception:
            pass

    except Exception as e:
        logger.error(f"Error in give_pro: {e}")
        await message.answer("❌ Ошибка.")
