from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from app.services.db_service import DatabaseService
from app.keyboards.inline import (
    clients_list_keyboard, client_action_keyboard,
    confirm_delete_keyboard, client_info_keyboard
)

router = Router()
db = DatabaseService()


@router.message(Command("add_client"))
async def add_client(message: Message):
    user = db.get_user(message.from_user.id)
    if not user or user.role != "trainer":
        await message.answer("❌ Эта команда доступна только тренерам.")
        return

    args = message.text.split()
    if len(args) < 2:
        await message.answer(
            "❌ Использование: /add_client @username\n\n"
            "Пример: /add_client @john_doe"
        )
        return

    username = args[1].lstrip('@')
    client = db.get_user_by_username(username)

    if not client:
        await message.answer(f"❌ Пользователь @{username} не найден.")
        return

    if client.role != "client":
        await message.answer(f"❌ @{username} не является учеником.")
        return

    await message.bot.send_message(
        chat_id=client.telegram_id,
        text=f"🏋️ Тренер {user.full_name} хочет добавить вас в список учеников!\n\n"
             f"Вы согласны стать учеником этого тренера?",
        reply_markup=client_action_keyboard("accept_invite", user.id)
    )

    await message.answer(f"✅ Приглашение отправлено пользователю @{username}.")


@router.callback_query(F.data.startswith("accept_invite"))
async def accept_invite(callback: CallbackQuery):
    _, trainer_id = callback.data.split(":")
    trainer_id = int(trainer_id)

    client = db.get_user(callback.from_user.id)
    if not client:
        await callback.answer("❌ Сначала зарегистрируйтесь через /start")
        return

    success = db.add_client_to_trainer(trainer_id, client.id)

    if success:
        await callback.message.edit_text(
            "✅ Вы приняли приглашение! Теперь вы ученик этого тренера."
        )
        await callback.message.bot.send_message(
            chat_id=trainer_id,
            text=f"✅ Пользователь @{callback.from_user.username} принял ваше приглашение!"
        )
    else:
        await callback.message.edit_text(
            "❌ Вы уже являетесь учеником этого тренера."
        )

    await callback.answer()


@router.message(Command("my_clients"))
async def my_clients(message: Message):
    user = db.get_user(message.from_user.id)
    if not user or user.role != "trainer":
        await message.answer("❌ Эта команда доступна только тренерам.")
        return

    clients = db.get_trainer_clients(user.id)

    if not clients:
        await message.answer(
            "📋 У вас пока нет учеников.\n\n"
            "Добавьте ученика: /add_client @username"
        )
        return

    keyboard = clients_list_keyboard(clients)
    await message.answer(
        f"📋 Ваши ученики ({len(clients)}):",
        reply_markup=keyboard
    )


@router.callback_query(F.data.startswith("client_"))
async def client_action(callback: CallbackQuery):
    _, action, client_id = callback.data.split(":")
    client_id = int(client_id)

    if action == "info":
        await view_client_info(callback, client_id)
    elif action == "measurements":
        await view_client_measurements(callback, client_id)
    elif action == "chart":
        await view_client_chart(callback, client_id)
    elif action == "report":
        await generate_client_report(callback, client_id)
    elif action == "delete":
        await confirm_delete_client(callback, client_id)

    await callback.answer()


async def view_client_info(callback: CallbackQuery, client_id: int):
    client = db.get_user(client_id)
    if not client:
        await callback.message.answer("❌ Ученик не найден.")
        return

    text = f"👤 **{client.full_name}**\n\n"
    text += f"📱 Username: @{client.username}\n"
    text += f"🎂 Возраст: {client.age} лет\n"
    text += f"📏 Рост: {client.height} см\n"
    text += f"🎯 Цель: {client.goal}\n"

    await callback.message.answer(text, parse_mode="Markdown")


async def view_client_measurements(callback: CallbackQuery, client_id: int):
    client = db.get_user(client_id)
    if not client:
        await callback.message.answer("❌ Ученик не найден.")
        return

    measurements = db.get_measurements(client_id, days=30)

    if not measurements:
        await callback.message.answer(
            f"📊 У ученика {client.full_name} пока нет замеров."
        )
        return

    last = measurements[-1]
    text = f"📊 **Последние замеры {client.full_name}:**\n\n"
    text += f"📅 Дата: {last.measured_at.strftime('%d/%m/%Y %H:%M')}\n"
    if last.weight: text += f"⚖️ Вес: {last.weight:.1f} кг\n"
    if last.waist: text += f"📏 Талия: {last.waist:.1f} см\n"
    if last.hips: text += f"📏 Бедра: {last.hips:.1f} см\n"
    if last.chest: text += f"📏 Грудь: {last.chest:.1f} см\n"
    if last.biceps: text += f"💪 Бицепс: {last.biceps:.1f} см\n"

    await callback.message.answer(text, parse_mode="Markdown")


