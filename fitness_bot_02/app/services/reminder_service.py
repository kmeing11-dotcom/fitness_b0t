from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, timedelta
from app.services.db_service import DatabaseService
from app.db import get_db

class ReminderService:
    def __init__(self, bot):
        self.bot = bot
        self.scheduler = AsyncIOScheduler(jobstores={'default': MemoryJobStore()})
        self.scheduler.start()

    async def schedule_reminder(self, trainer_id, day_of_week, time_str):
        hour, minute = map(int, time_str.split(':'))
        cron = CronTrigger(day_of_week=day_of_week, hour=hour, minute=minute)
        job_id = f"reminder_{trainer_id}_{day_of_week}_{hour}_{minute}"
        self.scheduler.add_job(
            self.send_reminders_to_clients,
            trigger=cron,
            args=[trainer_id],
            id=job_id,
            replace_existing=True
        )

    async def send_reminders_to_clients(self, trainer_id):
        db = DatabaseService(next(get_db()))
        clients = db.get_trainer_clients(trainer_id)
        for client in clients:
            try:
                await self.bot.send_message(client.telegram_id, "⏰ Напоминание: внесите замеры через /set_measurements")
                await asyncio.sleep(0.5)
            except:
                pass