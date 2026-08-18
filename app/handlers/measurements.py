from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, BufferedInputFile
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.enums import ParseMode
from datetime import datetime
from app.services.db_service import DatabaseService
from app.services.chart_service import ChartService
from app.models import UserRole
from app.keyboards.inline import get_cancel_keyboard, get_back_keyboard, get_stats_period_keyboard
from app.utils.logger import get_logger
import traceback

logger = get_logger(__name__)
router = Router()
db = DatabaseService()
chart_service = ChartService()


class MeasurementStates(StatesGroup):
    weight = State()
    waist = State()
    hips = State()
    chest = State()
    biceps = State()


# ============================================================
#  КОМАНДА /set_measurements
# ============================================================

@router.message(Command("set_measurements"))
async def start_measurements(message: Message, state: FSMContext):
    try:
        user = db.get_user_by_telegram(message.from_user.id)
        if not user:
            await message.answer(
                "❌ Вы не зарегистрированы. Используйте /start.",
                reply_markup=get_cancel_keyboard()
            )
            return

        if user.role != UserRole.CLIENT:
            await message.answer("❌ Эта команда доступна только ученикам.")
            return

        await state.clear()

        last_measurement = db.get_last_measurement(user.id)
        last_text = ""
        if last_measurement:
            last_text = (
                f"\n📋 <i>Последний замер: {last_measurement.measured_at.strftime('%d.%m.%Y')}</i>\n"
                f"⚖️ Вес: {last_measurement.weight or '—'} кг\n"
            )

        await message.answer(
            f"📝 <b>Введите замеры</b>\n\n"
            f"На каждом шаге введите значение или отправьте 'пропустить'.\n"
            f"{last_text}\n"
            f"⚖️ <b>Шаг 1/5</b>: Введите вес (в кг):",
            parse_mode=ParseMode.HTML,
            reply_markup=get_cancel_keyboard()
        )
        await state.set_state(MeasurementStates.weight)

    except Exception as e:
        logger.error(f"Error in start_measurements: {e}")
        await message.answer("❌ Ошибка при начале ввода замеров.")


# ============================================================
#  ОБРАБОТКА ЗАМЕРОВ
# ============================================================

@router.message(StateFilter(MeasurementStates.weight))
async def process_weight(message: Message, state: FSMContext):
    try:
        if message.text == "❌ Отмена":
            await cancel_measurements(message, state)
            return

        value = await process_measurement_value(message, "weight")
        if value is None:
            return

        await state.update_data(weight=value)
        await message.answer(
            "📏 <b>Шаг 2/5</b>: Введите обхват талии (в см):\n"
            "<i>Или отправьте 'пропустить'</i>",
            parse_mode=ParseMode.HTML,
            reply_markup=get_cancel_keyboard()
        )
        await state.set_state(MeasurementStates.waist)

    except Exception as e:
        logger.error(f"Error in process_weight: {e}")
        await message.answer("❌ Ошибка при обработке веса.")


@router.message(StateFilter(MeasurementStates.waist))
async def process_waist(message: Message, state: FSMContext):
    try:
        if message.text == "❌ Отмена":
            await cancel_measurements(message, state)
            return

        value = await process_measurement_value(message, "waist")
        if value is None:
            return

        await state.update_data(waist=value)
        await message.answer(
            "📏 <b>Шаг 3/5</b>: Введите обхват бедер (в см):\n"
            "<i>Или отправьте 'пропустить'</i>",
            parse_mode=ParseMode.HTML,
            reply_markup=get_cancel_keyboard()
        )
        await state.set_state(MeasurementStates.hips)

    except Exception as e:
        logger.error(f"Error in process_waist: {e}")
        await message.answer("❌ Ошибка при обработке талии.")


