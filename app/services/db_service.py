from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config import Config
from app.models import User, Measurement, TrainerClient, Reminder, ReminderLog, Broadcast, UserRole, Subscription
from datetime import datetime, timedelta
from app.utils.logger import get_logger
from contextlib import contextmanager

logger = get_logger(__name__)


class DatabaseService:
    """Сервис для работы с базой данных"""

    def __init__(self):
        connect_args = {}
        if Config.DATABASE_URL and Config.DATABASE_URL.startswith("sqlite"):
            connect_args = {"check_same_thread": False}

        self.engine = create_engine(
            Config.DATABASE_URL,
            connect_args=connect_args,
            pool_pre_ping=True,
            pool_recycle=3600,
            echo=Config.DEBUG if hasattr(Config, 'DEBUG') else False
        )
        self.Session = sessionmaker(bind=self.engine)
        logger.info("✅ DatabaseService initialized")

    @contextmanager
    def _get_session(self):
        """Контекстный менеджер для сессии с обработкой ошибок"""
        session = self.Session()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            session.close()

    # ====================== USER ======================

    def get_user(self, user_id: int):
        with self._get_session() as session:
            return session.query(User).filter(User.id == user_id).first()

    def get_user_by_telegram(self, telegram_id: int):
        with self._get_session() as session:
            return session.query(User).filter(User.telegram_id == telegram_id).first()

    def get_user_by_username(self, username: str):
        if not username:
            return None
        with self._get_session() as session:
            return session.query(User).filter(User.username == username).first()

