from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime
from app.services.db_service import DatabaseService
from app.services.reminder_service import ReminderService

router = Router()
db = DatabaseService()
reminder_service = None  # Будет инициализирован в bot.py


class ReminderStates(StatesGroup):
    choosing_day = State()
    choosing_time = State()


@router.message(Command("set_reminder"))
async def set_reminder(message: Message, state: FSMContext):
    user = await db.get_user(message.from_user.id)
    if not user or user.role != "trainer":
        await message.answer("❌ Эта команда доступна только тренерам.")
        return

    days = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=day, callback_data=f"day_{i}")]
            for i, day in enumerate(days)
        ]
    )

    await message.answer(
        "📅 Выберите день недели для напоминания:",
        reply_markup=keyboard
    )
    await state.set_state(ReminderStates.choosing_day)


@router.callback_query(StateFilter(ReminderStates.choosing_day), F.data.startswith("day_"))
async def process_day_selection(callback: CallbackQuery, state: FSMContext):
    day = int(callback.data.split("_")[1])
    await state.update_data(day=day)

    await callback.message.edit_text(
        f"✅ Выбран день: {['Пн','Вт','Ср','Чт','Пт','Сб','Вс'][day]}\n\n"
        f"🕐 Введите время в формате ЧЧ:ММ (например, 10:00):"
    )
    await state.set_state(ReminderStates.choosing_time)
    await callback.answer()


@router.message(StateFilter(ReminderStates.choosing_time))
async def process_time_selection(message: Message, state: FSMContext):
    try:
        time_str = message.text.strip()
        datetime.strptime(time_str, "%H:%M")

        data = await state.get_data()
        day = data['day']

        user = await db.get_user(message.from_user.id)

        reminder = await db.create_reminder(user.id, day, time_str)

        global reminder_service
        if reminder_service:
            await reminder_service.schedule_reminder(user.id, day, time_str)

        days = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
        await message.answer(
            f"✅ Напоминание установлено!\n\n"
            f"📅 День: {days[day]}\n"
            f"🕐 Время: {time_str}\n\n"
            f"В указанное время все ваши ученики будут получать напоминание о замерах."
        )
        await state.clear()

    except ValueError:
        await message.answer(
            "❌ Неверный формат времени. Пожалуйста, используйте формат ЧЧ:ММ\n"
            "Пример: 10:00"
        )

@router.message(Command("my_reminders"))
async def my_reminders(message: Message):
    user = await db.get_user(message.from_user.id)
    if not user or user.role != "trainer":
        await message.answer("❌ Эта команда доступна только тренерам.")
        return

    reminders = await db.get_trainer_reminders(user.id)

    if not reminders:
        await message.answer(
            "📅 У вас пока нет настроенных напоминаний.\n\n"
            "Настройте напоминание: /set_reminder"
        )
        return

    days = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
    response = "📅 Ваши напоминания:\n\n"

    for reminder in reminders:
        response += f"• {days[reminder.day_of_week]}, {reminder.time.strftime('%H:%M')}\n"

    await message.answer(response)


# Функция для инициализации reminder_service из bot.py
def init_reminder_service(service):
    global reminder_service
    reminder_service = service