@router.message(StateFilter(MeasurementStates.hips))
async def process_hips(message: Message, state: FSMContext):
    try:
        if message.text == "❌ Отмена":
            await cancel_measurements(message, state)
            return

        value = await process_measurement_value(message, "hips")
        if value is None:
            return

        await state.update_data(hips=value)
        await message.answer(
            "📏 <b>Шаг 4/5</b>: Введите обхват груди (в см):\n"
            "<i>Или отправьте 'пропустить'</i>",
            parse_mode=ParseMode.HTML,
            reply_markup=get_cancel_keyboard()
        )
        await state.set_state(MeasurementStates.chest)

    except Exception as e:
        logger.error(f"Error in process_hips: {e}")
        await message.answer("❌ Ошибка при обработке бедер.")


@router.message(StateFilter(MeasurementStates.chest))
async def process_chest(message: Message, state: FSMContext):
    try:
        if message.text == "❌ Отмена":
            await cancel_measurements(message, state)
            return

        value = await process_measurement_value(message, "chest")
        if value is None:
            return

        await state.update_data(chest=value)
        await message.answer(
            "💪 <b>Шаг 5/5</b>: Введите обхват бицепса (в см):\n"
            "<i>Или отправьте 'пропустить'</i>",
            parse_mode=ParseMode.HTML,
            reply_markup=get_cancel_keyboard()
        )
        await state.set_state(MeasurementStates.biceps)

    except Exception as e:
        logger.error(f"Error in process_chest: {e}")
        await message.answer("❌ Ошибка при обработке груди.")


@router.message(StateFilter(MeasurementStates.biceps))
async def process_biceps(message: Message, state: FSMContext):
    try:
        if message.text == "❌ Отмена":
            await cancel_measurements(message, state)
            return

        value = await process_measurement_value(message, "biceps")
        if value is None:
            return

        await state.update_data(biceps=value)

        data = await state.get_data()

        measurement_data = {}
        fields = ['weight', 'waist', 'hips', 'chest', 'biceps']
        field_labels = {
            'weight': 'Вес',
            'waist': 'Талия',
            'hips': 'Бедра',
            'chest': 'Грудь',
            'biceps': 'Бицепс'
        }
        field_emojis = {
            'weight': '⚖️',
            'waist': '📏',
            'hips': '📏',
            'chest': '📏',
            'biceps': '💪'
        }

        for field in fields:
            if data.get(field) is not None:
                measurement_data[field] = data[field]

        if not measurement_data:
            await message.answer(
                "❌ Вы должны ввести хотя бы один замер.",
                reply_markup=get_back_keyboard()
            )
            await state.clear()
            return

        user = db.get_user_by_telegram(message.from_user.id)
        db.create_measurement(user.id, measurement_data)
        logger.info(f"✅ Measurements saved for user {user.id}: {len(measurement_data)} fields")

        response = "✅ <b>Замеры сохранены!</b>\n\n"
        for field, value in measurement_data.items():
            response += f"{field_emojis.get(field, '📊')} {field_labels.get(field, field)}: <b>{value:.1f}</b>\n"

        response += "\n📊 Для просмотра прогресса используйте /my_progress"

        await message.answer(
            response,
            parse_mode=ParseMode.HTML,
            reply_markup=get_back_keyboard()
        )
        await state.clear()

    except Exception as e:
        logger.error(f"Error in process_biceps: {e}")
        await message.answer("❌ Ошибка при сохранении замеров.")
        await state.clear()


# ============================================================
#  ВСПОМОГАТЕЛЬНАЯ ФУНКЦИЯ
# ============================================================

