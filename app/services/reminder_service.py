import asyncio
from datetime import datetime, time, timedelta
from typing import List, Dict
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.jobstores.memory import MemoryJobStore
from app.config import Config
from app.services.db_service import DatabaseService
from app.models import User, UserRole

class ReminderService:
    def __init__(self, bot):
        self.bot = bot
        self.db = DatabaseService()
        
        jobstores = {
            'default': MemoryJobStore()
        }
        
        self.scheduler = AsyncIOScheduler(jobstores=jobstores)
        self.scheduler.start()
        
        self.schedule_cleanup_jobs()
    
    def schedule_cleanup_jobs(self):
        self.scheduler.add_job(
            self.cleanup_logs,
            trigger=CronTrigger(hour=3, minute=0),
            id='cleanup_logs',
            replace_existing=True
        )
        
        self.scheduler.add_job(
            self.check_missing_measurements,
            trigger=CronTrigger(day_of_week='sun', hour=23, minute=59),
            id='check_missing_measurements',
            replace_existing=True
        )
    
    async def schedule_reminder(self, trainer_id: int, day_of_week: int, time_str: str):
        hour, minute = map(int, time_str.split(':'))
        
        cron = CronTrigger(
            day_of_week=day_of_week,
            hour=hour,
            minute=minute
        )
        
        job_id = f"reminder_{trainer_id}_{day_of_week}_{hour}_{minute}"
        
        self.scheduler.add_job(
            self.send_reminders_to_clients,
            trigger=cron,
            args=[trainer_id],
            id=job_id,
            replace_existing=True,
            misfire_grace_time=3600
        )
        
        return job_id
    
    async def send_reminders_to_clients(self, trainer_id: int):
        try:
            clients = await self.db.get_trainer_clients(trainer_id)
            
            if not clients:
                return
            
            message = "⏰ Напоминание: пришлите свои замеры через /set_measurements"
            
            for client in clients:
                try:
                    await self.bot.send_message(
                        chat_id=client.telegram_id,
                        text=message
                    )
                    
                    reminder = await self.db.get_trainer_reminders(trainer_id)
                    if reminder:
                        await self.db.log_reminder(reminder[0].id, client.id, is_followup=False)
                    
                    await self.schedule_followup(client.id, trainer_id)
                    
                    await asyncio.sleep(0.5)
                    
                except Exception as e:
                    print(f"Error sending reminder to client {client.telegram_id}: {e}")
                    
        except Exception as e:
            print(f"Error in send_reminders_to_clients: {e}")
    
    async def schedule_followup(self, client_id: int, trainer_id: int):
        def followup_job():
            asyncio.create_task(self.send_followup_reminder(client_id, trainer_id))
        
        run_time = datetime.now() + timedelta(hours=24)
        
        self.scheduler.add_job(
            followup_job,
            trigger='date',
            run_date=run_time,
            id=f"followup_{client_id}_{int(run_time.timestamp())}",
            replace_existing=True
        )
    
    async def send_followup_reminder(self, client_id: int, trainer_id: int):
        client = await self.db.get_user_by_username(str(client_id))
        if not client:
            return
        
        last_measurement = await self.db.get_last_measurement(client.id)
        
        if last_measurement and (datetime.now() - last_measurement.measured_at) < timedelta(hours=24):
            return
        
        try:
            message = "⏰ Повторное напоминание: пожалуйста, пришлите свои замеры через /set_measurements"
            await self.bot.send_message(
                chat_id=client.telegram_id,
                text=message
            )
            
            reminder = await self.db.get_trainer_reminders(trainer_id)
            if reminder:
                await self.db.log_reminder(reminder[0].id, client.id, is_followup=True)
                
        except Exception as e:
            print(f"Error sending follow-up to client {client.telegram_id}: {e}")
    
    async def check_missing_measurements(self):
        try:
            clients = await self.db.get_users_by_role(UserRole.CLIENT)
            
            missing_clients = []
            for client in clients:
                last_measurement = await self.db.get_last_measurement(client.id)
                
                if not last_measurement or (datetime.now() - last_measurement.measured_at) > timedelta(days=7):
                    missing_clients.append(client)
            
            if missing_clients:
                trainer_groups = {}
                
                for client in missing_clients:
                    async with self.db.get_session() as session:
                        from sqlalchemy import select
                        from app.models import TrainerClient
                        result = await session.execute(
                            select(TrainerClient.trainer_id)
                            .where(
                                TrainerClient.client_id == client.id,
                                TrainerClient.is_active == True
                            )
                        )
                        trainer_ids = result.scalars().all()
                        
                        for trainer_id in trainer_ids:
                            if trainer_id not in trainer_groups:
                                trainer_groups[trainer_id] = []
                            trainer_groups[trainer_id].append(client.full_name or str(client.telegram_id))
                
                for trainer_id, client_names in trainer_groups.items():
                    trainer = await self.db.get_user(trainer_id)
                    if trainer:
                        message = f"📊 Weekly Report: {len(client_names)} clients haven't submitted measurements this week:\n"
                        message += "\n".join(f"• {name}" for name in client_names[:10])
                        if len(client_names) > 10:
                            message += f"\n... and {len(client_names) - 10} more"
                        
                        await self.bot.send_message(
                            chat_id=trainer.telegram_id,
                            text=message
                        )
                        
                        await asyncio.sleep(0.5)
                        
        except Exception as e:
            print(f"Error in check_missing_measurements: {e}")
    
    async def cleanup_logs(self):
        import os
        from pathlib import Path
        from app.config import Config
        
        log_dir = Path(Config.LOG_FILE).parent
        if not log_dir.exists():
            return
        
        log_files = list(log_dir.glob("*.log*"))
        log_files.sort(key=os.path.getmtime)
        
        if len(log_files) > 7:
            for file in log_files[:-7]:
                try:
                    os.remove(file)
                    print(f"Removed old log file: {file}")
                except Exception as e:
                    print(f"Error removing log file {file}: {e}")