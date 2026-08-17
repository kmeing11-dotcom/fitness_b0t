from sqlalchemy.orm import Session
from app.models import User, Measurement, TrainerClient, Reminder, ReminderLog, Broadcast, UserRole
from datetime import datetime, timedelta

class DatabaseService:
    def __init__(self, db: Session):
        self.db = db

    def get_user(self, telegram_id: int):
        return self.db.query(User).filter(User.telegram_id == telegram_id).first()

    def get_user_by_username(self, username: str):
        return self.db.query(User).filter(User.username == username).first()

    def create_user(self, telegram_id, username, full_name, role, **kwargs):
        user = User(telegram_id=telegram_id, username=username, full_name=full_name, role=role, **kwargs)
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def get_trainer_clients(self, trainer_id: int):
        return self.db.query(User).join(TrainerClient, User.id == TrainerClient.client_id).filter(
            TrainerClient.trainer_id == trainer_id,
            TrainerClient.is_active == True,
            User.is_active == True
        ).all()

    def add_client_to_trainer(self, trainer_id, client_id):
        if self.db.query(TrainerClient).filter_by(trainer_id=trainer_id, client_id=client_id).first():
            return False
        tc = TrainerClient(trainer_id=trainer_id, client_id=client_id)
        self.db.add(tc)
        self.db.commit()
        return True

    def remove_client_from_trainer(self, trainer_id, client_id):
        self.db.query(TrainerClient).filter_by(trainer_id=trainer_id, client_id=client_id).update({"is_active": False})
        self.db.commit()

    def create_measurement(self, user_id, data):
        m = Measurement(user_id=user_id, **data)
        self.db.add(m)
        self.db.commit()
        self.db.refresh(m)
        return m

    def get_measurements(self, user_id, days=30):
        cutoff = datetime.now() - timedelta(days=days)
        return self.db.query(Measurement).filter(
            Measurement.user_id == user_id,
            Measurement.measured_at >= cutoff
        ).order_by(Measurement.measured_at.asc()).all()

    def get_all_users(self):
        return self.db.query(User).all()

    def get_users_by_role(self, role):
        return self.db.query(User).filter(User.role == role, User.is_active == True).all()

    def create_reminder(self, trainer_id, day_of_week, time_str):
        from datetime import time
        t = datetime.strptime(time_str, "%H:%M").time()
        reminder = Reminder(trainer_id=trainer_id, day_of_week=day_of_week, time=t)
        self.db.add(reminder)
        self.db.commit()
        self.db.refresh(reminder)
        return reminder

    def get_trainer_reminders(self, trainer_id):
        return self.db.query(Reminder).filter_by(trainer_id=trainer_id, is_active=True).all()