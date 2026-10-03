# app/models.py
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, ForeignKey,
    Boolean, Text, Time, Enum, UniqueConstraint, Index, BigInteger
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

Base = declarative_base()


class UserRole(str, enum.Enum):
    TRAINER = "trainer"
    CLIENT = "client"


class Goal(str, enum.Enum):
    WEIGHT_LOSS = "weight_loss"
    MUSCLE_GAIN = "muscle_gain"
    MAINTAIN = "maintain"


class SubscriptionPlan(str, enum.Enum):
    FREE = "free"
    PRO = "pro"


class User(Base):
    __tablename__ = "users"
    timezone = Column(String(50), default="Europe/Moscow")
    invite_token = Column(String(32), unique=True, nullable=True, index=True)
    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False, index=True)
    username = Column(String(100), unique=True, nullable=True)
    full_name = Column(String(200), nullable=True)
    role = Column(Enum(UserRole, name="userrole"), nullable=False)

    # Trainer fields
    phone = Column(String(20), nullable=True)
    studio_name = Column(String(200), nullable=True)

    # Client fields
    age = Column(Integer, nullable=True)
    height = Column(Float, nullable=True)
    goal = Column(String(50), nullable=True)

    created_at = Column(DateTime, server_default=func.now())
    is_active = Column(Boolean, default=True)

    # Relationships
    trainer_clients = relationship(
        "TrainerClient",
        foreign_keys="TrainerClient.trainer_id",
        back_populates="trainer",
        cascade="all, delete-orphan"
    )
    client_trainers = relationship(
        "TrainerClient",
        foreign_keys="TrainerClient.client_id",
        back_populates="client",
        cascade="all, delete-orphan"
    )
    measurements = relationship(
        "Measurement",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    reminders = relationship(
        "Reminder",
        back_populates="trainer",
        cascade="all, delete-orphan"
    )
    subscription = relationship(
        "Subscription",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan"
    )
    reminder_logs = relationship(
        "ReminderLog",
        back_populates="client",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<User(id={self.id}, telegram_id={self.telegram_id}, role={self.role})>"


class TrainerClient(Base):
    __tablename__ = "trainer_clients"
    __table_args__ = (
        UniqueConstraint('trainer_id', 'client_id', name='uq_trainer_client'),
        Index('idx_trainer_client_trainer', 'trainer_id'),
        Index('idx_trainer_client_client', 'client_id'),
    )

    id = Column(Integer, primary_key=True)
    trainer_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    client_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    is_active = Column(Boolean, default=True)

    trainer = relationship("User", foreign_keys=[trainer_id], back_populates="trainer_clients")
    client = relationship("User", foreign_keys=[client_id], back_populates="client_trainers")

    def __repr__(self):
        return f"<TrainerClient(trainer_id={self.trainer_id}, client_id={self.client_id})>"


class Measurement(Base):
    __tablename__ = "measurements"
    __table_args__ = (
        Index('idx_measurement_user_date', 'user_id', 'measured_at'),
    )

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    weight = Column(Float, nullable=True)
    waist = Column(Float, nullable=True)
    hips = Column(Float, nullable=True)
    chest = Column(Float, nullable=True)
    biceps = Column(Float, nullable=True)
    measured_at = Column(DateTime, server_default=func.now(), index=True)
    notes = Column(Text, nullable=True)

    user = relationship("User", back_populates="measurements")

    def __repr__(self):
        return f"<Measurement(user_id={self.user_id}, measured_at={self.measured_at})>"


class Reminder(Base):
    __tablename__ = "reminders"

    id = Column(Integer, primary_key=True)
    trainer_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    day_of_week = Column(Integer, nullable=True)
    time = Column(Time, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())

    trainer = relationship("User", back_populates="reminders")
    logs = relationship("ReminderLog", back_populates="reminder", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Reminder(id={self.id}, trainer_id={self.trainer_id}, time={self.time})>"


class ReminderLog(Base):
    __tablename__ = "reminder_logs"
    __table_args__ = (
        Index('idx_reminder_log_client_sent', 'client_id', 'sent_at'),
        Index('idx_reminder_log_reminder', 'reminder_id'),
    )

    id = Column(Integer, primary_key=True)
    reminder_id = Column(Integer, ForeignKey("reminders.id", ondelete="CASCADE"), nullable=False)
    client_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    sent_at = Column(DateTime, server_default=func.now())
    is_followup = Column(Boolean, default=False)
    is_acknowledged = Column(Boolean, default=False)

    reminder = relationship("Reminder", back_populates="logs")
    client = relationship("User", back_populates="reminder_logs")

    def __repr__(self):
        return f"<ReminderLog(reminder_id={self.reminder_id}, client_id={self.client_id})>"


class Broadcast(Base):
    __tablename__ = "broadcasts"

    id = Column(Integer, primary_key=True)
    message = Column(Text, nullable=False)
    sent_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    sent_at = Column(DateTime, server_default=func.now())
    recipients_count = Column(Integer, default=0)

    sender = relationship("User")

    def __repr__(self):
        return f"<Broadcast(id={self.id}, sent_at={self.sent_at})>"


class Subscription(Base):
    __tablename__ = "subscriptions"
    __table_args__ = (
        Index('idx_subscription_user_active', 'user_id', 'is_active'),
        Index('idx_subscription_expires', 'expires_at'),
    )

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    plan = Column(Enum(SubscriptionPlan, name="subscriptionplan"), nullable=False, default=SubscriptionPlan.FREE)
    expires_at = Column(DateTime, nullable=False)
    is_trial = Column(Boolean, default=False)  
    created_at = Column(DateTime, server_default=func.now())
    is_active = Column(Boolean, default=True)

    user = relationship("User", back_populates="subscription")

    def is_expired(self):
        return self.expires_at < func.now() if self.expires_at else True

    def __repr__(self):
        return f"<Subscription(user_id={self.user_id}, plan={self.plan}, is_trial={self.is_trial}, active={self.is_active})>"
