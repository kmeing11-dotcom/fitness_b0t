from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from typing import List, Optional
from app.models import User


# ============================================================
#  REPLY KEYBOARDS (обычные клавиатуры)
# ============================================================

def get_role_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура выбора роли"""
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
    """Главное меню тренера"""
    kb = [
        [KeyboardButton(text="👥 Мои ученики")],
        [KeyboardButton(text="📊 Статистика"), KeyboardButton(text="📈 Отчёты")],
        [KeyboardButton(text="⏰ Напоминания"), KeyboardButton(text="📨 Рассылка")],
        [KeyboardButton(text="⚙️ Настройки"), KeyboardButton(text="❓ Помощь")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)


def get_client_menu_keyboard() -> ReplyKeyboardMarkup:
    """Главное меню ученика"""
    kb = [
        [KeyboardButton(text="📝 Внести замеры")],
        [KeyboardButton(text="📊 Мой прогресс")],
        [KeyboardButton(text="📄 Мой отчёт")],
        [KeyboardButton(text="❓ Помощь")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)


def get_cancel_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура с кнопкой отмены"""
    kb = [
        [KeyboardButton(text="❌ Отмена")]
    ]
    return ReplyKeyboardMarkup(
        keyboard=kb,
        resize_keyboard=True,
        one_time_keyboard=True
    )


def get_back_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура с кнопкой назад (для обычных сообщений)"""
    kb = [
        [KeyboardButton(text="🔙 Назад")]
    ]
    return ReplyKeyboardMarkup(
        keyboard=kb,
        resize_keyboard=True
    )


def get_yes_no_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура Да/Нет"""
    kb = [
        [KeyboardButton(text="✅ Да"), KeyboardButton(text="❌ Нет")]
    ]
    return ReplyKeyboardMarkup(
        keyboard=kb,
        resize_keyboard=True,
        one_time_keyboard=True
    )


# ============================================================
#  INLINE KEYBOARDS (клавиатуры под сообщениями)
# ============================================================

