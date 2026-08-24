from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.enums import ParseMode
from datetime import datetime
from app.services.db_service import DatabaseService
from app.services.reminder_service import ReminderService
from app.keyboards.inline import (
    get_cancel_keyboard,
    get_back_keyboard,
    get_days_of_week_keyboard,
    get_reminder_actions_keyboard
)
from app.models import UserRole
from app.utils.logger import get_logger
import traceback

logger = get_logger(__name__)
router = Router()
db = DatabaseService()

_reminder_service = None


class ReminderStates(StatesGroup):
    choosing_day = State()
    choosing_time = State()


def init_reminder_service(service: ReminderService):
    global _reminder_service
    _reminder_service = service
    logger.info("✅ Reminder service initialized in reminders.py")


def get_reminder_service() -> ReminderService:
    if _reminder_service is None:
        logger.warning("⚠️ Reminder service not initialized!")
    return _reminder_service


# ============================================================
#  КОМАНДА /set_reminder
# ============================================================

@router.message(Command("set_reminder"))
async def set_reminder(message: Message, state: FSMContext):
    try:
        user = db.get_user_by_telegram(message.from_user.id)
        if not user:
            await message.answer("❌ Вы не зарегистрированы. Используйте /start.")
            return

        if user.role != UserRole.TRAINER:
            await message.answer("❌ Эта команда доступна только тренерам.")
            return

        await message.answer(
            "📅 Выберите день недели для напоминания:\n\n"
            "<i>В этот день ваши ученики будут получать напоминание о замерах.</i>",
            parse_mode=ParseMode.HTML,
            reply_markup=get_days_of_week_keyboard()
        )
        await state.set_state(ReminderStates.choosing_day)

    except Exception as e:
        logger.error(f"Error in set_reminder: {e}")
        await message.answer("❌ Ошибка при настройке напоминания.")


# ============================================================
#  ВЫБОР ДНЯ
# ============================================================

