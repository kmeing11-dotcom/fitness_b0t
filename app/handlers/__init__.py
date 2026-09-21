# app/handlers/__init__.py
"""
Регистрация всех роутеров бота.

Порядок ВАЖЕН — aiogram проверяет роутеры по очереди,
и первый подходящий обрабатывает update.

Правила:
1. Специфичные фильтры (Command, F.data.regexp) — раньше
2. Catch-all (F.data == ..., F.text == ...) — позже
3. Reply-меню (menu.py) — в конце
"""

from . import (
    # Специфичные команды
    start,          # /start, регистрация, goal callback
    help,           # /help, /faq

    # Замеры и прогресс ученика
    measurements,   # /set_measurements, /my_progress

    # Работа с учениками (тренер)
    client,         # /add_client, /my_clients, /delete_client, info_, chart_, msg_

    # Отчёты — ДО client, чтобы report_select_* не перехватился
    reports,        # /report, /my_report, report_select_*

    # Статистика
    stats,          # /stats, stats_select_*, stats_period_*

    # Напоминания
    reminders,      # /set_reminder, /my_reminders, reminder_*, delete_reminder_*

    # Админ — ПОСЛЕ обычных, чтобы admin_* не конфликтовал
    admin,          # /admin, admin_*, broadcast_*, back_to_menu

    # Reply-меню — в САМОМ КОНЦЕ
    menu,           # F.text == "🔙 Назад" и т.д.

    # trainer.py — УДАЛЁН (дубликат client.py)
    # Если он тебе нужен — верни, но тогда убери дубли из client.py
)

__all__ = [
    "start",
    "help",
    "measurements",
    "client",
    "reports",
    "stats",
    "reminders",
    "admin",
    "menu",
]
