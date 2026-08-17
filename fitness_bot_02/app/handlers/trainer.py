from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from app.services.db_service import DatabaseService
from app.keyboards.inline import (
    clients_list_keyboard, client_actions_keyboard,
    trainer_menu_keyboard, confirm_delete_keyboard
)
from app.db import get_db
from app.models import UserRole

router = Router()

class MessageStates(StatesGroup):
    msg_text = State()

@router.message(F.text == "👥 Ученики")
async def show_clients(message: Message):
    db = DatabaseService(next(get_db()))
    user = db.get_user(message.from_user.id)
    if not user or user.role != UserRole.TRAINER:
        return
    clients = db.get_trainer_clients(user.id)
    if not clients:
        await message.answer("📭 У вас пока нет учеников.", reply_markup=trainer_menu_keyboard())
        return
    await message.answer("Выберите ученика:", reply_markup=clients_list_keyboard(clients))

@router.callback_query(F.data.startswith("info_"))
async def client_info(callback: CallbackQuery):
    client_id = int(callback.data.split("_")[1])
    db = DatabaseService(next(get_db()))
    client = db.get_user(client_id)
    if not client:
        await callback.answer("❌ Ученик не найден.")
        return
    text = f"👤 **{client.full_name}**\n"
    text += f"📱 @{client.username}\n"
    text += f"🎂 Возраст: {client.age or 'N/A'}\n"
    text += f"📏 Рост: {client.height or 'N/A'} см\n"
    text += f"🎯 Цель: {client.goal or 'N/A'}"
    await callback.message.edit_text(text, parse_mode="Markdown")
    await callback.message.edit_reply_markup(reply_markup=client_actions_keyboard(client_id))
    await callback.answer()

@router.callback_query(F.data.startswith("measurements_"))
async def client_measurements(callback: CallbackQuery):
    client_id = int(callback.data.split("_")[1])
    db = DatabaseService(next(get_db()))
    measurements = db.get_measurements(client_id, days=30)
    if not measurements:
        await callback.answer("📊 Нет замеров за последние 30 дней.")
        return
    last = measurements[-1]
    text = f"📊 Последний замер:\n📅 {last.measured_at.strftime('%d/%m')}\n"
    if last.weight: text += f"⚖️ Вес: {last.weight:.1f} кг\n"
    if last.waist: text += f"📏 Талия: {last.waist:.1f} см\n"
    if last.hips: text += f"📏 Бедра: {last.hips:.1f} см\n"
    if last.chest: text += f"📏 Грудь: {last.chest:.1f} см\n"
    if last.biceps: text += f"💪 Бицепс: {last.biceps:.1f} см\n"
    await callback.message.edit_text(text, parse_mode="Markdown")
    await callback.message.edit_reply_markup(reply_markup=client_actions_keyboard(client_id))
    await callback.answer()

@router.callback_query(F.data.startswith("chart_"))
async def client_chart(callback: CallbackQuery):
    client_id = int(callback.data.split("_")[1])
    db = DatabaseService(next(get_db()))
    measurements = db.get_measurements(client_id, days=30)
    if len(measurements) < 2:
        await callback.answer("❌ Нужно минимум 2 замера для графика.")
        return
    from app.services.chart_service import ChartService
    chart = ChartService()
    path = await chart.generate_stats_chart(client_id, measurements)
    if path:
        await callback.message.answer_photo(photo=open(path, 'rb'), caption="📈 График прогресса")
    else:
        await callback.answer("❌ Ошибка генерации графика.")
    await callback.answer()

@router.callback_query(F.data.startswith("report_"))
async def client_report(callback: CallbackQuery):
    client_id = int(callback.data.split("_")[1])
    db = DatabaseService(next(get_db()))
    client = db.get_user(client_id)
    measurements = db.get_measurements(client_id, days=28)
    from app.services.pdf_service import PDFService
    pdf = PDFService()
    path = await pdf.generate_client_report(client_id, client, measurements, None)
    if path:
        await callback.message.answer_document(open(path, 'rb'), caption="📄 Отчёт по ученику")
    else:
        await callback.answer("❌ Ошибка генерации отчёта.")
    await callback.answer()

@router.callback_query(F.data.startswith("msg_"))
async def client_message_start(callback: CallbackQuery, state: FSMContext):
    client_id = int(callback.data.split("_")[1])
    await state.set_state(MessageStates.msg_text)
    await state.update_data(msg_client_id=client_id)
    await callback.message.edit_text("📨 Введите текст сообщения для ученика:")
    await callback.answer()

@router.message(MessageStates.msg_text)
async def client_message_send(message: Message, state: FSMContext):
    data = await state.get_data()
    client_id = data['msg_client_id']
    db = DatabaseService(next(get_db()))
    client = db.get_user(client_id)
    if client:
        await message.bot.send_message(client.telegram_id, f"📩 Сообщение от тренера:\n\n{message.text}")
        await message.answer("✅ Сообщение отправлено ученику.", reply_markup=trainer_menu_keyboard())
    else:
        await message.answer("❌ Ученик не найден.", reply_markup=trainer_menu_keyboard())
    await state.clear()

@router.callback_query(F.data.startswith("delete_"))
async def client_delete_confirm(callback: CallbackQuery):
    client_id = int(callback.data.split("_")[1])
    await callback.message.edit_text("❓ Удалить ученика?", reply_markup=confirm_delete_keyboard(client_id))
    await callback.answer()

@router.callback_query(F.data.startswith("confirm_delete_"))
async def client_delete(callback: CallbackQuery):
    client_id = int(callback.data.split("_")[1])
    db = DatabaseService(next(get_db()))
    trainer = db.get_user(callback.from_user.id)
    db.remove_client_from_trainer(trainer.id, client_id)
    await callback.message.edit_text("✅ Ученик удалён.", reply_markup=trainer_menu_keyboard())
    await callback.answer()