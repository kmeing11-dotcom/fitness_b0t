import asyncio
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from app.config import Config

class BackupService:
    @staticmethod
    async def backup_database():
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_dir = Path(Config.TEMP_FOLDER) / "backups"
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            backup_file = backup_dir / f"db_backup_{timestamp}.sql"
            
            # Для SQLite просто копируем файл
            db_path = Path("fitness.db")
            if db_path.exists():
                import shutil
                shutil.copy2(db_path, backup_file)
                print(f"Backup created: {backup_file}")
                return str(backup_file)
            
            return None
            
        except Exception as e:
            print(f"Error creating backup: {e}")
            return None
    
    @staticmethod
    async def cleanup_old_backups(days_to_keep: int = 7):
        try:
            backup_dir = Path(Config.TEMP_FOLDER) / "backups"
            if not backup_dir.exists():
                return
            
            cutoff = datetime.now() - timedelta(days=days_to_keep)
            
            for backup_file in backup_dir.glob("db_backup_*.sql"):
                if datetime.fromtimestamp(backup_file.stat().st_mtime) < cutoff:
                    backup_file.unlink()
                    print(f"Removed old backup: {backup_file}")
                    
        except Exception as e:
            print(f"Error cleaning backups: {e}")