async def view_client_chart(callback: CallbackQuery, client_id: int):
    from app.services.chart_service import ChartService

    measurements = db.get_measurements(client_id, days=30)

    if len(measurements) < 2:
        await callback.message.answer(
            "❌ Недостаточно данных для построения графика. Нужно минимум 2 замера."
        )
        return

    chart_service = ChartService()
    chart_path = await chart_service.generate_stats_chart(client_id, measurements)

    if chart_path:
        await callback.message.answer_document(
            document=open(chart_path, 'rb'),
            caption=f"📊 График прогресса ученика"
        )
    else:
        await callback.message.answer("❌ Ошибка при генерации графика.")


async def generate_client_report(callback: CallbackQuery, client_id: int):
    from app.services.pdf_service import PDFService
    from app.services.chart_service import ChartService

    client = db.get_user(client_id)
    if not client:
        await callback.message.answer("❌ Ученик не найден.")
        return

    measurements = db.get_measurements(client_id, days=28)

    chart_service = ChartService()
    chart_path = await chart_service.generate_report_chart(client_id, measurements)

    pdf_service = PDFService()
    pdf_path = await pdf_service.generate_client_report(
        client_id, client, measurements, chart_path
    )

    if pdf_path:
        await callback.message.answer_document(
            document=open(pdf_path, 'rb'),
            caption=f"📄 Отчет по ученику {client.full_name}"
        )
    else:
        await callback.message.answer("❌ Ошибка при генерации отчета.")


async def confirm_delete_client(callback: CallbackQuery, client_id: int):
    await callback.message.edit_text(
        "❓ Вы уверены, что хотите удалить этого ученика?",
        reply_markup=confirm_delete_keyboard(client_id)
    )


@router.callback_query(F.data.startswith("delete_confirm"))
async def delete_client_confirm(callback: CallbackQuery):
    _, client_id = callback.data.split(":")
    client_id = int(client_id)

    user = db.get_user(callback.from_user.id)
    if not user:
        await callback.answer("❌ Ошибка аутентификации.")
        return

    db.remove_client_from_trainer(user.id, client_id)

    await callback.message.edit_text(
        "✅ Ученик удален из вашего списка."
    )
    await callback.answer()


@router.message(Command("delete_client"))
async def delete_client(message: Message):
    user = db.get_user(message.from_user.id)
    if not user or user.role != "trainer":
        await message.answer("❌ Эта команда доступна только тренерам.")
        return

    args = message.text.split()
    if len(args) < 2:
        await message.answer(
            "❌ Использование: /delete_client @username\n\n"
            "Пример: /delete_client @john_doe"
        )
        return

    username = args[1].lstrip('@')
    client = db.get_user_by_username(username)

    if not client:
        await message.answer(f"❌ Пользователь @{username} не найден.")
        return

    clients = db.get_trainer_clients(user.id)
    if client.id not in [c.id for c in clients]:
        await message.answer(f"❌ @{username} не является вашим учеником.")
        return

    db.remove_client_from_trainer(user.id, client.id)
    await message.answer(f"✅ Ученик @{username} удален из вашего списка.")

    await message.bot.send_message(
        chat_id=client.telegram_id,
        text=f"ℹ️ Тренер {user.full_name} удалил вас из списка учеников."
    )


@router.message(Command("report"))
async def report_command(message: Message):
    user = db.get_user(message.from_user.id)
    if not user or user.role != "trainer":
        await message.answer("❌ Эта команда доступна только тренерам.")
        return

    args = message.text.split()
    if len(args) < 2:
        await message.answer(
            "❌ Использование: /report @username\n\n"
            "Пример: /report @john_doe"
        )
        return

    username = args[1].lstrip('@')
    client = db.get_user_by_username(username)

    if not client:
        await message.answer(f"❌ Пользователь @{username} не найден.")
        return

    clients = db.get_trainer_clients(user.id)
    if client.id not in [c.id for c in clients]:
        await message.answer(f"❌ @{username} не является вашим учеником.")
        return

    measurements = db.get_measurements(client.id, days=28)

    from app.services.pdf_service import PDFService
    from app.services.chart_service import ChartService

    chart_service = ChartService()
    chart_path = await chart_service.generate_report_chart(client.id, measurements)

    pdf_service = PDFService()
    pdf_path = await pdf_service.generate_client_report(
        client.id, client, measurements, chart_path
    )

    if pdf_path:
        await message.answer_document(
            document=open(pdf_path, 'rb'),
            caption=f"📄 Отчет по ученику {client.full_name}"
        )
    else:
        await message.answer("❌ Ошибка при генерации отчета.")
