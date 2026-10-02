# app/handlers/__init__.py
from . import (
    start,
    help,
    profile,       # <-- НОВЫЙ
    measurements,
    client,
    reports,
    stats,
    reminders,
    admin,
    menu,
)

__all__ = [
    "start",
    "help",
    "profile",     # <-- НОВЫЙ
    "measurements",
    "client",
    "reports",
    "stats",
    "reminders",
    "admin",
    "menu",
]
