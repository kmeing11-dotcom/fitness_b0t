from app.db import engine
from app.models import Base

print("🚀 Создаём таблицы...")
Base.metadata.create_all(engine)
print("✅ Все таблицы созданы!")
