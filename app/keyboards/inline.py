# app/keyboards/inline.py
from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from typing import List, Optional


def _get(obj, key, default=None):
    """Универсальный доступ к полю (dict / DotDict / объект)."""
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


# ============================================================
#  REPLY KEYBOARDS
# ============================================================

def get_role_keyboard() -> ReplyKeyboardMarkup:
    kb = [
        [KeyboardButton(text="👨‍🏫 Тренер")],
        [KeyboardButton(text="👤 Ученик")]
    ]
    return ReplyKeyboardMarkup(
        keyboard=kb,
        resize_keyboard=True,
        one_time_keyboard=True
    )


def get_trainer_menu_keyboard() -> ReplyKeyboardMarkup:
    kb = [
        [KeyboardButton(text="👥 Мои ученики")],
        [KeyboardButton(text="📊 Статистика"), KeyboardButton(text="📈 Отчёты")],
        [KeyboardButton(text="⏰ Напоминания"), KeyboardButton(text="📨 Рассылка")],
        [KeyboardButton(text="⚙️ Настройки"), KeyboardButton(text="❓ Помощь")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)


def get_client_menu_keyboard() -> ReplyKeyboardMarkup:
    kb = [
        [KeyboardButton(text="📝 Внести замеры")],
        [KeyboardButton(text="📊 Мой прогресс")],
        [KeyboardButton(text="📄 Мой отчёт")],
        [KeyboardButton(text="❓ Помощь")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)


def get_cancel_keyboard() -> ReplyKeyboardMarkup:
    """
    FIX: раньше была кнопка «❌ Отмена» — не работала.
    Теперь — «🔙 Назад». Используется в FSM, где хендлер
    сам ловит текст «🔙 Назад» и отменяет ввод.
    """
    kb = [[KeyboardButton(text="🔙 Назад")]]
    return ReplyKeyboardMarkup(
        keyboard=kb,
        resize_keyboard=True,
        one_time_keyboard=True
    )


def get_back_keyboard() -> ReplyKeyboardMarkup:
    """Reply-клавиатура с кнопкой Назад (только для обычных сообщений)."""
    kb = [[KeyboardButton(text="🔙 Назад")]]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)


def get_yes_no_keyboard() -> ReplyKeyboardMarkup:
    kb = [[KeyboardButton(text="✅ Да"), KeyboardButton(text="❌ Нет")]]
    return ReplyKeyboardMarkup(
        keyboard=kb,
        resize_keyboard=True,
        one_time_keyboard=True
    )


# ============================================================
#  INLINE KEYBOARDS
# ============================================================

def get_clients_list_keyboard(
    clients: List,
    action: str = "info",
    page: int = 0,
    per_page: int = 5
) -> Optional[InlineKeyboardMarkup]:
    if not clients:
        return None

    total = len(clients)
    start = page * per_page
    end = min(start + per_page, total)

    kb = []

    for client in clients[start:end]:
        name = (
            _get(client, 'full_name')
            or _get(client, 'username')
            or f"ID:{_get(client, 'id')}"
        )
        client_id = _get(client, 'id')
        kb.append([
            InlineKeyboardButton(
                text=f"👤 {name}",
                callback_data=f"{action}_{client_id}"
            )
        ])

    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton(
            text="⬅️",
            callback_data=f"page_{page - 1}_{action}"
        ))
    if end < total:
        nav_row.append(InlineKeyboardButton(
            text="➡️",
            callback_data=f"page_{page + 1}_{action}"
        ))
    if nav_row:
        kb.append(nav_row)

    kb.append([
        InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")
    ])

    return InlineKeyboardMarkup(inline_keyboard=kb)


