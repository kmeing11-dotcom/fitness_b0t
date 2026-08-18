from aiogram import Router, F
from aiogram.types import CallbackQuery
from app.services.db_service import DatabaseService
from app.keyboards.inline import client_actions_keyboard

router = Router()
db = DatabaseService()


@router.callback_query(F.data.startswith("info_"))
async def show_client_info(callback: CallbackQuery):
    client_id = int(callback.data.split("_")[1])
    client = db.get_user(client_id)
    if not client:
        await callback.answer("❌ Ученик не найден.")
        return

    text = (
        f"👤 **{client.full_name}**\n"
        f"📱 @{client.username}\n"
        f"🎂 Возраст: {client.age or 'N/A'}\n"
        f"📏 Рост: {client.height or 'N/A'} см\n"
        f"🎯 Цель: {client.goal or 'N/A'}"
    )

    # ----------------- ДОБАВЬ ЭТУ СТРОКУ -----------------
    text += "\n\n📊 Нажми /stats, чтобы увидеть график прогресса."
    # ----------------------------------------------------

    await callback.message.edit_text(text, parse_mode="Markdown")
    await callback.answer()
