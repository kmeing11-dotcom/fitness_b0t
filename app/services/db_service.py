from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy import select, update, delete, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from app.config import Config
from app.models import (
    User, TrainerClient, Measurement, Reminder, 
    ReminderLog, Broadcast, UserRole
)

class DatabaseService:
    def __init__(self):
        if Config.DATABASE_URL.startswith("sqlite"):
            self.engine = create_async_engine(
                Config.DATABASE_URL,
                echo=False,
                connect_args={"check_same_thread": False}
            )
        else:
            self.engine = create_async_engine(
                Config.DATABASE_URL,
                echo=False,
                pool_size=10,
                max_overflow=20
            )
        self.async_session = sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )
    
    async def get_session(self):
        async with self.async_session() as session:
            return session
    
    async def get_user(self, telegram_id: int) -> Optional[User]:
        async with await self.get_session() as session:
            result = await session.execute(
                select(User).where(User.telegram_id == telegram_id)
            )
            return result.scalar_one_or_none()
    
    async def get_user_by_username(self, username: str) -> Optional[User]:
        async with await self.get_session() as session:
            result = await session.execute(
                select(User).where(User.username == username)
            )
            return result.scalar_one_or_none()
    
    async def create_user(self, telegram_id: int, username: str, full_name: str, 
                         role: UserRole, **kwargs) -> User:
        async with await self.get_session() as session:
            user = User(
                telegram_id=telegram_id,
                username=username,
                full_name=full_name,
                role=role,
                **kwargs
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            return user
    
    async def get_trainer_clients(self, trainer_id: int) -> List[User]:
        async with await self.get_session() as session:
            result = await session.execute(
                select(User)
                .join(TrainerClient, User.id == TrainerClient.client_id)
                .where(
                    TrainerClient.trainer_id == trainer_id,
                    TrainerClient.is_active == True,
                    User.is_active == True
                )
            )
            return result.scalars().all()
    
    async def add_client_to_trainer(self, trainer_id: int, client_id: int) -> bool:
        async with await self.get_session() as session:
            existing = await session.execute(
                select(TrainerClient).where(
                    TrainerClient.trainer_id == trainer_id,
                    TrainerClient.client_id == client_id
                )
            )
            if existing.scalar_one_or_none():
                return False
            
            tc = TrainerClient(trainer_id=trainer_id, client_id=client_id)
            session.add(tc)
            await session.commit()
            return True
    
    async def remove_client_from_trainer(self, trainer_id: int, client_id: int):
        async with await self.get_session() as session:
            await session.execute(
                update(TrainerClient)
                .where(
                    TrainerClient.trainer_id == trainer_id,
                    TrainerClient.client_id == client_id
                )
                .values(is_active=False)
            )
            await session.commit()
    
    async def create_measurement(self, user_id: int, data: Dict[str, float]) -> Measurement:
        async with await self.get_session() as session:
            measurement = Measurement(
                user_id=user_id,
                **data
            )
            session.add(measurement)
            await session.commit()
            await session.refresh(measurement)
            return measurement
    
    async def get_last_measurement(self, user_id: int) -> Optional[Measurement]:
        async with await self.get_session() as session:
            result = await session.execute(
                select(Measurement)
                .where(Measurement.user_id == user_id)
                .order_by(Measurement.measured_at.desc())
                .limit(1)
            )
            return result.scalar_one_or_none()
    
    async def get_measurements(self, user_id: int, days: int = 30) -> List[Measurement]:
        cutoff = datetime.now() - timedelta(days=days)
        async with await self.get_session() as session:
            result = await session.execute(
                select(Measurement)
                .where(
                    Measurement.user_id == user_id,
                    Measurement.measured_at >= cutoff
                )
                .order_by(Measurement.measured_at.asc())
            )
            return result.scalars().all()
    
    async def get_all_users(self) -> List[User]:
        async with await self.get_session() as session:
            result = await session.execute(select(User))
            return result.scalars().all()
    
    async def get_users_by_role(self, role: UserRole) -> List[User]:
        async with await self.get_session() as session:
            result = await session.execute(
                select(User).where(User.role == role, User.is_active == True)
            )
            return result.scalars().all()
    
    async def get_daily_measurements_count(self) -> int:
        today = datetime.now().date()
        async with await self.get_session() as session:
            result = await session.execute(
                select(func.count(Measurement.id))
                .where(func.date(Measurement.measured_at) == today)
            )
            return result.scalar()
    
    async def create_reminder(self, trainer_id: int, day_of_week: int, time_str: str) -> Reminder:
        from datetime import time
        t = datetime.strptime(time_str, "%H:%M").time()
        async with await self.get_session() as session:
            reminder = Reminder(
                trainer_id=trainer_id,
                day_of_week=day_of_week,
                time=t
            )
            session.add(reminder)
            await session.commit()
            await session.refresh(reminder)
            return reminder
    
    async def get_trainer_reminders(self, trainer_id: int) -> List[Reminder]:
        async with await self.get_session() as session:
            result = await session.execute(
                select(Reminder)
                .where(
                    Reminder.trainer_id == trainer_id,
                    Reminder.is_active == True
                )
            )
            return result.scalars().all()
    
    async def get_clients_without_measurements(self, days: int = 7) -> List[User]:
        cutoff = datetime.now() - timedelta(days=days)
        async with await self.get_session() as session:
            result = await session.execute(
                select(User)
                .where(
                    User.role == UserRole.CLIENT,
                    User.is_active == True,
                    ~User.id.in_(
                        select(Measurement.user_id)
                        .where(Measurement.measured_at >= cutoff)
                    )
                )
            )
            return result.scalars().all()
    
    async def log_reminder(self, reminder_id: int, client_id: int, is_followup: bool = False):
        async with await self.get_session() as session:
            log = ReminderLog(
                reminder_id=reminder_id,
                client_id=client_id,
                is_followup=is_followup
            )
            session.add(log)
            await session.commit()
    
    async def broadcast_message(self, message: str, sender_id: int) -> int:
        async with await self.get_session() as session:
            broadcast = Broadcast(
                message=message,
                sent_by=sender_id,
                recipients_count=0
            )
            session.add(broadcast)
            await session.commit()
            return broadcast.id
    
    async def update_broadcast_count(self, broadcast_id: int, count: int):
        async with await self.get_session() as session:
            await session.execute(
                update(Broadcast)
                .where(Broadcast.id == broadcast_id)
                .values(recipients_count=count)
            )
            await session.commit()