from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

def role_keyboard():
    kb = [
        [KeyboardButton(text="Тренер")],
        [KeyboardButton(text="Ученик")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def trainer_menu_keyboard():
    kb = [
        [KeyboardButton(text="👥 Ученики")],
        [KeyboardButton(text="📊 Статистика"), KeyboardButton(text="📈 Отчёты")],
        [KeyboardButton(text="⏰ Напоминания"), KeyboardButton(text="📨 Сообщение ученику")],
        [KeyboardButton(text="❓ Помощь")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def client_menu_keyboard():
    kb = [
        [KeyboardButton(text="📝 Внести замеры")],
        [KeyboardButton(text="📊 Мой прогресс")],
        [KeyboardButton(text="❓ Помощь")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def clients_list_keyboard(clients, action="info"):
    kb = []
    for c in clients:
        kb.append([InlineKeyboardButton(text=f"{c.full_name} (@{c.username})", callback_data=f"{action}_{c.id}")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

def client_actions_keyboard(client_id):
    kb = [
        [InlineKeyboardButton(text="📊 Замеры", callback_data=f"measurements_{client_id}")],
        [InlineKeyboardButton(text="📈 График", callback_data=f"chart_{client_id}")],
        [InlineKeyboardButton(text="📄 Отчёт", callback_data=f"report_{client_id}")],
        [InlineKeyboardButton(text="📨 Написать", callback_data=f"msg_{client_id}")],
        [InlineKeyboardButton(text="❌ Удалить", callback_data=f"delete_{client_id}")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def confirm_delete_keyboard(client_id):
    kb = [
        [
            InlineKeyboardButton(text="✅ Да", callback_data=f"confirm_delete_{client_id}"),
            InlineKeyboardButton(text="❌ Нет", callback_data="cancel_delete")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def client_action_keyboard(action, trainer_id):
    kb = [
        [InlineKeyboardButton(text="✅ Принять", callback_data=f"{action}:{trainer_id}")],
        [InlineKeyboardButton(text="❌ Отклонить", callback_data="reject_invite")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def client_info_keyboard(client_id):
    kb = [
        [InlineKeyboardButton(text="📊 Замеры", callback_data=f"measurements_{client_id}")],
        [InlineKeyboardButton(text="📈 График", callback_data=f"chart_{client_id}")],
        [InlineKeyboardButton(text="📄 Отчёт", callback_data=f"report_{client_id}")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)