def create_user(self, telegram_id, username, full_name, role, **kwargs):
    with self._get_session() as session:
        # Проверяем, существует ли пользователь с таким telegram_id
        existing_user = session.query(User).filter(User.telegram_id == telegram_id).first()
        
        if existing_user:
            # Обновляем существующего пользователя
            existing_user.username = username
            existing_user.full_name = full_name
            existing_user.role = role
            for key, value in kwargs.items():
                if hasattr(existing_user, key):
                    setattr(existing_user, key, value)
            session.flush()
            # ВАЖНО: Убираем session.refresh() и session.expunge()
            return existing_user
        
        # Создаём нового пользователя
        user = User(
            telegram_id=telegram_id,
            username=username,
            full_name=full_name,
            role=role,
            **kwargs
        )
        session.add(user)
        session.flush()
        # ВАЖНО: Убираем session.refresh() и session.expunge()
        return user

    def update_user(self, user_id: int, **kwargs):
        with self._get_session() as session:
            user = session.query(User).filter(User.id == user_id).first()
            if user:
                for key, value in kwargs.items():
                    if hasattr(user, key):
                        setattr(user, key, value)
                session.flush()
                session.refresh(user)
                return user
            return None

    def get_all_users(self):
        with self._get_session() as session:
            return session.query(User).all()

    def get_users_by_role(self, role: UserRole):
        with self._get_session() as session:
            return session.query(User).filter(
                User.role == role,
                User.is_active == True
            ).all()

    def get_users_by_ids(self, user_ids: list):
        if not user_ids:
            return []
        with self._get_session() as session:
            return session.query(User).filter(User.id.in_(user_ids)).all()

    # ====================== CLIENTS ======================

    def get_trainer_clients(self, trainer_id: int):
        with self._get_session() as session:
            return session.query(User).join(
                TrainerClient, User.id == TrainerClient.client_id
            ).filter(
                TrainerClient.trainer_id == trainer_id,
                TrainerClient.is_active == True,
                User.is_active == True
            ).all()

    def get_trainer_clients_full(self, trainer_id: int):
        with self._get_session() as session:
            return session.query(TrainerClient).filter(
                TrainerClient.trainer_id == trainer_id,
                TrainerClient.is_active == True
            ).all()

    def get_client_trainers(self, client_id: int):
        with self._get_session() as session:
            return session.query(User).join(
                TrainerClient, User.id == TrainerClient.trainer_id
            ).filter(
                TrainerClient.client_id == client_id,
                TrainerClient.is_active == True,
                User.is_active == True
            ).all()

    def add_client_to_trainer(self, trainer_id: int, client_id: int) -> bool:
        with self._get_session() as session:
            existing = session.query(TrainerClient).filter_by(
                trainer_id=trainer_id,
                client_id=client_id
            ).first()

            if existing:
                if not existing.is_active:
                    existing.is_active = True
                    session.flush()
                    return True
                return False

            tc = TrainerClient(trainer_id=trainer_id, client_id=client_id)
            session.add(tc)
            session.flush()
            return True

    def remove_client_from_trainer(self, trainer_id: int, client_id: int):
        with self._get_session() as session:
            session.query(TrainerClient).filter_by(
                trainer_id=trainer_id,
                client_id=client_id
            ).update({"is_active": False})

    def is_trainer_of_client(self, trainer_id: int, client_id: int) -> bool:
        with self._get_session() as session:
            return session.query(TrainerClient).filter(
                TrainerClient.trainer_id == trainer_id,
                TrainerClient.client_id == client_id,
                TrainerClient.is_active == True
            ).first() is not None

    # ====================== MEASUREMENTS ======================

    def create_measurement(self, user_id: int, data: dict):
        with self._get_session() as session:
            m = Measurement(user_id=user_id, **data)
            session.add(m)
            session.flush()
            session.refresh(m)
            return m

    def get_measurements(self, user_id: int, days: int = 30):
        cutoff = datetime.now() - timedelta(days=days)
        with self._get_session() as session:
            return session.query(Measurement).filter(
                Measurement.user_id == user_id,
                Measurement.measured_at >= cutoff
            ).order_by(Measurement.measured_at.asc()).all()

    def get_all_measurements(self, user_id: int, limit: int = None):
        with self._get_session() as session:
            query = session.query(Measurement).filter(
                Measurement.user_id == user_id
            ).order_by(Measurement.measured_at.desc())
            if limit:
                query = query.limit(limit)
            return query.all()

    def get_last_measurement(self, user_id: int):
        with self._get_session() as session:
            return session.query(Measurement).filter(
                Measurement.user_id == user_id
            ).order_by(Measurement.measured_at.desc()).first()

    def get_first_measurement(self, user_id: int):
        with self._get_session() as session:
            return session.query(Measurement).filter(
                Measurement.user_id == user_id
            ).order_by(Measurement.measured_at.asc()).first()

    def get_measurement_stats(self, user_id: int, days: int = 30):
        with self._get_session() as session:
            from sqlalchemy import func
            return session.query(
                func.min(Measurement.weight).label('min_weight'),
                func.max(Measurement.weight).label('max_weight'),
                func.avg(Measurement.weight).label('avg_weight'),
                func.count(Measurement.id).label('total')
            ).filter(
                Measurement.user_id == user_id,
                Measurement.measured_at >= datetime.now() - timedelta(days=days)
            ).first()

    # ====================== REMINDERS ======================

    def create_reminder(self, trainer_id: int, day_of_week: int, time_str: str):
        from datetime import time
        t = datetime.strptime(time_str, "%H:%M").time()
        with self._get_session() as session:
            reminder = Reminder(
                trainer_id=trainer_id,
                day_of_week=day_of_week,
                time=t,
                is_active=True
            )
            session.add(reminder)
            session.flush()
            session.refresh(reminder)
            return reminder

    def get_trainer_reminders(self, trainer_id: int):
        with self._get_session() as session:
            return session.query(Reminder).filter(
                Reminder.trainer_id == trainer_id,
                Reminder.is_active == True
            ).all()

    def get_reminder(self, reminder_id: int):
        with self._get_session() as session:
            return session.query(Reminder).filter(Reminder.id == reminder_id).first()

    def update_reminder(self, reminder_id: int, **kwargs):
        with self._get_session() as session:
            reminder = session.query(Reminder).filter(Reminder.id == reminder_id).first()
            if reminder:
                for key, value in kwargs.items():
                    if hasattr(reminder, key):
                        setattr(reminder, key, value)
                session.flush()
                session.refresh(reminder)
                return reminder
            return None

    def delete_reminder(self, reminder_id: int):
        with self._get_session() as session:
            session.query(Reminder).filter(Reminder.id == reminder_id).update({"is_active": False})

    def log_reminder(self, reminder_id: int, client_id: int, is_followup: bool = False):
        with self._get_session() as session:
            log = ReminderLog(
                reminder_id=reminder_id,
                client_id=client_id,
                is_followup=is_followup,
                is_acknowledged=False
            )
            session.add(log)
            session.flush()
            session.refresh(log)
            return log

    def get_reminder_logs(self, client_id: int, days: int = 30):
        cutoff = datetime.now() - timedelta(days=days)
        with self._get_session() as session:
            return session.query(ReminderLog).filter(
                ReminderLog.client_id == client_id,
                ReminderLog.sent_at >= cutoff
            ).all()

    # ====================== BROADCAST ======================

    def broadcast_message(self, message: str, sender_id: int):
        with self._get_session() as session:
            b = Broadcast(message=message, sent_by=sender_id, recipients_count=0)
            session.add(b)
            session.flush()
            session.refresh(b)
            return b.id

    def update_broadcast_count(self, broadcast_id: int, count: int):
        with self._get_session() as session:
            session.query(Broadcast).filter(Broadcast.id == broadcast_id).update(
                {"recipients_count": count}
            )

    def get_broadcasts(self, limit: int = 10):
        with self._get_session() as session:
            return session.query(Broadcast).order_by(
                Broadcast.sent_at.desc()
            ).limit(limit).all()

    # ====================== SUBSCRIPTIONS ======================

    def get_user_subscription(self, user_id: int):
        with self._get_session() as session:
            return session.query(Subscription).filter(
                Subscription.user_id == user_id,
                Subscription.is_active == True
            ).first()

    def set_trial_subscription(self, user_id: int, days: int = 7):
        with self._get_session() as session:
            old = session.query(Subscription).filter_by(user_id=user_id).first()
            if old:
                old.is_active = False

            expires_at = datetime.now() + timedelta(days=days)
            sub = Subscription(
                user_id=user_id,
                plan="pro",
                expires_at=expires_at,
                is_active=True
            )
            session.add(sub)
            session.flush()
            session.refresh(sub)
            return sub

    def set_subscription(self, user_id: int, plan: str, days: int = 30):
        with self._get_session() as session:
            old = session.query(Subscription).filter_by(user_id=user_id).first()
            if old:
                old.is_active = False

            expires_at = datetime.now() + timedelta(days=days)
            sub = Subscription(
                user_id=user_id,
                plan=plan,
                expires_at=expires_at,
                is_active=True
            )
            session.add(sub)
            session.flush()
            session.refresh(sub)
            return sub

    def cancel_subscription(self, user_id: int) -> bool:
        with self._get_session() as session:
            sub = session.query(Subscription).filter_by(user_id=user_id, is_active=True).first()
            if sub:
                sub.is_active = False
                session.flush()
                return True
            return False

    def is_subscription_active(self, user_id: int) -> bool:
        with self._get_session() as session:
            sub = session.query(Subscription).filter_by(user_id=user_id, is_active=True).first()
            if not sub:
                return False
            return sub.expires_at > datetime.now()

    def get_all_active_subscriptions(self) -> int:
        with self._get_session() as session:
            return session.query(Subscription).filter(
                Subscription.is_active == True,
                Subscription.expires_at > datetime.now()
            ).count()

    def get_expired_subscriptions(self):
        with self._get_session() as session:
            return session.query(Subscription).filter(
                Subscription.is_active == True,
                Subscription.expires_at <= datetime.now()
            ).all()

    # ====================== STATISTICS ======================

    def get_daily_measurements_count(self) -> int:
        today = datetime.now().date()
        with self._get_session() as session:
            return session.query(Measurement).filter(
                Measurement.measured_at >= today
            ).count()

    def get_daily_active_users(self) -> int:
        today = datetime.now().date()
        with self._get_session() as session:
            return session.query(User).filter(User.is_active == True).count()

    def get_stats(self):
        with self._get_session() as session:
            from sqlalchemy import func
            total_users = session.query(func.count(User.id)).scalar()
            active_users = session.query(func.count(User.id)).filter(User.is_active == True).scalar()
            total_trainers = session.query(func.count(User.id)).filter(User.role == UserRole.TRAINER).scalar()
            total_clients = session.query(func.count(User.id)).filter(User.role == UserRole.CLIENT).scalar()
            today_measurements = self.get_daily_measurements_count()
            active_subscriptions = self.get_all_active_subscriptions()

            return {
                'total_users': total_users or 0,
                'active_users': active_users or 0,
                'total_trainers': total_trainers or 0,
                'total_clients': total_clients or 0,
                'today_measurements': today_measurements,
                'active_subscriptions': active_subscriptions or 0
            }
