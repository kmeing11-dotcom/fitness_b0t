from sqlalchemy import (
    Column, Integer, String, Float, DateTime, ForeignKey,
    Boolean, Text, Date, Time, Enum, UniqueConstraint
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

Base = declarative_base()


class UserRole(str, enum.Enum):
    TRAINER = "trainer"
    CLIENT = "client"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    username = Column(String(100), unique=True)
    full_name = Column(String(200))
    role = Column(Enum(UserRole), nullable=False)

    # Trainer fields
    phone = Column(String(20))
    studio_name = Column(String(200))

    # Client fields
    age = Column(Integer)
    height = Column(Float)
    goal = Column(String(50))  # weight_loss, muscle_gain, maintain

    created_at = Column(DateTime, server_default=func.now())
    is_active = Column(Boolean, default=True)

    # Relationships
    trainer_clients = relationship("TrainerClient", foreign_keys="TrainerClient.trainer_id", back_populates="trainer")
    client_trainers = relationship("TrainerClient", foreign_keys="TrainerClient.client_id", back_populates="client")
    measurements = relationship("Measurement", back_populates="user")
    reminders = relationship("Reminder", back_populates="trainer")


class TrainerClient(Base):
    __tablename__ = "trainer_clients"

    id = Column(Integer, primary_key=True)
    trainer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    client_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    is_active = Column(Boolean, default=True)

    trainer = relationship("User", foreign_keys=[trainer_id], back_populates="trainer_clients")
    client = relationship("User", foreign_keys=[client_id], back_populates="client_trainers")


class Measurement(Base):
    __tablename__ = "measurements"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    weight = Column(Float)  # kg
    waist = Column(Float)  # cm
    hips = Column(Float)  # cm
    chest = Column(Float)  # cm
    biceps = Column(Float)  # cm
    measured_at = Column(DateTime, server_default=func.now(), index=True)
    notes = Column(Text)

    user = relationship("User", back_populates="measurements")


class Reminder(Base):
    __tablename__ = "reminders"

    id = Column(Integer, primary_key=True)
    trainer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    day_of_week = Column(Integer)  # 0-6 (Monday-Sunday)
    time = Column(Time, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())

    trainer = relationship("User", back_populates="reminders")


class ReminderLog(Base):
    __tablename__ = "reminder_logs"

    id = Column(Integer, primary_key=True)
    reminder_id = Column(Integer, ForeignKey("reminders.id"), nullable=False)
    client_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    sent_at = Column(DateTime, server_default=func.now())
    is_followup = Column(Boolean, default=False)
    is_acknowledged = Column(Boolean, default=False)

    reminder = relationship("Reminder")
    client = relationship("User")


class Broadcast(Base):
    __tablename__ = "broadcasts"

    id = Column(Integer, primary_key=True)
    message = Column(Text, nullable=False)
    sent_by = Column(Integer, ForeignKey("users.id"))
    sent_at = Column(DateTime, server_default=func.now())
    recipients_count = Column(Integer, default=0)

    sender = relationship("User")

class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    plan = Column(String(20), nullable=False, default="free")  # free, pro
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    is_active = Column(Boolean, default=True)

    user = relationship("User", back_populates="subscription")

# Не забудь добавить в модель User обратную связь:
# В классе User добавь строку:
# subscription = relationship("Subscription", back_populates="user", uselist=False)
