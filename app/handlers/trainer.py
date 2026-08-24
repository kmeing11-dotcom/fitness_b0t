from aiogram import Router, F
from aiogram.types import CallbackQuery
from app.services.db_service import DatabaseService
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = Router()
db = DatabaseService()


@router.callback_query()
async def handle_all_callbacks(callback: CallbackQuery):
    """Обработчик всех callback запросов"""
    try:
        logger.info(f"📥 Callback: {callback.data}")
        
        # Пробуем распарсить
        if "_" in callback.data:
            parts = callback.data.split("_")
            action = parts[0]
            
            if len(parts) > 1 and parts[1].isdigit():
                client_id = int(parts[1])
                logger.info(f"✅ Action: {action}, Client ID: {client_id}")
                
                client = db.get_user(client_id)
                if client:
                    await callback.answer(f"✅ Найден: {client.full_name}")
                    await callback.message.edit_text(
                        f"👤 {client.full_name}\n"
                        f"ID: {client.telegram_id}\n"
                        f"Action: {action}"
                    )
                else:
                    await callback.answer("❌ Клиент не найден")
            else:
                await callback.answer(f"❌ Неверный ID: {parts[1] if len(parts) > 1 else 'нет'}")
        else:
            await callback.answer(f"❌ Неизвестный формат: {callback.data}")
            
    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")
        await callback.answer(f"❌ Ошибка: {str(e)[:50]}")
