# app/services/subscription_service.py
from datetime import datetime
from functools import wraps
from typing import Optional, Callable

from aiogram.types import Message, CallbackQuery
from aiogram.enums import ParseMode

from app.services.db_service import DatabaseService
from app.utils.logger import get_logger

logger = get_logger(__name__)
db = DatabaseService()


# ============================================================
#  ЛИМИТЫ
# ============================================================

FREE_CLIENT_LIMIT = 3


# ============================================================
#  ПРОВЕРКИ ПОДПИСКИ
# ============================================================

def is_pro(user_id: int) -> bool:
    """Проверяет, активна ли Pro-подписка у пользователя."""
    try:
        sub = db.get_user_subscription(user_id)
        if not sub or not sub.get('is_active'):
            return False

        expires_at = sub.get('expires_at')
        if not expires_at:
            return False

        return expires_at > datetime.now()

    except Exception as e:
        logger.error(f"Error in is_pro: {e}")
        return False


def get_subscription_info(user_id: int) -> dict:
    """Возвращает инфо о подписке: план, дата истечения, дней осталось."""
    sub = db.get_user_subscription(user_id)

    if not sub or not sub.get('is_active'):
        return {
            'plan': 'free',
            'is_pro': False,
            'expires_at': None,
            'days_left': 0
        }

    expires_at = sub.get('expires_at')
    days_left = 0
    is_pro_active = False
    if expires_at and expires_at > datetime.now():
        days_left = (expires_at - datetime.now()).days
        is_pro_active = True

    return {
        'plan': sub.get('plan', 'free'),
        'is_pro': is_pro_active,
        'expires_at': expires_at,
        'days_left': days_left
    }


def days_until_expiry(user_id: int) -> int:
    """Сколько дней до конца подписки. -1 если нет подписки."""
    info = get_subscription_info(user_id)
    if not info['is_pro']:
        return -1
    return info['days_left']


def can_add_client(user_id: int) -> tuple:
    """Может ли добавить ученика. Возвращает (можно, причина)."""
    if is_pro(user_id):
        return True, ""

    try:
        clients = db.get_trainer_clients(user_id)
        if len(clients) >= FREE_CLIENT_LIMIT:
            return False, (
                f"❌ <b>Лимит Free-плана: {FREE_CLIENT_LIMIT} ученика</b>\n\n"
                f"У вас уже {len(clients)} учеников.\n\n"
                f"💎 Оформите Pro-подписку (/pro), чтобы:\n"
                f"• Добавлять безлимит учеников\n"
                f"• Делать PDF-отчёты\n"
                f"• Настраивать напоминания\n"
                f"• Смотреть полную статистику"
            )
        return True, ""
    except Exception as e:
        logger.error(f"Error in can_add_client: {e}")
        return True, ""


def can_use_reports(user_id: int) -> tuple:
    """Доступ к PDF-отчётам."""
    if is_pro(user_id):
        return True, ""
    return False, (
        f"❌ <b>PDF-отчёты доступны только на Pro</b>\n\n"
        f"💎 Оформите Pro-подписку (/pro) за 450 ₽/мес\n\n"
        f"<b>Что вы получите:</b>\n"
        f"• Безлимит учеников\n"
        f"• PDF-отчёты с графиками\n"
        f"• Автонапоминания\n"
        f"• Полная статистика"
    )


def can_use_reminders(user_id: int) -> tuple:
    """Доступ к напоминаниям."""
    if is_pro(user_id):
        return True, ""
    return False, (
        f"❌ <b>Напоминания доступны только на Pro</b>\n\n"
        f"💎 Оформите Pro-подписку (/pro) за 450 ₽/мес\n\n"
        f"<b>Что вы получите:</b>\n"
        f"• Автонапоминания ученикам\n"
        f"• Безлимит учеников\n"
        f"• PDF-отчёты\n"
        f"• Полная статистика"
    )


def can_use_stats(user_id: int) -> tuple:
    """Доступ к полной статистике."""
    return True, ""


# ============================================================
#  АКТИВАЦИЯ / ТРИАЛ
# ============================================================

def activate_pro(user_id: int, days: int = 30) -> bool:
    """Активирует Pro-подписку на N дней."""
    try:
        db.set_subscription(user_id=user_id, plan='pro', days=days)
        logger.info(f"✅ Pro activated for user {user_id} for {days} days")
        return True
    except Exception as e:
        logger.error(f"Error activating Pro: {e}")
        return False


def give_trial(user_id: int, days: int = 7) -> bool:
    """
    Даёт бесплатный триал Pro на N дней.
    Используется при регистрации тренера.
    НЕ даёт повторно, если уже есть активная подписка.
    """
    try:
        existing = db.get_user_subscription(user_id)
        if existing and existing.get('is_active'):
            logger.info(f"User {user_id} already has active subscription — no trial")
            return False

        db.set_subscription(user_id=user_id, plan='pro', days=days)
        logger.info(f"🎁 Trial {days} days given to user {user_id}")
        return True
    except Exception as e:
        logger.error(f"Error in give_trial: {e}")
        return False


# ============================================================
#  ДЕКОРАТОРЫ
# ============================================================

def pro_required(feature_name: str = "Эта функция"):
    """Декоратор: требует Pro-подписку."""
    def decorator(handler: Callable):
        @wraps(handler)
        async def wrapper(event, *args, **kwargs):
            user_id = None
            reply_func = None

            if isinstance(event, Message):
                user_id = event.from_user.id
                reply_func = event.answer
            elif isinstance(event, CallbackQuery):
                user_id = event.from_user.id
                reply_func = lambda text, **kw: event.message.answer(text, **kw)

            if not user_id:
                return

            user = db.get_user_by_telegram(user_id)
            if not user:
                await reply_func("❌ Вы не зарегистрированы. /start")
                return

            if user['role'] != 'trainer':
                return await handler(event, *args, **kwargs)

            if not is_pro(user['id']):
                text = (
                    f"❌ <b>{feature_name} доступна только на Pro</b>\n\n"
                    f"💎 Оформите Pro-подписку за 450 ₽/мес\n"
                    f"Команда: /pro"
                )
                await reply_func(text, parse_mode=ParseMode.HTML)
                if isinstance(event, CallbackQuery):
                    await event.answer()
                return

            return await handler(event, *args, **kwargs)

        return wrapper
    return decorator
