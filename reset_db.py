import os
from pathlib import Path

# Найдём файл fitness.db в любом месте проекта
base_dir = Path(__file__).parent
possible_paths = [
    base_dir / "fitness.db",
    base_dir / "app" / "fitness.db",
    base_dir / "temp" / "fitness.db",
    base_dir / "app" / "temp" / "fitness.db"
]

deleted = False
for path in possible_paths:
    if path.exists():
        path.unlink()
        print(f"✅ Удалена БД: {path}")
        deleted = True

if not deleted:
    print("ℹ️ База данных не найдена (будет создана при запуске).")

# Принудительно создадим новую БД через SQLAlchemy
from app.db import engine
from app.models import Base
print("🚀 Создаём новые таблицы...")
Base.metadata.create_all(engine)
print("✅ Новые таблицы созданы!")
