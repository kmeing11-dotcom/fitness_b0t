from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config import Config
from app.models import User, Measurement, TrainerClient, Reminder, ReminderLog, Broadcast, UserRole, Subscription
from datetime import datetime, timedelta

class DatabaseService:
    def __init__(self):
        self.engine = create_engine(
            Config.DATABASE_URL,
            connect_args={"check_same_thread": False}
        )
        self.Session = sessionmaker(bind=self.engine)

    # ====================== USER ======================
    def get_user(self, telegram_id: int):
        with self.Session() as session:
            return session.query(User).filter(User.telegram_id == telegram_id).first()

    def get_user_by_username(self, username: str):
        with self.Session() as session:
            return session.query(User).filter(User.username == username).first()

    def create_user(self, telegram_id, username, full_name, role, **kwargs):
        with self.Session() as session:
            user = User(
                telegram_id=telegram_id,
                username=username,
                full_name=full_name,
                role=role,
                **kwargs
            )
            session.add(user)
            session.commit()
            session.refresh(user)
            return user

    def get_all_users(self):
        with self.Session() as session:
            return session.query(User).all()

    def get_users_by_role(self, role):
        with self.Session() as session:
            return session.query(User).filter(User.role == role, User.is_active == True).all()

    # ====================== CLIENTS ======================
    def get_trainer_clients(self, trainer_id: int):
        with self.Session() as session:
            return session.query(User).join(TrainerClient, User.id == TrainerClient.client_id).filter(
                TrainerClient.trainer_id == trainer_id,
                TrainerClient.is_active == True,
                User.is_active == True
            ).all()

    def add_client_to_trainer(self, trainer_id, client_id):
        with self.Session() as session:
            # Ищем запись, даже если она неактивна
            existing = session.query(TrainerClient).filter_by(
                trainer_id=trainer_id, 
                client_id=client_id
            ).first()
            
            if existing:
                # Если запись есть, но неактивна — просто делаем её активной
                if not existing.is_active:
                    existing.is_active = True
                    session.commit()
                    return True
                # Если активна — значит, уже ученик
                return False
            
            # Если записи нет — создаём новую
            tc = TrainerClient(trainer_id=trainer_id, client_id=client_id)
            session.add(tc)
            session.commit()
            return True

    def remove_client_from_trainer(self, trainer_id, client_id):
        with self.Session() as session:
            session.query(TrainerClient).filter_by(trainer_id=trainer_id, client_id=client_id).update({"is_active": False})
            session.commit()

    # ====================== MEASUREMENTS ======================
    def create_measurement(self, user_id, data):
        with self.Session() as session:
            m = Measurement(user_id=user_id, **data)
            session.add(m)
            session.commit()
            session.refresh(m)
            return m

    def get_measurements(self, user_id, days=30):
        cutoff = datetime.now() - timedelta(days=days)
        with self.Session() as session:
            return session.query(Measurement).filter(
                Measurement.user_id == user_id,
                Measurement.measured_at >= cutoff
            ).order_by(Measurement.measured_at.asc()).all()

    def get_last_measurement(self, user_id: int):
        with self.Session() as session:
            return session.query(Measurement).filter(
                Measurement.user_id == user_id
            ).order_by(Measurement.measured_at.desc()).first()

    # ====================== REMINDERS ======================
    def create_reminder(self, trainer_id, day_of_week, time_str):
        from datetime import time
        t = datetime.strptime(time_str, "%H:%M").time()
        with self.Session() as session:
            reminder = Reminder(trainer_id=trainer_id, day_of_week=day_of_week, time=t)
            session.add(reminder)
            session.commit()
            session.refresh(reminder)
            return reminder

    def get_trainer_reminders(self, trainer_id):
        with self.Session() as session:
            return session.query(Reminder).filter_by(trainer_id=trainer_id, is_active=True).all()

    # ====================== BROADCAST ======================
    def broadcast_message(self, message: str, sender_id: int):
        with self.Session() as session:
            b = Broadcast(message=message, sent_by=sender_id, recipients_count=0)
            session.add(b)
            session.commit()
            return b.id

    def update_broadcast_count(self, broadcast_id: int, count: int):
        with self.Session() as session:
            session.query(Broadcast).filter(Broadcast.id == broadcast_id).update({"recipients_count": count})
            session.commit()

    # ====================== DAILY STATS ======================
    def get_daily_measurements_count(self):
        today = datetime.now().date()
        with self.Session() as session:
            return session.query(Measurement).filter(
                Measurement.measured_at >= today
            ).count()

    # ====================== SUBSCRIPTIONS ======================
    def get_user_subscription(self, user_id: int):
        with self.Session() as session:
            return session.query(Subscription).filter_by(user_id=user_id, is_active=True).first()

    def set_trial_subscription(self, user_id: int, days: int = 7):
        with self.Session() as session:
            # Деактивируем старую подписку, если есть
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
            session.commit()
            return sub

    def cancel_subscription(self, user_id: int):
        with self.Session() as session:
            sub = session.query(Subscription).filter_by(user_id=user_id, is_active=True).first()
            if sub:
                sub.is_active = False
                session.commit()
                return True
            return False

    def is_subscription_active(self, user_id: int) -> bool:
        with self.Session() as session:
            sub = session.query(Subscription).filter_by(user_id=user_id, is_active=True).first()
            if not sub:
                return False
            return sub.expires_at > datetime.now()

    def get_all_active_subscriptions(self):
        with self.Session() as session:
            return session.query(Subscription).filter_by(is_active=True).count()