async def process_measurement_value(message: Message, field: str):
    text = message.text.strip().lower()

    if text == "пропустить":
        return None

    text = text.replace(',', '.')

    try:
        value = float(text)

        if value <= 0:
            await message.answer(
                "❌ Значение должно быть больше 0. Пожалуйста, введите корректное число или 'пропустить'.",
                reply_markup=get_cancel_keyboard()
            )
            return None

        if field == "weight" and (value < 20 or value > 500):
            await message.answer(
                "❌ Вес должен быть от 20 до 500 кг. Пожалуйста, введите корректное значение или 'пропустить'.",
                reply_markup=get_cancel_keyboard()
            )
            return None

        if field in ["waist", "hips", "chest", "biceps"] and (value < 10 or value > 300):
            await message.answer(
                f"❌ Значение должно быть от 10 до 300 см. Пожалуйста, введите корректное значение или 'пропустить'.",
                reply_markup=get_cancel_keyboard()
            )
            return None

        return round(value, 1)

    except ValueError:
        await message.answer(
            "❌ Пожалуйста, введите корректное число (например, 75.5) или 'пропустить'.",
            reply_markup=get_cancel_keyboard()
        )
        return None


async def cancel_measurements(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "❌ Ввод замеров отменён.",
        reply_markup=get_back_keyboard()
    )


# ============================================================
#  КОМАНДА /my_progress
# ============================================================

@router.message(Command("my_progress"))
async def my_progress(message: Message):
    try:
        user = db.get_user_by_telegram(message.from_user.id)
        if not user:
            await message.answer("❌ Вы не зарегистрированы. Используйте /start.")
            return

        if user.role != UserRole.CLIENT:
            await message.answer("❌ Эта команда доступна только ученикам.")
            return

        measurements = db.get_measurements(user.id, days=30)

        if not measurements:
            await message.answer(
                "📊 У вас пока нет замеров.\n\n"
                "Внесите первый замер: /set_measurements",
                reply_markup=get_back_keyboard()
            )
            return

        sorted_measurements = sorted(measurements, key=lambda m: m.measured_at)
        last = sorted_measurements[-1]
        first = sorted_measurements[0]

        response = f"📊 <b>Ваш прогресс</b>\n\n"
        response += f"📅 Период: {first.measured_at.strftime('%d.%m.%Y')} — {last.measured_at.strftime('%d.%m.%Y')}\n"
        response += f"📊 Всего замеров: {len(measurements)}\n\n"

        response += "📝 <b>Текущие замеры:</b>\n"
        if last.weight:
            response += f"⚖️ Вес: <b>{last.weight:.1f}</b> кг\n"
        if last.waist:
            response += f"📏 Талия: <b>{last.waist:.1f}</b> см\n"
        if last.hips:
            response += f"📏 Бедра: <b>{last.hips:.1f}</b> см\n"
        if last.chest:
            response += f"📏 Грудь: <b>{last.chest:.1f}</b> см\n"
        if last.biceps:
            response += f"💪 Бицепс: <b>{last.biceps:.1f}</b> см\n"

        if len(measurements) >= 2:
            response += "\n📈 <b>Изменения за период:</b>\n"

            field_labels = {
                'weight': ('Вес', 'кг'),
                'waist': ('Талия', 'см'),
                'hips': ('Бедра', 'см'),
                'chest': ('Грудь', 'см'),
                'biceps': ('Бицепс', 'см')
            }

            for field, (label, unit) in field_labels.items():
                first_val = getattr(first, field)
                last_val = getattr(last, field)
                if first_val is not None and last_val is not None:
                    change = last_val - first_val
                    emoji = "⬆️" if change > 0 else "⬇️" if change < 0 else "➡️"
                    response += f"{emoji} {label}: <b>{change:+.1f}</b> {unit}\n"

        try:
            chart_data = await chart_service.generate_simple_chart(measurements)
            if chart_data:
                photo = BufferedInputFile(chart_data, filename=f"progress_{user.id}.png")
                await message.answer_photo(
                    photo=photo,
                    caption=f"📊 График прогресса для {user.full_name or 'ученика'}"
                )
        except Exception as e:
            logger.error(f"Error generating chart in my_progress: {e}")

        await message.answer(
            response,
            parse_mode=ParseMode.HTML,
            reply_markup=get_back_keyboard()
        )

    except Exception as e:
        logger.error(f"Error in my_progress: {e}\n{traceback.format_exc()}")
        await message.answer("❌ Ошибка при загрузке прогресса.")