@router.callback_query(StateFilter(ReminderStates.choosing_day), F.data.startswith("reminder_day_"))
async def process_day_selection(callback: CallbackQuery, state: FSMContext):
    try:
        logger.info(f"📥 [reminder_day_] data: {callback.data}")
        
        day_str = callback.data.split("_")[2]
        logger.info(f"📥 day_str: {day_str}")

        if day_str == "daily":
            day = None
            day_name = "📅 Ежедневно"
        else:
            day = int(day_str)
            days = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
            day_name = days[day]

        await state.update_data(day=day)

        await callback.message.edit_text(
            f"✅ Выбран день: <b>{day_name}</b>\n\n"
            f"🕐 Теперь выберите время или введите в формате <b>ЧЧ:ММ</b> (например, 10:00):",
            parse_mode=ParseMode.HTML,
            reply_markup=get_time_selection_keyboard()
        )
        await state.set_state(ReminderStates.choosing_time)
        await callback.answer()

    except ValueError:
        await callback.answer("❌ Неверный формат дня", show_alert=True)
    except Exception as e:
        logger.error(f"Error in process_day_selection: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


# ============================================================
#  ВЫБОР ВРЕМЕНИ
# ============================================================

@router.message(StateFilter(ReminderStates.choosing_time))
async def process_time_selection(message: Message, state: FSMContext):
    try:
        logger.info(f"📥 [process_time_selection] text: {message.text}")
        
        time_str = message.text.strip()

        try:
            datetime.strptime(time_str, "%H:%M")
        except ValueError:
            await message.answer(
                "❌ Неверный формат времени.\n"
                "Пожалуйста, используйте формат <b>ЧЧ:ММ</b>\n"
                "Пример: 10:00",
                parse_mode=ParseMode.HTML,
                reply_markup=get_cancel_keyboard()
            )
            return

        data = await state.get_data()
        day = data.get('day')

        user = db.get_user_by_telegram(message.from_user.id)
        if not user:
            await message.answer("❌ Пользователь не найден.")
            await state.clear()
            return

        logger.info(f"📝 Creating reminder: trainer_id={user.id}, day={day}, time={time_str}")
        
        reminder = db.create_reminder(user.id, day, time_str)
        logger.info(f"✅ Reminder created: {reminder}")

        if not reminder:
            await message.answer(
                "❌ Не удалось создать напоминание. Попробуйте позже.",
                reply_markup=get_cancel_keyboard()
            )
            await state.clear()
            return

        reminder_service = get_reminder_service()
        logger.info(f"📝 Reminder service: {reminder_service}")
        
        if reminder_service:
            try:
                await reminder_service.schedule_reminder(
                    trainer_id=user.id,
                    day_of_week=day,
                    time_str=time_str,
                    reminder_id=reminder.id
                )
                logger.info(f"✅ Reminder scheduled: user={user.id}, day={day}, time={time_str}")
            except Exception as e:
                logger.error(f"Failed to schedule reminder: {e}")
                await message.answer(
                    "⚠️ Напоминание создано в БД, но не запланировано.\n"
                    "Оно будет восстановлено при перезапуске бота."
                )
        else:
            logger.error("❌ Reminder service is None!")
            await message.answer(
                "⚠️ Сервис напоминаний не инициализирован.\n"
                "Напоминание сохранено в БД и будет активировано позже."
            )

        day_name = get_day_name(day)
        await message.answer(
            f"✅ <b>Напоминание установлено!</b>\n\n"
            f"📅 День: {day_name}\n"
            f"🕐 Время: {time_str}\n\n"
            f"💡 В указанное время все ваши ученики будут получать напоминание о замерах.",
            parse_mode=ParseMode.HTML,
            reply_markup=get_back_keyboard()
        )
        await state.clear()

    except Exception as e:
        logger.error(f"❌ Error in process_time_selection: {e}\n{traceback.format_exc()}")
        await message.answer(f"❌ Ошибка при создании напоминания: {str(e)[:200]}", reply_markup=get_cancel_keyboard())
        await state.clear()


@router.callback_query(StateFilter(ReminderStates.choosing_time), F.data.startswith("reminder_time_"))
async def process_time_callback(callback: CallbackQuery, state: FSMContext):
    try:
        logger.info(f"📥 [reminder_time_] data: {callback.data}")
        
        time_str = callback.data.split("_")[2]

        if time_str == "custom":
            await callback.message.edit_text(
                "🕐 Введите время в формате <b>ЧЧ:ММ</b>\n"
                "Пример: 10:00",
                parse_mode=ParseMode.HTML,
                reply_markup=get_cancel_keyboard()
            )
            await callback.answer()
            return

        await callback.message.edit_text(
            f"✅ Выбрано время: <b>{time_str}</b>\n\n"
            "Подтверждаю создание напоминания...",
            parse_mode=ParseMode.HTML
        )

        # Имитируем ввод текста
        await process_time_selection(
            Message(
                message_id=callback.message.message_id,
                from_user=callback.from_user,
                chat=callback.message.chat,
                text=time_str
            ),
            state
        )
        await callback.answer()

    except Exception as e:
        logger.error(f"Error in process_time_callback: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


# ============================================================
#  ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================

def get_day_name(day: int) -> str:
    days = {
        0: "Понедельник",
        1: "Вторник",
        2: "Среда",
        3: "Четверг",
        4: "Пятница",
        5: "Суббота",
        6: "Воскресенье",
        None: "📅 Ежедневно"
    }
    return days.get(day, "Неизвестно")


def get_time_selection_keyboard() -> InlineKeyboardMarkup:
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


# ============================================================
#  /my_reminders
# ============================================================

@router.message(Command("my_reminders"))
async def my_reminders(message: Message):
    try:
        user = db.get_user_by_telegram(message.from_user.id)
        if not user:
            await message.answer("❌ Вы не зарегистрированы. Используйте /start.")
            return

        if user.role != UserRole.TRAINER:
            await message.answer("❌ Эта команда доступна только тренерам.")
            return

        reminders = db.get_trainer_reminders(user.id)

        if not reminders:
            await message.answer(
                "📅 У вас пока нет настроенных напоминаний.\n\n"
                "Настройте напоминание: /set_reminder"
            )
            return

        response = "📅 <b>Ваши напоминания:</b>\n\n"

        for i, reminder in enumerate(reminders, 1):
            day_name = get_day_name(reminder.day_of_week)
            status = "✅ Активно" if reminder.is_active else "⏸️ Приостановлено"
            response += (
                f"{i}. {day_name}, {reminder.time.strftime('%H:%M')} "
                f"— {status}\n"
            )

        response += "\n<i>Нажмите на напоминание для управления.</i>"

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=f"{get_day_name(r.day_of_week)} {r.time.strftime('%H:%M')}",
                        callback_data=f"reminder_manage_{r.id}"
                    )
                ]
                for r in reminders[:10]
            ] + [
                [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")]
            ]
        )

        await message.answer(response, parse_mode=ParseMode.HTML, reply_markup=keyboard)

    except Exception as e:
        logger.error(f"Error in my_reminders: {e}")
        await message.answer("❌ Ошибка при загрузке напоминаний.")