def get_client_actions_keyboard(client_id: int) -> InlineKeyboardMarkup:
    kb = [
        [
            InlineKeyboardButton(text="📊 Замеры", callback_data=f"measurements_{client_id}")
        ],
        [
            InlineKeyboardButton(text="📈 График", callback_data=f"chart_{client_id}"),
            InlineKeyboardButton(text="📄 Отчёт", callback_data=f"report_select_{client_id}")
        ],
        [
            InlineKeyboardButton(text="✏️ Написать", callback_data=f"msg_{client_id}"),
            InlineKeyboardButton(text="❌ Удалить", callback_data=f"delete_{client_id}")
        ],
        [
            InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_clients")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)


def get_confirm_delete_keyboard(client_id: int) -> InlineKeyboardMarkup:
    kb = [
        [
            InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"confirm_delete_{client_id}"),
            InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_delete")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)


def get_client_action_keyboard(action: str, trainer_id: int) -> InlineKeyboardMarkup:
    kb = [
        [
            InlineKeyboardButton(text="✅ Принять", callback_data=f"{action}:{trainer_id}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data="reject_invite")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)


# ============================================================
#  НАПОМИНАНИЯ
# ============================================================

def get_days_of_week_keyboard() -> InlineKeyboardMarkup:
    days = [
        ("Пн", 0), ("Вт", 1), ("Ср", 2),
        ("Чт", 3), ("Пт", 4), ("Сб", 5), ("Вс", 6)
    ]

    kb = []
    row = []
    for name, value in days:
        row.append(InlineKeyboardButton(
            text=name,
            callback_data=f"reminder_day_{value}"
        ))
        if len(row) == 4:
            kb.append(row)
            row = []
    if row:
        kb.append(row)

    kb.append([
        InlineKeyboardButton(text="📅 Ежедневно", callback_data="reminder_day_daily")
    ])
    kb.append([
        InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_reminder")
    ])

    return InlineKeyboardMarkup(inline_keyboard=kb)


def get_reminder_actions_keyboard(
    reminder_id: int,
    is_active: bool = True
) -> InlineKeyboardMarkup:
    kb = []

    if is_active:
        kb.append([
            InlineKeyboardButton(
                text="⏸️ Отключить",
                callback_data=f"toggle_reminder_{reminder_id}"
            )
        ])
    else:
        kb.append([
            InlineKeyboardButton(
                text="▶️ Включить",
                callback_data=f"toggle_reminder_{reminder_id}"
            )
        ])

    kb.append([
        InlineKeyboardButton(
            text="🗑️ Удалить",
            callback_data=f"delete_reminder_{reminder_id}"
        )
    ])

    kb.append([
        InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_reminders")
    ])

    return InlineKeyboardMarkup(inline_keyboard=kb)


# ============================================================
#  СТАТИСТИКА
# ============================================================

def get_stats_period_keyboard(client_id: int = None) -> InlineKeyboardMarkup:
    base = f"_{client_id}" if client_id else ""

    kb = [
        [
            InlineKeyboardButton(text="📊 7 дней", callback_data=f"stats_period_7{base}"),
            InlineKeyboardButton(text="📊 14 дней", callback_data=f"stats_period_14{base}")
        ],
        [
            InlineKeyboardButton(text="📊 30 дней", callback_data=f"stats_period_30{base}"),
            InlineKeyboardButton(text="📊 90 дней", callback_data=f"stats_period_90{base}")
        ],
        [
            InlineKeyboardButton(text="📊 Всё время", callback_data=f"stats_period_all{base}")
        ],
        [
            InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_stats")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)


# ============================================================
#  АДМИН
# ============================================================

def get_admin_keyboard() -> InlineKeyboardMarkup:
    kb = [
        [
            InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats"),
            InlineKeyboardButton(text="👥 Пользователи", callback_data="admin_users")
        ],
        [
            InlineKeyboardButton(text="📨 Рассылка", callback_data="admin_broadcast"),
            InlineKeyboardButton(text="💾 Бэкап", callback_data="admin_backup")
        ],
        [
            InlineKeyboardButton(text="📋 Логи", callback_data="admin_logs"),
            InlineKeyboardButton(text="💎 Подписки", callback_data="admin_subscriptions")
        ],
        [
            InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_admin")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)


def get_broadcast_confirm_keyboard() -> InlineKeyboardMarkup:
    kb = [
        [
            InlineKeyboardButton(text="✅ Отправить", callback_data="broadcast_confirm"),
            InlineKeyboardButton(text="❌ Отмена", callback_data="broadcast_cancel")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)


# ============================================================
#  ВЫБОР ЦЕЛИ
# ============================================================

def get_goal_inline_keyboard() -> InlineKeyboardMarkup:
    kb = [
        [
            InlineKeyboardButton(text="🎯 Похудение", callback_data="goal_weight_loss"),
            InlineKeyboardButton(text="💪 Набор", callback_data="goal_muscle_gain")
        ],
        [
            InlineKeyboardButton(text="⚖️ Поддержание", callback_data="goal_maintain"),
            InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_registration")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)


# ============================================================
#  ОБЩИЕ
# ============================================================

def get_back_inline_keyboard(callback: str = "back_to_menu") -> InlineKeyboardMarkup:
    kb = [
        [InlineKeyboardButton(text="🔙 Назад", callback_data=callback)]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)


def get_close_keyboard() -> InlineKeyboardMarkup:
    kb = [
        [InlineKeyboardButton(text="❌ Закрыть", callback_data="close")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)
