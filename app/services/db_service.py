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
            user = session.query(User).filter(User.id == user_id).first()
            if user:
                return {
                    'id': user.id,
                    'telegram_id': user.telegram_id,
                    'username': user.username,
                    'full_name': user.full_name,
                    'role': user.role.value if user.role else None,
                    'phone': user.phone,
                    'studio_name': user.studio_name,
                    'age': user.age,
                    'height': user.height,
                    'goal': user.goal,
                    'created_at': user.created_at,
                    'is_active': user.is_active
                }
            return None

  def get_user_by_telegram(self, telegram_id: int):
    logger.info(f"🔍 [get_user_by_telegram] searching for {telegram_id}")
    with self._get_session() as session:
        user = session.query(User).filter(User.telegram_id == telegram_id).first()
        if user:
            logger.info(f"🔍 [get_user_by_telegram] found user: id={user.id}, role={user.role}, role.value={user.role.value if user.role else None}")
            return {
                'id': user.id,
                'telegram_id': user.telegram_id,
                'username': user.username,
                'full_name': user.full_name,
                'role': user.role.value if user.role else None,
                'phone': user.phone,
                'studio_name': user.studio_name,
                'age': user.age,
                'height': user.height,
                'goal': user.goal,
                'created_at': user.created_at,
                'is_active': user.is_active
            }
        logger.info(f"🔍 [get_user_by_telegram] user not found")
        return None

    def get_user_by_username(self, username: str):
        if not username:
            return None
        with self._get_session() as session:
            user = session.query(User).filter(User.username == username).first()
            if user:
                return {
                    'id': user.id,
                    'telegram_id': user.telegram_id,
                    'username': user.username,
                    'full_name': user.full_name,
                    'role': user.role.value if user.role else None,
                    'phone': user.phone,
                    'studio_name': user.studio_name,
                    'age': user.age,
                    'height': user.height,
                    'goal': user.goal,
                    'created_at': user.created_at,
                    'is_active': user.is_active
                }
            return None

    def create_user(self, telegram_id, username, full_name, role, **kwargs):
        """Создаёт нового пользователя и возвращает словарь с данными"""
        with self._get_session() as session:
            # Проверяем, существует ли пользователь
            existing_user = session.query(User).filter(User.telegram_id == telegram_id).first()
            
            if existing_user:
                existing_user.username = username
                existing_user.full_name = full_name
                existing_user.role = role
                for key, value in kwargs.items():
                    if hasattr(existing_user, key):
                        setattr(existing_user, key, value)
                session.flush()
                logger.info(f"✅ User updated: {existing_user.telegram_id}")
                return {
                    'id': existing_user.id,
                    'telegram_id': existing_user.telegram_id,
                    'username': existing_user.username,
                    'full_name': existing_user.full_name,
                    'role': existing_user.role.value if existing_user.role else None,
                    'phone': existing_user.phone,
                    'studio_name': existing_user.studio_name,
                    'age': existing_user.age,
                    'height': existing_user.height,
                    'goal': existing_user.goal,
                    'created_at': existing_user.created_at,
                    'is_active': existing_user.is_active
                }
            
            user = User(
                telegram_id=telegram_id,
                username=username,
                full_name=full_name,
                role=role,
                **kwargs
            )
            session.add(user)
            session.flush()
            logger.info(f"✅ User created: {user.telegram_id}")
            return {
                'id': user.id,
                'telegram_id': user.telegram_id,
                'username': user.username,
                'full_name': user.full_name,
                'role': user.role.value if user.role else None,
                'phone': user.phone,
                'studio_name': user.studio_name,
                'age': user.age,
                'height': user.height,
                'goal': user.goal,
                'created_at': user.created_at,
                'is_active': user.is_active
            }

    def update_user(self, user_id: int, **kwargs):
        with self._get_session() as session:
            user = session.query(User).filter(User.id == user_id).first()
            if user:
                for key, value in kwargs.items():
                    if hasattr(user, key):
                        setattr(user, key, value)
                session.flush()
                return {
                    'id': user.id,
                    'telegram_id': user.telegram_id,
                    'username': user.username,
                    'full_name': user.full_name,
                    'role': user.role.value if user.role else None,
                    'phone': user.phone,
                    'studio_name': user.studio_name,
                    'age': user.age,
                    'height': user.height,
                    'goal': user.goal,
                    'created_at': user.created_at,
                    'is_active': user.is_active
                }
            return None

    def get_all_users(self):
        with self._get_session() as session:
            users = session.query(User).all()
            result = []
            for user in users:
                result.append({
                    'id': user.id,
                    'telegram_id': user.telegram_id,
                    'username': user.username,
                    'full_name': user.full_name,
                    'role': user.role.value if user.role else None,
                    'phone': user.phone,
                    'studio_name': user.studio_name,
                    'age': user.age,
                    'height': user.height,
                    'goal': user.goal,
                    'created_at': user.created_at,
                    'is_active': user.is_active
                })
            return result

    def get_users_by_role(self, role: UserRole):
        with self._get_session() as session:
            users = session.query(User).filter(
                User.role == role,
                User.is_active == True
            ).all()
            result = []
            for user in users:
                result.append({
                    'id': user.id,
                    'telegram_id': user.telegram_id,
                    'username': user.username,
                    'full_name': user.full_name,
                    'role': user.role.value if user.role else None,
                    'phone': user.phone,
                    'studio_name': user.studio_name,
                    'age': user.age,
                    'height': user.height,
                    'goal': user.goal,
                    'created_at': user.created_at,
                    'is_active': user.is_active
                })
            return result

    def get_users_by_ids(self, user_ids: list):
        if not user_ids:
            return []
        with self._get_session() as session:
            users = session.query(User).filter(User.id.in_(user_ids)).all()
            result = []
            for user in users:
                result.append({
                    'id': user.id,
                    'telegram_id': user.telegram_id,
                    'username': user.username,
                    'full_name': user.full_name,
                    'role': user.role.value if user.role else None,
                    'phone': user.phone,
                    'studio_name': user.studio_name,
                    'age': user.age,
                    'height': user.height,
                    'goal': user.goal,
                    'created_at': user.created_at,
                    'is_active': user.is_active
                })
            return result

    # ====================== CLIENTS ======================

    def get_trainer_clients(self, trainer_id: int):
        with self._get_session() as session:
            users = session.query(User).join(
                TrainerClient, User.id == TrainerClient.client_id
            ).filter(
                TrainerClient.trainer_id == trainer_id,
                TrainerClient.is_active == True,
                User.is_active == True
            ).all()
            result = []
            for user in users:
                result.append({
                    'id': user.id,
                    'telegram_id': user.telegram_id,
                    'username': user.username,
                    'full_name': user.full_name,
                    'role': user.role.value if user.role else None,
                    'phone': user.phone,
                    'studio_name': user.studio_name,
                    'age': user.age,
                    'height': user.height,
                    'goal': user.goal,
                    'created_at': user.created_at,
                    'is_active': user.is_active
                })
            return result

    def get_trainer_clients_full(self, trainer_id: int):
        with self._get_session() as session:
            clients = session.query(TrainerClient).filter(
                TrainerClient.trainer_id == trainer_id,
                TrainerClient.is_active == True
            ).all()
            result = []
            for client in clients:
                result.append({
                    'id': client.id,
                    'trainer_id': client.trainer_id,
                    'client_id': client.client_id,
                    'created_at': client.created_at,
                    'is_active': client.is_active
                })
            return result

    def get_client_trainers(self, client_id: int):
        with self._get_session() as session:
            users = session.query(User).join(
                TrainerClient, User.id == TrainerClient.trainer_id
            ).filter(
                TrainerClient.client_id == client_id,
                TrainerClient.is_active == True,
                User.is_active == True
            ).all()
            result = []
            for user in users:
                result.append({
                    'id': user.id,
                    'telegram_id': user.telegram_id,
                    'username': user.username,
                    'full_name': user.full_name,
                    'role': user.role.value if user.role else None,
                    'phone': user.phone,
                    'studio_name': user.studio_name,
                    'age': user.age,
                    'height': user.height,
                    'goal': user.goal,
                    'created_at': user.created_at,
                    'is_active': user.is_active
                })
            return result

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
            return {
                'id': m.id,
                'user_id': m.user_id,
                'weight': m.weight,
                'waist': m.waist,
                'hips': m.hips,
                'chest': m.chest,
                'biceps': m.biceps,
                'measured_at': m.measured_at,
                'notes': m.notes
            }

    def get_measurements(self, user_id: int, days: int = 30):
        cutoff = datetime.now() - timedelta(days=days)
        with self._get_session() as session:
            measurements = session.query(Measurement).filter(
                Measurement.user_id == user_id,
                Measurement.measured_at >= cutoff
            ).order_by(Measurement.measured_at.asc()).all()
            result = []
            for m in measurements:
                result.append({
                    'id': m.id,
                    'user_id': m.user_id,
                    'weight': m.weight,
                    'waist': m.waist,
                    'hips': m.hips,
                    'chest': m.chest,
                    'biceps': m.biceps,
                    'measured_at': m.measured_at,
                    'notes': m.notes
                })
            return result

    def get_all_measurements(self, user_id: int, limit: int = None):
        with self._get_session() as session:
            query = session.query(Measurement).filter(
                Measurement.user_id == user_id
            ).order_by(Measurement.measured_at.desc())
            if limit:
                query = query.limit(limit)
            measurements = query.all()
            result = []
            for m in measurements:
                result.append({
                    'id': m.id,
                    'user_id': m.user_id,
                    'weight': m.weight,
                    'waist': m.waist,
                    'hips': m.hips,
                    'chest': m.chest,
                    'biceps': m.biceps,
                    'measured_at': m.measured_at,
                    'notes': m.notes
                })
            return result

    def get_last_measurement(self, user_id: int):
        with self._get_session() as session:
            m = session.query(Measurement).filter(
                Measurement.user_id == user_id
            ).order_by(Measurement.measured_at.desc()).first()
            if m:
                return {
                    'id': m.id,
                    'user_id': m.user_id,
                    'weight': m.weight,
                    'waist': m.waist,
                    'hips': m.hips,
                    'chest': m.chest,
                    'biceps': m.biceps,
                    'measured_at': m.measured_at,
                    'notes': m.notes
                }
            return None

    def get_first_measurement(self, user_id: int):
        with self._get_session() as session:
            m = session.query(Measurement).filter(
                Measurement.user_id == user_id
            ).order_by(Measurement.measured_at.asc()).first()
            if m:
                return {
                    'id': m.id,
                    'user_id': m.user_id,
                    'weight': m.weight,
                    'waist': m.waist,
                    'hips': m.hips,
                    'chest': m.chest,
                    'biceps': m.biceps,
                    'measured_at': m.measured_at,
                    'notes': m.notes
                }
            return None

    def get_measurement_stats(self, user_id: int, days: int = 30):
        with self._get_session() as session:
            from sqlalchemy import func
            stats = session.query(
                func.min(Measurement.weight).label('min_weight'),
                func.max(Measurement.weight).label('max_weight'),
                func.avg(Measurement.weight).label('avg_weight'),
                func.count(Measurement.id).label('total')
            ).filter(
                Measurement.user_id == user_id,
                Measurement.measured_at >= datetime.now() - timedelta(days=days)
            ).first()
            if stats:
                return {
                    'min_weight': stats.min_weight,
                    'max_weight': stats.max_weight,
                    'avg_weight': stats.avg_weight,
                    'total': stats.total
                }
            return None

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
            return {
                'id': reminder.id,
                'trainer_id': reminder.trainer_id,
                'day_of_week': reminder.day_of_week,
                'time': reminder.time.strftime("%H:%M"),
                'is_active': reminder.is_active,
                'created_at': reminder.created_at
            }

    def get_trainer_reminders(self, trainer_id: int):
        with self._get_session() as session:
            reminders = session.query(Reminder).filter(
                Reminder.trainer_id == trainer_id,
                Reminder.is_active == True
            ).all()
            result = []
            for r in reminders:
                result.append({
                    'id': r.id,
                    'trainer_id': r.trainer_id,
                    'day_of_week': r.day_of_week,
                    'time': r.time.strftime("%H:%M"),
                    'is_active': r.is_active,
                    'created_at': r.created_at
                })
            return result

    def get_reminder(self, reminder_id: int):
        with self._get_session() as session:
            r = session.query(Reminder).filter(Reminder.id == reminder_id).first()
            if r:
                return {
                    'id': r.id,
                    'trainer_id': r.trainer_id,
                    'day_of_week': r.day_of_week,
                    'time': r.time.strftime("%H:%M"),
                    'is_active': r.is_active,
                    'created_at': r.created_at
                }
            return None

    def update_reminder(self, reminder_id: int, **kwargs):
        with self._get_session() as session:
            r = session.query(Reminder).filter(Reminder.id == reminder_id).first()
            if r:
                for key, value in kwargs.items():
                    if hasattr(r, key):
                        setattr(r, key, value)
                session.flush()
                return {
                    'id': r.id,
                    'trainer_id': r.trainer_id,
                    'day_of_week': r.day_of_week,
                    'time': r.time.strftime("%H:%M"),
                    'is_active': r.is_active,
                    'created_at': r.created_at
                }
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
            return {
                'id': log.id,
                'reminder_id': log.reminder_id,
                'client_id': log.client_id,
                'sent_at': log.sent_at,
                'is_followup': log.is_followup,
                'is_acknowledged': log.is_acknowledged
            }

    def get_reminder_logs(self, client_id: int, days: int = 30):
        cutoff = datetime.now() - timedelta(days=days)
        with self._get_session() as session:
            logs = session.query(ReminderLog).filter(
                ReminderLog.client_id == client_id,
                ReminderLog.sent_at >= cutoff
            ).all()
            result = []
            for log in logs:
                result.append({
                    'id': log.id,
                    'reminder_id': log.reminder_id,
                    'client_id': log.client_id,
                    'sent_at': log.sent_at,
                    'is_followup': log.is_followup,
                    'is_acknowledged': log.is_acknowledged
                })
            return result

    # ====================== BROADCAST ======================

    def broadcast_message(self, message: str, sender_id: int):
        with self._get_session() as session:
            b = Broadcast(message=message, sent_by=sender_id, recipients_count=0)
            session.add(b)
            session.flush()
            return b.id

    def update_broadcast_count(self, broadcast_id: int, count: int):
        with self._get_session() as session:
            session.query(Broadcast).filter(Broadcast.id == broadcast_id).update(
                {"recipients_count": count}
            )

    def get_broadcasts(self, limit: int = 10):
        with self._get_session() as session:
            broadcasts = session.query(Broadcast).order_by(
                Broadcast.sent_at.desc()
            ).limit(limit).all()
            result = []
            for b in broadcasts:
                result.append({
                    'id': b.id,
                    'message': b.message,
                    'sent_by': b.sent_by,
                    'sent_at': b.sent_at,
                    'recipients_count': b.recipients_count
                })
            return result

    # ====================== SUBSCRIPTIONS ======================

    def get_user_subscription(self, user_id: int):
        with self._get_session() as session:
            sub = session.query(Subscription).filter(
                Subscription.user_id == user_id,
                Subscription.is_active == True
            ).first()
            if sub:
                return {
                    'id': sub.id,
                    'user_id': sub.user_id,
                    'plan': sub.plan,
                    'expires_at': sub.expires_at,
                    'created_at': sub.created_at,
                    'is_active': sub.is_active
                }
            return None

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
            return {
                'id': sub.id,
                'user_id': sub.user_id,
                'plan': sub.plan,
                'expires_at': sub.expires_at,
                'created_at': sub.created_at,
                'is_active': sub.is_active
            }

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
            return {
                'id': sub.id,
                'user_id': sub.user_id,
                'plan': sub.plan,
                'expires_at': sub.expires_at,
                'created_at': sub.created_at,
                'is_active': sub.is_active
            }

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
            subs = session.query(Subscription).filter(
                Subscription.is_active == True,
                Subscription.expires_at <= datetime.now()
            ).all()
            result = []
            for sub in subs:
                result.append({
                    'id': sub.id,
                    'user_id': sub.user_id,
                    'plan': sub.plan,
                    'expires_at': sub.expires_at,
                    'created_at': sub.created_at,
                    'is_active': sub.is_active
                })
            return result

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
