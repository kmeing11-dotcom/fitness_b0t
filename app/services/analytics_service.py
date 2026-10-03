# app/services/analytics_service.py
from datetime import datetime, timedelta
from app.db import Session
from app.models import User, UserRole, TrainerClient, Subscription
from app.utils.logger import get_logger
import traceback

logger = get_logger(__name__)


class AnalyticsService:

    @staticmethod
    def get_full_stats() -> dict:
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
                # Активные Pro-подписки
                active_subs = session.query(Subscription).filter(
                    Subscription.is_active == True,
                    Subscription.expires_at > now
                ).all()

                # Разделяем: триалы vs платные
                pro_paid = 0
                pro_trial = 0
                expiring_soon = []

                for s in active_subs:
                    is_trial = getattr(s, 'is_trial', False)

                    if is_trial:
                        pro_trial += 1
                    else:
                        pro_paid += 1

                    # Скоро закончатся (в течение 3 дней)
                    days_left = (s.expires_at - now).days
                    if 0 <= days_left <= 3:
                        u = session.query(User).filter(User.id == s.user_id).first()
                        if u:
                            expiring_soon.append({
                                'name': u.full_name or u.username or f"ID{u.id}",
                                'days': days_left,
                                'is_trial': is_trial
                            })

                free_count = trainers - pro_paid - pro_trial
                if free_count < 0:
                    free_count = 0

                # Конверсия Free → Pro (без триалов)
                conversion = 0.0
                if trainers > 0:
                    conversion = round((pro_paid / trainers) * 100, 1)

                # ==================== ВЫРУЧКА ====================
                # Только платные подписки (is_trial=False)
                paid_subs = session.query(Subscription).filter(
                    Subscription.is_trial == False
                ).all()

                revenue_total = 0
                revenue_30d = 0

                for s in paid_subs:
                    if not s.expires_at or not s.created_at:
                        continue

                    duration_days = (s.expires_at - s.created_at).days
                    price = 2990 if duration_days > 100 else 299

                    revenue_total += price

                    if s.created_at >= month_ago:
                        revenue_30d += price

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

                return {
                    'total_users': total_users,
                    'trainers': trainers,
                    'clients': clients,
                    'pro_paid': pro_paid,
                    'pro_trial': pro_trial,
                    'free_count': free_count,
                    'conversion': conversion,
                    'revenue_total': revenue_total,
                    'revenue_30d': revenue_30d,
                    'reg_7d': reg_7d,
                    'reg_30d': reg_30d,
                    'top_trainers': top_trainers,
                    'expiring_soon': expiring_soon
                }

        except Exception as e:
            logger.error(f"Error in get_full_stats: {e}\n{traceback.format_exc()}")
            return None

    @staticmethod
    def format_stats_for_telegram(stats: dict) -> str:
        if not stats:
            return "❌ Не удалось получить статистику."

        text = "📊 <b>Аналитика системы</b>\n"
        text += "━━━━━━━━━━━━━━━━━━━━━\n\n"

        text += f"👥 <b>Всего пользователей:</b> {stats['total_users']}\n"
        text += f"👨‍🏫 Тренеров: {stats['trainers']}\n"
        text += f"👨‍🎓 Учеников: {stats['clients']}\n"

        text += "\n💎 <b>Подписки:</b>\n"
        text += f"  • <b>Платных Pro:</b> {stats['pro_paid']}\n"
        text += f"  • На триале: {stats['pro_trial']}\n"
        text += f"  • Free: {stats['free_count']}\n"
        text += f"  • Конверсия Free→Pro: <b>{stats['conversion']}%</b>\n"

        text += "\n💰 <b>Выручка (только платные):</b>\n"
        text += f"  • Всего: {stats['revenue_total']} ⭐️\n"
        text += f"  • За 30 дней: {stats['revenue_30d']} ⭐️\n"

        text += "\n📅 <b>Регистрации:</b>\n"
        text += f"  • За 7 дней: {stats['reg_7d']}\n"
        text += f"  • За 30 дней: {stats['reg_30d']}\n"

        if stats['top_trainers']:
            text += "\n🔥 <b>Топ-5 тренеров:</b>\n"
            for i, t in enumerate(stats['top_trainers'], 1):
                text += f"  {i}. {t['name']} — {t['clients']} уч.\n"

        if stats['expiring_soon']:
            text += "\n⚠️ <b>Скоро закончится:</b>\n"
            for item in stats['expiring_soon'][:5]:
                tag = "🎁 триал" if item['is_trial'] else "💎 платный"
                text += f"  • {item['name']} ({tag}, через {item['days']} дн.)\n"

        text += "\n━━━━━━━━━━━━━━━━━━━━━\n"
        text += f"<i>Обновлено: {datetime.now().strftime('%d.%m.%Y %H:%M')}</i>"

        return text
