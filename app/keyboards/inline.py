from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton
)


def role_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🏋️ Тренер", callback_data="role_trainer"),
            InlineKeyboardButton(text="👨‍🎓 Ученик", callback_data="role_client")
        ]
    ])


def trainer_menu_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="👥 Мои ученики"),
                KeyboardButton(text="➕ Добавить ученика")
            ],
            [
                KeyboardButton(text="📊 Статистика"),
                KeyboardButton(text="📄 Отчёт")
            ],
            [
                KeyboardButton(text="⏰ Напоминания"),
                KeyboardButton(text="❓ Помощь")
            ]
        ],
        resize_keyboard=True
    )


def client_menu_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="📝 Замеры"),
                KeyboardButton(text="📈 Мой прогресс")
            ],
            [
                KeyboardButton(text="❓ Помощь")
            ]
        ],
        resize_keyboard=True
    )


def clients_list_keyboard(clients, action="client"):
    buttons = []
    for client in clients:
        name = client.full_name or client.username or f"ID:{client.telegram_id}"
        buttons.append([
            InlineKeyboardButton(
                text=f"👤 {name}",
                callback_data=f"{action}:{client.id}"
            )
        ])
    # Добавляем кнопки действий
    if action == "client" and clients:
        buttons.append([
            InlineKeyboardButton(text="📊 График", callback_data=f"client:chart:{clients[0].id}"),
            InlineKeyboardButton(text="📄 Отчёт", callback_data=f"client:report:{clients[0].id}")
        ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def client_action_keyboard(action: str, trainer_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="✅ Принять приглашение",
                callback_data=f"{action}:{trainer_id}"
            )
        ],
        [
            InlineKeyboardButton(
                text="❌ Отклонить",
                callback_data="decline_invite"
            )
        ]
    ])


def confirm_delete_keyboard(client_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"delete_confirm:{client_id}"),
            InlineKeyboardButton(text="❌ Отмена", callback_data="delete_cancel")
        ]
    ])


def client_info_keyboard(client_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📊 Замеры", callback_data=f"client:measurements:{client_id}"),
            InlineKeyboardButton(text="📈 График", callback_data=f"client:chart:{client_id}")
        ],
        [
            InlineKeyboardButton(text="📄 Отчёт", callback_data=f"client:report:{client_id}"),
            InlineKeyboardButton(text="🗑️ Удалить", callback_data=f"client:delete:{client_id}")
        ]
    ])