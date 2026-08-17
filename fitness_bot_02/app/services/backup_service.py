import asyncio
from datetime import datetime, timedelta
from pathlib import Path
import shutil
from app.config import Config

class BackupService:
    @staticmethod
    async def backup_database():
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_dir = Path(Config.TEMP_FOLDER) / "backups"
            backup_dir.mkdir(parents=True, exist_ok=True)
            backup_file = backup_dir / f"db_backup_{timestamp}.sql"
            db_path = Path("fitness.db")
            if db_path.exists():
                shutil.copy2(db_path, backup_file)
                return str(backup_file)
            return None
        except Exception as e:
            print(f"Backup error: {e}")
            return None

    @staticmethod
    async def cleanup_old_backups(days_to_keep: int = 7):
        try:
            backup_dir = Path(Config.TEMP_FOLDER) / "backups"
            if not backup_dir.exists():
                return
            cutoff = datetime.now() - timedelta(days=days_to_keep)
            for f in backup_dir.glob("db_backup_*.sql"):
                if datetime.fromtimestamp(f.stat().st_mtime) < cutoff:
                    f.unlink()
        except Exception as e:
            print(f"Cleanup error: {e}")