@router.callback_query(F.data.startswith("reminder_manage_"))
async def manage_reminder(callback: CallbackQuery):
    try:
        reminder_id = int(callback.data.split("_")[2])
        reminder = db.get_reminder(reminder_id)

        if not reminder:
            await callback.answer("❌ Напоминание не найдено", show_alert=True)
            return

        user = db.get_user_by_telegram(callback.from_user.id)
        if not user or reminder.trainer_id != user.id:
            await callback.answer("❌ Это не ваше напоминание", show_alert=True)
            return

        day_name = get_day_name(reminder.day_of_week)
        status = "✅ Активно" if reminder.is_active else "⏸️ Приостановлено"

        text = (
            f"📅 <b>Управление напоминанием</b>\n\n"
            f"📅 День: {day_name}\n"
            f"🕐 Время: {reminder.time.strftime('%H:%M')}\n"
            f"📊 Статус: {status}\n"
            f"📋 Создано: {reminder.created_at.strftime('%d.%m.%Y')}\n\n"
            f"<i>Выберите действие:</i>"
        )

        await callback.message.edit_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=get_reminder_actions_keyboard(reminder.id, reminder.is_active)
        )
        await callback.answer()

    except Exception as e:
        logger.error(f"Error in manage_reminder: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@router.callback_query(F.data.startswith("toggle_reminder_"))
async def toggle_reminder(callback: CallbackQuery):
    try:
        reminder_id = int(callback.data.split("_")[2])
        reminder = db.get_reminder(reminder_id)

        if not reminder:
            await callback.answer("❌ Напоминание не найдено", show_alert=True)
            return

        new_status = not reminder.is_active
        db.update_reminder(reminder_id, is_active=new_status)

        reminder_service = get_reminder_service()
        if reminder_service:
            if new_status:
                await reminder_service.schedule_reminder(
                    trainer_id=reminder.trainer_id,
                    day_of_week=reminder.day_of_week,
                    time_str=reminder.time.strftime("%H:%M"),
                    reminder_id=reminder.id
                )
            else:
                job_id = f"reminder_{reminder.id}"
                await reminder_service.remove_reminder(job_id)

        status = "включено" if new_status else "выключено"
        await callback.answer(f"✅ Напоминание {status}")

        await manage_reminder(callback)

    except Exception as e:
        logger.error(f"Error in toggle_reminder: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@router.callback_query(F.data.startswith("delete_reminder_"))
async def delete_reminder(callback: CallbackQuery):
    try:
        reminder_id = int(callback.data.split("_")[2])
        reminder = db.get_reminder(reminder_id)

        if not reminder:
            await callback.answer("❌ Напоминание не найдено", show_alert=True)
            return

        reminder_service = get_reminder_service()
        if reminder_service:
            job_id = f"reminder_{reminder.id}"
            await reminder_service.remove_reminder(job_id)

        db.delete_reminder(reminder_id)

        await callback.answer("✅ Напоминание удалено")
        await callback.message.edit_text(
            "✅ Напоминание успешно удалено.",
            reply_markup=get_back_keyboard()
        )

    except Exception as e:
        logger.error(f"Error in delete_reminder: {e}")
        await callback.answer("❌ Ошибка при удалении", show_alert=True)


@router.callback_query(F.data == "back_to_reminders")
async def back_to_reminders(callback: CallbackQuery):
    try:
        fake_message = Message(
            message_id=callback.message.message_id,
            from_user=callback.from_user,
            chat=callback.message.chat,
            text="/my_reminders"
        )
        await my_reminders(fake_message)
        await callback.answer()

    except Exception as e:
        logger.error(f"Error in back_to_reminders: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)