def get_clients_list_keyboard(
    clients: List[dict],  # <-- теперь словари
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
        name = client.get('full_name') or client.get('username') or f"ID:{client.get('id')}"
        kb.append([
            InlineKeyboardButton(
                text=f"👤 {name}",
                callback_data=f"{action}_{client.get('id')}"
            )
        ])

    # ... остальной код без изменений


def get_client_actions_keyboard(client_id: int) -> InlineKeyboardMarkup:
    """Клавиатура действий с клиентом"""
    kb = [
        [
            InlineKeyboardButton(text="📊 Замеры", callback_data=f"measurements_{client_id}")
        ],
        [
            InlineKeyboardButton(text="📈 График", callback_data=f"chart_{client_id}"),
            InlineKeyboardButton(text="📄 Отчёт", callback_data=f"report_{client_id}")
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
    """Клавиатура подтверждения удаления"""
    kb = [
        [
            InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"confirm_delete_{client_id}"),
            InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_delete")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)


def get_client_action_keyboard(action: str, trainer_id: int) -> InlineKeyboardMarkup:
    """Клавиатура для подтверждения/отклонения действия"""
    kb = [
        [
            InlineKeyboardButton(text="✅ Принять", callback_data=f"{action}:{trainer_id}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data="reject_invite")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)


def get_client_info_keyboard(client_id: int) -> InlineKeyboardMarkup:
    """Клавиатура информации о клиенте"""
    kb = [
        [
            InlineKeyboardButton(text="📊 Замеры", callback_data=f"measurements_{client_id}"),
            InlineKeyboardButton(text="📈 График", callback_data=f"chart_{client_id}")
        ],
        [
            InlineKeyboardButton(text="📄 Отчёт", callback_data=f"report_{client_id}")
        ],
        [
            InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_clients")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)


# ============================================================
#  КЛАВИАТУРЫ ДЛЯ НАПОМИНАНИЙ
# ============================================================

def get_days_of_week_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора дня недели для напоминаний"""
    days = [
        ("Пн", 0), ("Вт", 1), ("Ср", 2),
        ("Чт", 3), ("Пт", 4), ("Сб", 5), ("Вс", 6)
    ]

    kb = []
    row = []
    for name, value in days:
        row.append(
            InlineKeyboardButton(
                text=name,
                callback_data=f"reminder_day_{value}"
            )
        )
        if len(row) == 4:
            kb.append(row)
            row = []
    if row:
        kb.append(row)

    kb.append([
        InlineKeyboardButton(
            text="📅 Ежедневно",
            callback_data="reminder_day_daily"
        )
    ])

    kb.append([
        InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_reminder")
    ])

    return InlineKeyboardMarkup(inline_keyboard=kb)


def get_reminder_time_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура с часто используемым временем для напоминаний"""
    kb = [
        [
            InlineKeyboardButton(text="08:00", callback_data="reminder_time_08:00"),
            InlineKeyboardButton(text="09:00", callback_data="reminder_time_09:00"),
            InlineKeyboardButton(text="10:00", callback_data="reminder_time_10:00")
        ],
        [
            InlineKeyboardButton(text="18:00", callback_data="reminder_time_18:00"),
            InlineKeyboardButton(text="19:00", callback_data="reminder_time_19:00"),
            InlineKeyboardButton(text="20:00", callback_data="reminder_time_20:00")
        ],
        [
            InlineKeyboardButton(text="🕐 Своё время", callback_data="reminder_time_custom")
        ],
        [
            InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_reminder")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)


def get_reminder_actions_keyboard(reminder_id: int, is_active: bool = True) -> InlineKeyboardMarkup:
    """Клавиатура управления напоминанием"""
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
#  КЛАВИАТУРЫ ДЛЯ СТАТИСТИКИ
# ============================================================

def get_stats_period_keyboard(client_id: int = None) -> InlineKeyboardMarkup:
    """Клавиатура выбора периода для статистики"""
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
#  КЛАВИАТУРЫ ДЛЯ ОТЧЁТОВ
# ============================================================

def get_report_actions_keyboard(client_id: int) -> InlineKeyboardMarkup:
    """Клавиатура действий с отчётом"""
    kb = [
        [
            InlineKeyboardButton(
                text="📄 Скачать PDF",
                callback_data=f"download_report_{client_id}"
            )
        ],
        [
            InlineKeyboardButton(
                text="📊 График",
                callback_data=f"chart_{client_id}"
            )
        ],
        [
            InlineKeyboardButton(text="🔙 Назад", callback_data=f"back_to_client_{client_id}")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)


# ============================================================
#  КЛАВИАТУРЫ ДЛЯ ПОДПИСКИ
# ============================================================

def get_subscription_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для подписки"""
    kb = [
        [
            InlineKeyboardButton(
                text="💎 PRO (7 дней бесплатно)",
                callback_data="subscribe_trial"
            )
        ],
        [
            InlineKeyboardButton(
                text="💎 PRO (месяц)",
                callback_data="subscribe_month"
            )
        ],
        [
            InlineKeyboardButton(
                text="💎 PRO (год)",
                callback_data="subscribe_year"
            )
        ],
        [
            InlineKeyboardButton(text="❌ Отмена", callback_data="close")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)


# ============================================================
#  КЛАВИАТУРЫ ДЛЯ РАССЫЛКИ
# ============================================================

def get_broadcast_confirm_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура подтверждения рассылки"""
    kb = [
        [
            InlineKeyboardButton(text="✅ Отправить", callback_data="broadcast_confirm"),
            InlineKeyboardButton(text="❌ Отмена", callback_data="broadcast_cancel")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)


# ============================================================
#  АДМИН-КЛАВИАТУРА
# ============================================================

def get_admin_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура администратора"""
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
            InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)


# ============================================================
#  КЛАВИАТУРА ДЛЯ ВЫБОРА ЦЕЛИ
# ============================================================

def get_goal_inline_keyboard() -> InlineKeyboardMarkup:
    """Inline-клавиатура для выбора цели"""
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
#  ОБЩИЕ КЛАВИАТУРЫ
# ============================================================

def get_close_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура с кнопкой закрытия (inline)"""
    kb = [
        [InlineKeyboardButton(text="❌ Закрыть", callback_data="close")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)


def get_back_inline_keyboard() -> InlineKeyboardMarkup:
    """Inline-клавиатура с кнопкой 'Назад'"""
    kb = [
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_clients")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)


def get_back_to_menu_keyboard(role: str) -> InlineKeyboardMarkup:
    """Клавиатура с кнопкой возврата в меню"""
    kb = [
        [InlineKeyboardButton(text="🏠 В меню", callback_data=f"back_to_menu_{role}")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)


# ============================================================
#  ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================

def get_action_from_callback(callback_data: str) -> tuple:
    """
    Разбирает callback_data на компоненты.
    """
    parts = callback_data.split('_')
    if len(parts) == 2:
        return (parts[0], parts[1], None)
    elif len(parts) == 3:
        return (parts[0], parts[1], parts[2])
    return (callback_data, None, None)
