import shutil
import gzip
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List
import logging

from app.config import Config

logger = logging.getLogger(__name__)


class BackupService:
    """Сервис для создания и управления бэкапами"""

    @staticmethod
    async def backup_database(compress: bool = True) -> Optional[str]:
        """Создаёт бэкап базы данных."""
        try:
            backup_dir = Path(Config.TEMP_FOLDER) / "backups"
            backup_dir.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            db_path = Path("fitness_bot.db")
            if not db_path.exists():
                alternatives = ["fitness.db", "bot.db", "app.db"]
                for alt in alternatives:
                    if Path(alt).exists():
                        db_path = Path(alt)
                        break
                else:
                    logger.error("❌ Database file not found")
                    return None

            backup_name = f"db_backup_{timestamp}.sql"
            backup_path = backup_dir / backup_name

            shutil.copy2(db_path, backup_path)
            logger.info(f"✅ SQLite backup created: {backup_path}")

            if compress:
                compressed_path = backup_path.with_suffix(backup_path.suffix + ".gz")
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
    async def cleanup_old_backups(days_to_keep: int = 7, keep_min: int = 3) -> int:
        """Удаляет старые бэкапы."""
        try:
            backup_dir = Path(Config.TEMP_FOLDER) / "backups"
            if not backup_dir.exists():
                return 0

            cutoff = datetime.now() - timedelta(days=days_to_keep)
            removed_count = 0

            backup_files = list(backup_dir.glob("db_backup_*.sql*"))
            backup_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)

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
