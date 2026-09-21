# app/services/backup_service.py
import shutil
import gzip
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from app.config import Config
from app.utils.logger import get_logger

logger = get_logger(__name__)


class BackupService:
    """Сервис для создания и управления бэкапами БД."""

    @staticmethod
    def _get_db_path() -> Optional[Path]:
        """
        FIX: определяет путь к SQLite-БД из Config.DATABASE_URL.
        Раньше искал только в CWD по именам fitness_bot.db и т.п.
        """
        url = Config.DATABASE_URL or ""

        # SQLite: sqlite:///./fitness_bot.db  или sqlite:////abs/path.db
        if url.startswith("sqlite"):
            # Отрезаем "sqlite:///"
            raw = url.replace("sqlite:///", "", 1).replace("sqlite://", "", 1)
            # Убираем query-параметры (?check_same_thread=...)
            raw = raw.split("?")[0]
            p = Path(raw)
            if not p.is_absolute():
                p = Path.cwd() / p
            return p if p.exists() else None

        # PostgreSQL и прочее — файловый бэкап невозможен
        return None

    @staticmethod
    async def backup_database(compress: bool = True) -> Optional[str]:
        """Создаёт бэкап базы данных (SQLite)."""
        try:
            backup_dir = Path(Config.get_temp_folder()) / "backups"
            backup_dir.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            # FIX: сначала пробуем взять путь из DATABASE_URL
            db_path = BackupService._get_db_path()

            # Fallback: старый поиск по CWD
            if db_path is None:
                for name in ("fitness_bot.db", "fitness.db", "bot.db", "app.db"):
                    candidate = Path(name)
                    if candidate.exists():
                        db_path = candidate
                        break

            if db_path is None or not db_path.exists():
                logger.error(
                    "❌ Database file not found. "
                    "Для PostgreSQL файловый бэкап не поддерживается."
                )
                return None

            backup_name = f"db_backup_{timestamp}.sql"
            backup_path = backup_dir / backup_name

            shutil.copy2(db_path, backup_path)
            logger.info(f"✅ SQLite backup created: {backup_path}")

            if compress:
                compressed_path = backup_path.with_suffix(
                    backup_path.suffix + ".gz"
                )
                with open(backup_path, 'rb') as f_in:
                    with gzip.open(compressed_path, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
                backup_path.unlink()
                logger.info(f"✅ Compressed backup: {compressed_path}")
                return str(compressed_path)

            return str(backup_path)

        except Exception as e:
            logger.error(f"❌ Error creating backup: {e}")
            return None

    @staticmethod
    async def cleanup_old_backups(
        days_to_keep: int = 7,
        keep_min: int = 3
    ) -> int:
        """Удаляет старые бэкапы."""
        try:
            backup_dir = Path(Config.get_temp_folder()) / "backups"
            if not backup_dir.exists():
                return 0

            cutoff = datetime.now() - timedelta(days=days_to_keep)
            removed_count = 0

            backup_files = list(backup_dir.glob("db_backup_*.sql*"))
            backup_files.sort(
                key=lambda f: f.stat().st_mtime,
                reverse=True
            )

            if len(backup_files) <= keep_min:
                return 0

            for backup_file in backup_files[keep_min:]:
                mtime = datetime.fromtimestamp(backup_file.stat().st_mtime)
                if mtime < cutoff:
                    backup_file.unlink()
                    removed_count += 1
                    logger.info(f"🗑️ Removed old backup: {backup_file.name}")

            logger.info(f"✅ Cleaned up {removed_count} old backups")
            return removed_count

        except Exception as e:
            logger.error(f"❌ Error cleaning backups: {e}")
            return 0
