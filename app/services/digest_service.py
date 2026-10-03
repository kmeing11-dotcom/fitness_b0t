# app/services/digest_service.py
from datetime import datetime, timedelta
import asyncio
import traceback

from app.db import Session
from app.models import User, UserRole, TrainerClient, Measurement
from app.utils.logger import get_logger

logger = get_logger(__name__)


class DigestService:
    """Сервис еженедельных дайджестов для тренеров."""

    @staticmethod
    def build_digest_for_trainer(trainer_id: int):
        """Собирает текст дайджеста для одного тренера."""
        try:
            with Session() as session:
                trainer = session.query(User).filter(User.id == trainer_id).first()
                if not trainer:
                    return None

                relations = session.query(TrainerClient).filter(
                    TrainerClient.trainer_id == trainer_id,
                    TrainerClient.is_active == True
                ).all()

                if not relations:
                    return None

                client_ids = [r.client_id for r in relations]
                clients = session.query(User).filter(
                    User.id.in_(client_ids),
                    User.is_active == True
                ).all()

                if not clients:
                    return None

                week_ago = datetime.now() - timedelta(days=7)

                submitted = []
                not_submitted = []
                changes = []
                stale_clients = []

                for client in clients:
                    name = client.full_name or f"ID{client.id}"

                    last = session.query(Measurement).filter(
                        Measurement.user_id == client.id
                    ).order_by(Measurement.measured_at.desc()).first()

                    if not last:
                        not_submitted.append(name)
                        stale_clients.append((name, "никогда"))
                        continue

                    if last.measured_at >= week_ago:
                        submitted.append(name)

                        first = session.query(Measurement).filter(
                            Measurement.user_id == client.id,
                            Measurement.measured_at >= week_ago,
                            Measurement.measured_at <= last.measured_at
                        ).order_by(Measurement.measured_at.asc()).first()

                        if first and first.weight and last.weight:
                            diff = last.weight - first.weight
                            changes.append((name, diff))
                    else:
                        not_submitted.append(name)

                        days_ago = (datetime.now() - last.measured_at).days
                        if days_ago >= 7:
                            stale_clients.append((name, f"{days_ago} дн. назад"))

                total = len(clients)
                text = f"📊 <b>Еженедельный отчёт</b>\n"
                text += f"━━━━━━━━━━━━━━━━━━━━━\n\n"
                text += f"👥 <b>Учеников:</b> {total}\n"
                text += f"✅ <b>Сдали замеры:</b> {len(submitted)}\n"
                text += f"⚠️ <b>Не сдали:</b> {len(not_submitted)}\n"

                if changes:
                    text += f"\n📈 <b>Изменения веса за неделю:</b>\n"
                    changes.sort(key=lambda x: abs(x[1]), reverse=True)
                    for name, diff in changes[:10]:
                        emoji = "⬇️" if diff < 0 else "⬆️" if diff > 0 else "➡️"
                        text += f"  {emoji} {name}: {diff:+.1f} кг\n"
                    if len(changes) > 10:
                        text += f"  ... и ещё {len(changes) - 10}\n"

                if stale_clients:
                    text += f"\n⚠️ <b>Без замеров 7+ дней:</b>\n"
                    for name, info in stale_clients[:10]:
                        text += f"  • {name} ({info})\n"
                    if len(stale_clients) > 10:
                        text += f"  ... и ещё {len(stale_clients) - 10}\n"

                text += f"\n━━━━━━━━━━━━━━━━━━━━━\n"
                text += f"<i>Отчёт формируется автоматически.</i>"

                return text

        except Exception as e:
            logger.error(f"Error in build_digest: {e}\n{traceback.format_exc()}")
            return None

    @staticmethod
    async def send_digest_to_one_trainer(bot, trainer_id: int, chat_id: int):
        """Отправляет дайджест одному тренеру (для персонального job)."""
        try:
            text = DigestService.build_digest_for_trainer(trainer_id)

            if not text:
                logger.debug(f"Digest skipped: trainer {trainer_id} has no data")
                return False

            await bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode="HTML"
            )
            logger.info(f"✅ Digest sent to trainer {trainer_id}")
            return True

        except Exception as e:
            logger.warning(f"Failed to send digest to {trainer_id}: {e}")
            return False

    @staticmethod
    async def send_digests_to_all_trainers(bot):
        """Отправляет дайджест всем активным тренерам (для /test_digest_all)."""
        try:
            logger.info("📊 Starting weekly digests to ALL...")

            with Session() as session:
                trainers = session.query(User).filter(
                    User.role == UserRole.TRAINER,
                    User.is_active == True
                ).all()

                trainer_data = [(t.id, t.telegram_id) for t in trainers]

            sent = 0
            failed = 0

            for trainer_id, chat_id in trainer_data:
                ok = await DigestService.send_digest_to_one_trainer(
                    bot, trainer_id, chat_id
                )
                if ok:
                    sent += 1
                else:
                    failed += 1
                await asyncio.sleep(0.3)

            logger.info(f"✅ Digests: {sent} ok, {failed} skipped/failed")

        except Exception as e:
            logger.error(f"Error in send_digests: {e}\n{traceback.format_exc()}")

