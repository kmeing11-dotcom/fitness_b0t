# app/services/reminder_service.py
import asyncio
from datetime import datetime, timedelta
from typing import Optional
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR

from app.config import Config
from app.db import Session
from app.models import User, UserRole, Reminder, ReminderLog, TrainerClient
from app.utils.logger import get_logger
import traceback

logger = get_logger(__name__)


class ReminderService:
    """Сервис для управления напоминаниями."""

    def __init__(self, bot):
        self.bot = bot
        self.scheduler = None
        self._running = False
        self._scheduler_task = None

        self.jobstores = {
            'default': MemoryJobStore()
        }

        logger.info("✅ ReminderService initialized")

    async def start(self):
        if self._running:
            logger.warning("ReminderService already running")
            return

        self._running = True

        self.scheduler = AsyncIOScheduler(
            jobstores=self.jobstores,
            timezone='UTC'  # FIX: базовый UTC, для каждого job — своя tz
        )

        self.scheduler.add_listener(
            self._on_job_executed,
            EVENT_JOB_EXECUTED | EVENT_JOB_ERROR
        )

        self.scheduler.start()

        self._schedule_cleanup_jobs()

        await self._restore_reminders()

        logger.info("✅ ReminderService started")

    async def stop(self):
        self._running = False

        if self.scheduler:
            self.scheduler.shutdown(wait=False)
            logger.info("✅ Scheduler stopped")

        if self._scheduler_task and not self._scheduler_task.done():
            self._scheduler_task.cancel()
            try:
                await self._scheduler_task
            except asyncio.CancelledError:
                pass

        logger.info("✅ ReminderService stopped")

    def _schedule_cleanup_jobs(self):
        if not self.scheduler:
            return

        self.scheduler.add_job(
            self.cleanup_logs,
            trigger=CronTrigger(hour=3, minute=0, timezone='UTC'),
            id='cleanup_logs',
            replace_existing=True,
            misfire_grace_time=3600
        )
        logger.info("✅ Cleanup logs job scheduled")

        self.scheduler.add_job(
            self.check_missing_measurements,
            trigger=CronTrigger(day_of_week='sun', hour=23, minute=59, timezone='UTC'),
            id='check_missing_measurements',
            replace_existing=True,
            misfire_grace_time=7200
        )
        logger.info("✅ Missing measurements check job scheduled")

    async def _restore_reminders(self):
        """Восстанавливает напоминания при старте с правильной таймзоной."""
        try:
            with Session() as session:
                reminders = session.query(Reminder).filter(
                    Reminder.is_active == True
                ).all()

                restored_count = 0
                for reminder in reminders:
                    if reminder.day_of_week is None and reminder.time is None:
                        continue

                    # FIX: берём таймзону тренера
                    trainer = session.query(User).filter(
                        User.id == reminder.trainer_id
                    ).first()
                    tz = (trainer.timezone if trainer and trainer.timezone
                          else "Europe/Moscow")

                    await self.schedule_reminder(
                        trainer_id=reminder.trainer_id,
                        day_of_week=reminder.day_of_week,
                        time_str=reminder.time.strftime("%H:%M"),
                        reminder_id=reminder.id,
                        timezone=tz
                    )
                    restored_count += 1

                logger.info(f"✅ Restored {restored_count} reminders")

        except Exception as e:
            logger.error(f"❌ Failed to restore reminders: {e}")

    async def schedule_reminder(
        self,
        trainer_id: int,
        day_of_week: int,
        time_str: str,
        reminder_id: Optional[int] = None,
        timezone: str = "Europe/Moscow"
    ) -> Optional[str]:
        """
        FIX: добавлен параметр timezone.
        CronTrigger использует timezone для расчёта времени.
        """
        if not self.scheduler:
            logger.error("Scheduler not running")
            return None

        if not time_str:
            logger.error(f"Invalid time string: {time_str}")
            return None

        try:
            parts = time_str.split(':')
            if len(parts) != 2:
                logger.error(f"Invalid time format: {time_str}")
                return None

            hour = int(parts[0])
            minute = int(parts[1])

            if not (0 <= hour < 24 and 0 <= minute < 60):
                logger.error(f"Invalid time: {hour}:{minute}")
                return None

        except ValueError as e:
            logger.error(f"Failed to parse time '{time_str}': {e}")
            return None

        # FIX: используем переданную таймзону
        if day_of_week is not None:
            cron = CronTrigger(
                day_of_week=day_of_week,
                hour=hour,
                minute=minute,
                timezone=timezone
            )
        else:
            cron = CronTrigger(
                hour=hour,
                minute=minute,
                timezone=timezone
            )

        job_id = f"reminder_{trainer_id}_{day_of_week if day_of_week is not None else 'daily'}_{hour}_{minute}"
        if reminder_id:
            job_id = f"reminder_{reminder_id}"

        job = self.scheduler.add_job(
            self._send_reminders_to_clients,
            trigger=cron,
            args=[trainer_id],
            id=job_id,
            replace_existing=True,
            misfire_grace_time=3600,
            max_instances=1
        )

        logger.info(
            f"✅ Reminder scheduled: trainer={trainer_id}, "
            f"time={time_str}, day={day_of_week}, tz={timezone}"
        )
        return job_id

    async def remove_reminder(self, job_id: str) -> bool:
        if not self.scheduler:
            return False

        try:
            self.scheduler.remove_job(job_id)
            logger.info(f"✅ Removed reminder job: {job_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to remove reminder {job_id}: {e}")
            return False

    async def _send_reminders_to_clients(self, trainer_id: int):
        try:
            logger.info(f"📤 Sending reminders to clients of trainer {trainer_id}")

            with Session() as session:
                trainer_clients = session.query(TrainerClient).filter(
                    TrainerClient.trainer_id == trainer_id,
                    TrainerClient.is_active == True
                ).all()

                if not trainer_clients:
                    logger.debug(f"No active clients for trainer {trainer_id}")
                    return

                trainer = session.query(User).filter(
                    User.id == trainer_id
                ).first()

                if not trainer:
                    logger.error(f"Trainer {trainer_id} not found")
                    return

                reminder = session.query(Reminder).filter(
                    Reminder.trainer_id == trainer_id,
                    Reminder.is_active == True
                ).first()

                message = (
                    "⏰ Напоминание: пришлите свои замеры через /set_measurements\n\n"
                    "📝 Чтобы отслеживать прогресс, важно заполнять замеры регулярно!"
                )

                sent_count = 0
                for tc in trainer_clients:
                    client = tc.client
                    try:
                        await self.bot.send_message(
                            chat_id=client.telegram_id,
                            text=message
                        )
                        sent_count += 1

                        if reminder:
                            self._log_reminder(reminder.id, client.id, is_followup=False)

                        await self._schedule_followup(client.id, trainer_id)

                        await asyncio.sleep(0.5)

                    except Exception as e:
                        logger.error(f"Error sending reminder to {client.telegram_id}: {e}")

                logger.info(f"✅ Sent {sent_count} reminders for trainer {trainer_id}")

        except Exception as e:
            logger.error(f"Error in _send_reminders_to_clients: {e}\n{traceback.format_exc()}")

    async def _schedule_followup(self, client_id: int, trainer_id: int):
        """Планирует повторное напоминание через 24 часа."""
        run_time = datetime.now() + timedelta(hours=24)
        job_id = f"followup_{client_id}_{int(run_time.timestamp())}"

        if self.scheduler is None:
            return

        self.scheduler.add_job(
            self._send_followup_reminder,
            trigger=DateTrigger(run_date=run_time),
            args=[client_id, trainer_id],
            id=job_id,
            replace_existing=True,
            misfire_grace_time=3600
        )

    async def _send_followup_reminder(self, client_id: int, trainer_id: int):
        try:
            logger.info(f"📤 Sending followup to client {client_id}")

            with Session() as session:
                client = session.query(User).filter(User.id == client_id).first()
                if not client:
                    return

                from app.models import Measurement
                last_measurement = session.query(Measurement).filter(
                    Measurement.user_id == client_id
                ).order_by(Measurement.measured_at.desc()).first()

                if last_measurement and (datetime.now() - last_measurement.measured_at) < timedelta(hours=24):
                    logger.debug(f"Client {client_id} already submitted measurements")
                    return

                message = (
                    "⏰ Повторное напоминание: пожалуйста, пришлите замеры через /set_measurements\n\n"
                    "📊 Регулярные замеры помогают отслеживать прогресс!"
                )

                await self.bot.send_message(
                    chat_id=client.telegram_id,
                    text=message
                )

                reminder = session.query(Reminder).filter(
                    Reminder.trainer_id == trainer_id,
                    Reminder.is_active == True
                ).first()

                if reminder:
                    self._log_reminder(reminder.id, client_id, is_followup=True)

                logger.info(f"✅ Sent follow-up to client {client_id}")

        except Exception as e:
            logger.error(f"Error in followup for client {client_id}: {e}")

    def _log_reminder(self, reminder_id: int, client_id: int, is_followup: bool = False):
        try:
            with Session() as session:
                log = ReminderLog(
                    reminder_id=reminder_id,
                    client_id=client_id,
                    is_followup=is_followup,
                    is_acknowledged=False
                )
                session.add(log)
                session.commit()
        except Exception as e:
            logger.error(f"Failed to log reminder: {e}")

    async def check_missing_measurements(self):
        try:
            logger.info("📊 Checking missing measurements...")

            with Session() as session:
                from app.models import Measurement

                clients = session.query(User).filter(
                    User.role == UserRole.CLIENT,
                    User.is_active == True
                ).all()

                missing_clients = []
                for client in clients:
                    last_measurement = session.query(Measurement).filter(
                        Measurement.user_id == client.id
                    ).order_by(Measurement.measured_at.desc()).first()

                    if not last_measurement or (datetime.now() - last_measurement.measured_at) > timedelta(days=7):
                        missing_clients.append(client)

                if not missing_clients:
                    return

                trainer_groups = {}
                for client in missing_clients:
                    trainer_relations = session.query(TrainerClient).filter(
                        TrainerClient.client_id == client.id,
                        TrainerClient.is_active == True
                    ).all()

                    for relation in trainer_relations:
                        if relation.trainer_id not in trainer_groups:
                            trainer_groups[relation.trainer_id] = []
                        trainer_groups[relation.trainer_id].append(
                            client.full_name or f"Клиент {client.telegram_id}"
                        )

                for trainer_id, client_names in trainer_groups.items():
                    trainer = session.query(User).filter(User.id == trainer_id).first()
                    if not trainer:
                        continue

                    message = (
                        f"📊 Еженедельный отчёт: {len(client_names)} клиентов "
                        f"не отправили замеры за неделю:\n\n"
                    )
                    message += "\n".join(f"• {name}" for name in client_names[:10])
                    if len(client_names) > 10:
                        message += f"\n\n... и ещё {len(client_names) - 10} клиентов"

                    try:
                        await self.bot.send_message(
                            chat_id=trainer.telegram_id,
                            text=message
                        )
                        await asyncio.sleep(0.5)
                    except Exception as e:
                        logger.error(f"Error sending report to trainer {trainer_id}: {e}")

        except Exception as e:
            logger.error(f"Error in check_missing_measurements: {e}")

    async def cleanup_logs(self):
        try:
            import os
            from pathlib import Path

            log_dir = Path(Config.LOG_FILE).parent
            if not log_dir.exists():
                return

            log_files = list(log_dir.glob("*.log*"))
            log_files.sort(key=os.path.getmtime)

            if len(log_files) > 7:
                removed_count = 0
                for file in log_files[:-7]:
                    try:
                        os.remove(file)
                        removed_count += 1
                    except Exception as e:
                        logger.error(f"Error removing {file}: {e}")

                logger.info(f"🧹 Cleaned up {removed_count} old log files")

        except Exception as e:
            logger.error(f"Error in cleanup_logs: {e}")

    def _on_job_executed(self, event):
        if event.exception:
            logger.error(f"Job {event.job_id} failed: {event.exception}")
        else:
            logger.debug(f"Job {event.job_id} executed")
