# app/services/analytics_service.py
from datetime import datetime, timedelta
from app.db import Session
from app.models import User, UserRole, TrainerClient, Measurement, Subscription
from app.utils.logger import get_logger
import traceback

logger = get_logger(__name__)


class AnalyticsService:
    """Расширенная аналитика для админа."""

    @staticmethod
    def get_full_stats() -> dict:
        """
        Возвращает полный срез по системе:
        - пользователи
        - подписки
        - выручка
        - регистрации
        - топ тренеров
        - требуют внимания
        """
        try:
            with Session() as session:
                now = datetime.now()
                week_ago = now - timedelta(days=7)
                month_ago = now - timedelta(days=30)

                # ==================== ПОЛЬЗОВАТЕЛИ ====================
                total_users = session.query(User).count()
                trainers = session.query(User).filter(
                    User.role == UserRole.TRAINER
                ).count()
                clients = session.query(User).filter(
                    User.role == UserRole.CLIENT
                ).count()

                # ==================== ПОДПИСКИ ====================
                pro_active = session.query(Subscription).filter(
                    Subscription.is_active == True,
                    Subscription.expires_at > now
                ).count()

                # Триалы = Pro-подписки, которые скоро закончатся И созданы < 8 дней назад
                # Проще: считаем Pro-подписки, у которых осталось <= 7 дней
                trial_like = session.query(Subscription).filter(
                    Subscription.is_active == True,
                    Subscription.expires_at > now,
                    Subscription.expires_at <= now + timedelta(days=7)
                ).count()

                free_count = trainers - pro_active
                if free_count < 0:
                    free_count = 0

                # Конверсия
                conversion = 0.0
                if trainers > 0:
                    conversion = round((pro_active / trainers) * 100, 1)

                # ==================== ВЫРУЧКА ====================
                # Считаем по подпискам: каждая месячная = 299 ⭐️, годовая = 2990 ⭐️
                # Приблизительная оценка
                # В реальности нужна таблица payments, но у нас её нет
                # Поэтому оцениваем: pro_active × средняя цена

                # Активные продления за последние 30 дней
                recent_subs = session.query(Subscription).filter(
                    Subscription.created_at >= month_ago
                ).all()

                revenue_30d = 0
                for s in recent_subs:
                    # Если expires_at - created_at > 100 дней — это годовой
                    if s.expires_at and s.created_at:
                        duration_days = (s.expires_at - s.created_at).days
                        if duration_days > 100:
                            revenue_30d += 2990
                        else:
                            revenue_30d += 299

                # Общая выручка (по всем подпискам за всё время)
                all_subs = session.query(Subscription).all()
                revenue_total = 0
                for s in all_subs:
                    if s.expires_at and s.created_at:
                        duration_days = (s.expires_at - s.created_at).days
                        if duration_days > 100:
                            revenue_total += 2990
                        else:
                            revenue_total += 299

                # ==================== РЕГИСТРАЦИИ ====================
                reg_7d = session.query(User).filter(
                    User.created_at >= week_ago
                ).count()

                reg_30d = session.query(User).filter(
                    User.created_at >= month_ago
                ).count()

                # ==================== ТОП ТРЕНЕРОВ ====================
                top_trainers = []
                trainer_rows = session.query(User).filter(
                    User.role == UserRole.TRAINER
                ).all()

                for t in trainer_rows:
                    count = session.query(TrainerClient).filter(
                        TrainerClient.trainer_id == t.id,
                        TrainerClient.is_active == True
                    ).count()

                    if count > 0:
                        top_trainers.append({
                            'name': t.full_name or t.username or f"ID{t.id}",
                            'clients': count
                        })

                top_trainers.sort(key=lambda x: x['clients'], reverse=True)
                top_trainers = top_trainers[:5]

                # ==================== ТРЕБУЮТ ВНИМАНИЯ ====================
                expiring_soon = []
                # Pro-подписки, которые закончатся в течение 3 дней
                expiring_subs = session.query(Subscription).filter(
                    Subscription.is_active == True,
                    Subscription.expires_at > now,
                    Subscription.expires_at <= now + timedelta(days=3)
                ).all()

                for s in expiring_subs:
                    u = session.query(User).filter(User.id == s.user_id).first()
                    if u:
                        days_left = (s.expires_at - now).days
                        expiring_soon.append({
                            'name': u.full_name or u.username or f"ID{u.id}",
                            'days': days_left
                        })

                # Тренеры без активности > 14 дней
                inactive_trainers = []
                # Простая эвристика: тренеры без новых замеров учеников за 14 дней
                # (в идеале надо last_seen, но его нет)

                # ==================== ИТОГ ====================
                return {
                    'total_users': total_users,
                    'trainers': trainers,
                    'clients': clients,
                    'pro_active': pro_active,
                    'trial_like': trial_like,
                    'free_count': free_count,
                    'conversion': conversion,
                    'revenue_total': revenue_total,
                    'revenue_30d': revenue_30d,
                    'reg_7d': reg_7d,
                    'reg_30d': reg_30d,
                    'top_trainers': top_trainers,
                    'expiring_soon': expiring_soon,
                    'inactive_trainers': inactive_trainers
                }

        except Exception as e:
            logger.error(f"Error in get_full_stats: {e}\n{traceback.format_exc()}")
            return None

    @staticmethod
    def format_stats_for_telegram(stats: dict) -> str:
        """Форматирует статистику для отправки в Telegram."""
        if not stats:
            return "❌ Не удалось получить статистику."

        text = "📊 <b>Аналитика системы</b>\n"
        text += "━━━━━━━━━━━━━━━━━━━━━\n\n"

        text += f"👥 <b>Всего пользователей:</b> {stats['total_users']}\n"
        text += f"👨‍🏫 Тренеров: {stats['trainers']}\n"
        text += f"👨‍🎓 Учеников: {stats['clients']}\n"

        text += "\n💎 <b>Подписки:</b>\n"
        text += f"  • Активных Pro: {stats['pro_active']}\n"
        text += f"  • Скоро закончатся: {stats['trial_like']}\n"
        text += f"  • Free: {stats['free_count']}\n"
        text += f"  • Конверсия Free→Pro: <b>{stats['conversion']}%</b>\n"

        text += "\n💰 <b>Выручка (оценка):</b>\n"
        text += f"  • Всего: {stats['revenue_total']} ⭐️\n"
        text += f"  • За 30 дней: {stats['revenue_30d']} ⭐️\n"

        text += "\n📅 <b>Регистрации:</b>\n"
        text += f"  • За 7 дней: {stats['reg_7d']}\n"
        text += f"  • За 30 дней: {stats['reg_30d']}\n"

        if stats['top_trainers']:
            text += "\n🔥 <b>Топ-5 тренеров по ученикам:</b>\n"
            for i, t in enumerate(stats['top_trainers'], 1):
                text += f"  {i}. {t['name']} — {t['clients']} уч.\n"

        if stats['expiring_soon']:
            text += "\n⚠️ <b>Скоро закончится Pro:</b>\n"
            for item in stats['expiring_soon'][:5]:
                text += f"  • {item['name']} (через {item['days']} дн.)\n"

        text += "\n━━━━━━━━━━━━━━━━━━━━━\n"
        text += f"<i>Обновлено: {datetime.now().strftime('%d.%m.%Y %H:%M')}</i>"

        return text
