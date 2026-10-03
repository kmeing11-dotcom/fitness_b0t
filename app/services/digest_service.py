# app/services/digest_service.py
from datetime import datetime, timedelta
from app.db import Session
from app.models import User, UserRole, TrainerClient, Measurement
from app.utils.logger import get_logger
import traceback

logger = get_logger(__name__)


class DigestService:
    """Сервис еженедельных дайджестов для тренеров."""

    @staticmethod
    def build_digest_for_trainer(trainer_id: int) -> str:
        """
        Собирает текст дайджеста для одного тренера.
        Возвращает готовый HTML-текст или None, если нечего показывать.
        """
        try:
            with Session() as session:
                # Получаем тренера
                trainer = session.query(User).filter(
                    User.id == trainer_id
                ).first()

                if not trainer:
                    return None

                # Получаем активных учеников
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
                two_weeks_ago = datetime.now() - timedelta(days=14)

                # Кто сдал замеры за последнюю неделю
                submitted = []
                not_submitted = []
                changes = []  # список (имя, изменение веса)
                stale_clients = []  # без замеров >7 дней

                for client in clients:
                    # Последний замер
                    last = session.query(Measurement).filter(
                        Measurement.user_id == client.id
                    ).order_by(Measurement.measured_at.desc()).first()

                    if not last:
                        not_submitted.append(client.full_name or f"ID{client.id}")
                        stale_clients.append(
                            (client.full_name or f"ID{client.id}", "никогда")
                        )
                        continue

                    # Замер за последнюю неделю
                    if last.measured_at >= week_ago:
                        submitted.append(client.full_name or f"ID{client.id}")

                        # Изменение веса за неделю
                        first = session.query(Measurement).filter(
                            Measurement.user_id == client.id,
                            Measurement.measured_at >= week_ago,
                            Measurement.measured_at <= last.measured_at
                        ).order_by(Measurement.measured_at.asc()).first()

                        if first and first.weight and last.weight:
                            diff = last.weight - first.weight
                            changes.append((
                                client.full_name or f"ID{client.id}",
                                diff
                            ))
                    else:
                        not_submitted.append(client.full_name or f"ID{client.id}")

                        # Проверяем, как давно нет замеров
                        days_ago = (datetime.now() - last.measured_at).days
                        if days_ago >= 7:
                            stale_clients.append((
                                client.full_name or f"ID{client.id}",
                                f"{days_ago} дней назад"
                            ))

                # Формируем текст
                total = len(clients)
                text = f"📊 <b>Еженедельный отчёт</b>\n"
                text += f"━━━━━━━━━━━━━━━━━━━━━\n\n"

                text += f"👥 <b>Учеников:</b> {total}\n"
                text += f"✅ <b>Сдали замеры:</b> {len(submitted)}\n"
                text += f"⚠️ <b>Не сдали:</b> {len(not_submitted)}\n"

                # Изменения
                if changes:
                    text += f"\n📈 <b>Изменения веса за неделю:</b>\n"
                    # Сортируем по убыванию изменения (сначала самые большие)
                    changes.sort(key=lambda x: abs(x[1]), reverse=True)

                    for name, diff in changes[:10]:
                        emoji = "⬇️" if diff < 0 else "⬆️" if diff > 0 else "➡️"
                        text += f"  {emoji} {name}: {diff:+.1f} кг\n"

                    if len(changes) > 10:
                        text += f"  ... и ещё {len(changes) - 10}\n"

                # Отстающие
                if stale_clients:
                    text += f"\n⚠️ <b>Без замеров 7+ дней:</b>\n"
                    for name, info in stale_clients[:10]:
                        text += f"  • {name} ({info})\n"

                    if len(stale_clients) > 10:
                        text += f"  ... и ещё {len(stale_clients) - 10}\n"

                text += f"\n━━━━━━━━━━━━━━━━━━━━━\n"
                text += f"<i>Отчёт формируется автоматически каждую субботу.</i>"

                return text

        except Exception as e:
            logger.error(f"Error building digest for trainer {trainer_id}: {e}\n{traceback.format_exc()}")
            return None

    @staticmethod
    async def send_digests_to_all_trainers(bot):
        """
        Отправляет дайджест всем активным тренерам.
        Вызывается из APScheduler в субботу 20:30.
        """
        try:
            logger.info("📊 Starting weekly digests...")

            with Session() as session:
                trainers = session.query(User).filter(
                    User.role == UserRole.TRAINER,
                    User.is_active == True
                ).all()

                trainer_ids = [t.id for t in trainers]
                trainer_chats = {t.id: t.telegram_id for t in trainers}

            sent = 0
            failed = 0

            for trainer_id in trainer_ids:
                text = DigestService.build_digest_for_trainer(trainer_id)

                if not text:
                    continue

                try:
                    await bot.send_message(
                        chat_id=trainer_chats[trainer_id],
                        text=text,
                        parse_mode="HTML"
                    )
                    sent += 1
                    # Небольшая пауза, чтобы не спамить API Telegram
                    import asyncio
                    await asyncio.sleep(0.3)

                except Exception as e:
                    failed += 1
                    logger.warning(
                        f"Failed to send digest to trainer {trainer_id}: {e}"
                    )

            logger.info(f"✅ Digests sent: {sent} ok, {failed} failed")

        except Exception as e:
            logger.error(f"Error in send_digests_to_all_trainers: {e}\n{traceback.format_exc()}")
