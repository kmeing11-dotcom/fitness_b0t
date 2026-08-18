import os

# Удаляем старый файл базы данных
db_file = "fitness.db"
if os.path.exists(db_file):
    os.remove(db_file)
    print("✅ Старая база данных удалена.")
else:
    print("ℹ️ База данных не найдена (возможно, уже удалена).")
