from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config import Config
from app.models import User, Measurement, TrainerClient, Reminder, ReminderLog, Broadcast, UserRole
from datetime import datetime, timedelta

class DatabaseService:
    def __init__(self):
        self.engine = create_engine(
            Config.DATABASE_URL,
            connect_args={"check_same_thread": False}
        )
        self.Session = sessionmaker(bind=self.engine)

    def get_user(self, telegram_id: int):
        with self.Session() as session:
            return session.query(User).filter(User.telegram_id == telegram_id).first()

    def get_user_by_username(self, username: str):
        with self.Session() as session:
            return session.query(User).filter(User.username == username).first()

    def create_user(self, telegram_id, username, full_name, role, **kwargs):
        with self.Session() as session:
            user = User(telegram_id=telegram_id, username=username, full_name=full_name, role=role, **kwargs)
            session.add(user)
            session.commit()
            session.refresh(user)
            return user

    def get_trainer_clients(self, trainer_id: int):
        with self.Session() as session:
            return session.query(User).join(TrainerClient, User.id == TrainerClient.client_id).filter(
                TrainerClient.trainer_id == trainer_id,
                TrainerClient.is_active == True,
                User.is_active == True
            ).all()

    def add_client_to_trainer(self, trainer_id, client_id):
        with self.Session() as session:
            if session.query(TrainerClient).filter_by(trainer_id=trainer_id, client_id=client_id).first():
                return False
            tc = TrainerClient(trainer_id=trainer_id, client_id=client_id)
            session.add(tc)
            session.commit()
            return True

    def remove_client_from_trainer(self, trainer_id, client_id):
        with self.Session() as session:
            session.query(TrainerClient).filter_by(trainer_id=trainer_id, client_id=client_id).update({"is_active": False})
            session.commit()

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

    def get_all_users(self):
        with self.Session() as session:
            return session.query(User).all()

    def get_users_by_role(self, role):
        with self.Session() as session:
            return session.query(User).filter(User.role == role, User.is_active == True).all()

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
