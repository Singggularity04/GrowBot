"""Booking flow — allows choice between in-Telegram calendar or Dikidi link."""

from datetime import datetime
from pathlib import Path

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

import database as db
from config import ADMIN_ID, CHANNEL_ID, now_moscow
from texts import SERVICES, PRE_BOOKING
from keyboards import (
    services_kb, service_detail_kb, booking_choice_kb, 
    calendar_kb, time_slots_kb, confirm_booking_kb, back_to_menu_kb
)
from scheduler import schedule_reminder

# Only import if subscription handler is enabled
try:
    from handlers.subscription import check_subscription
except ImportError:
    async def check_subscription(bot, user_id): return True

router = Router()

# Success image shown after booking confirmation
SUCCESS_IMAGE = Path(__file__).resolve().parent.parent / "images" / "success.jpeg"


# =========================================================================
# GROW BOT EXPLICIT FUNNEL ROUTING (Dikidi choice triggers this)
# =========================================================================

@router.callback_query(F.data == "quick_book")
async def show_services(callback: CallbackQuery) -> None:
    """Show list of available services."""
    await callback.answer()
    await db.log_interaction(callback.from_user.id, "view_services")
    await callback.message.edit_text(
        "⚡ <b>Быстрая запись</b>\n\nВыберите услугу 👇",
        reply_markup=services_kb(),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("svc:"))
async def show_service_detail(callback: CallbackQuery) -> None:
    """Show service details with booking CTA."""
    service_key = callback.data.split(":")[1]
    service = SERVICES.get(service_key)
    if not service:
        await callback.answer("Услуга не найдена", show_alert=True)
        return

    await callback.answer()
    await db.log_interaction(callback.from_user.id, f"view_{service_key}")
    await callback.message.edit_text(
        service["detail"],
        reply_markup=service_detail_kb(service_key),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("pre_book:"))
async def pre_booking(callback: CallbackQuery) -> None:
    """Motivational message before booking choice."""
    await callback.answer()
    await db.log_interaction(callback.from_user.id, "pre_book")
    await callback.message.edit_text(
        PRE_BOOKING, 
        reply_markup=booking_choice_kb(), 
        parse_mode="HTML"
    )


# =========================================================================
# TELEGRAM BOOKING FLOW (Adapted from NailsBot)
# =========================================================================

class BookingStates(StatesGroup):
    select_date = State()
    select_time = State()
    enter_name = State()
    enter_phone = State()
    confirm = State()


# --------------- Start booking ---------------

@router.callback_query(F.data == "booking_telegram")
async def booking_start(callback: CallbackQuery, state: FSMContext):
    """Open the calendar for date selection."""
    # Ensure they are subscribed if required
    if not await check_subscription(callback.bot, callback.from_user.id):
        from keyboards import subscription_kb
        await callback.message.edit_text(
            "Для записи необходимо подписаться на наш канал: 👇",
            reply_markup=subscription_kb(),
        )
        await callback.answer()
        return

    # Check if user already has a booking
    existing = await db.get_booking_by_user(callback.from_user.id)
    if existing:
        await callback.answer(
            "❗ У вас уже есть активная запись. Сначала отмените её через меню.",
            show_alert=True,
        )
        return

    await state.set_state(BookingStates.select_date)

    now = now_moscow()
    available = await db.get_available_dates()
    text = "📅 <b>Выберите дату в Telegram-календаре:</b>"
    markup = calendar_kb(now.year, now.month, available)

    # If triggered from a photo message, delete it and send new text message
    if callback.message.photo:
        await callback.message.delete()
        await callback.message.answer(text, reply_markup=markup, parse_mode="HTML")
    else:
        await callback.message.edit_text(text, reply_markup=markup, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("booking_back:"))
async def booking_back(callback: CallbackQuery, state: FSMContext):
    """Return to calendar preserving the month the user was looking at."""
    existing = await db.get_booking_by_user(callback.from_user.id)
    if existing:
        await callback.answer(
            "❗ У вас уже есть активная запись. Сначала отмените её.",
            show_alert=True,
        )
        return

    _, ym = callback.data.split(":")
    year, month = map(int, ym.split("-"))

    await state.set_state(BookingStates.select_date)
    available = await db.get_available_dates()
    
    text = "📅 <b>Выберите дату в Telegram-календаре:</b>"
    markup = calendar_kb(year, month, available)
    
    await callback.message.edit_text(text, reply_markup=markup, parse_mode="HTML")
    await callback.answer()


# --------------- Calendar navigation ---------------

@router.callback_query(F.data.startswith("cal_nav:"))
async def calendar_navigate(callback: CallbackQuery):
    """Switch month in the calendar."""
    _, ym = callback.data.split(":")
    year, month = map(int, ym.split("-"))
    available = await db.get_available_dates()
    await callback.message.edit_reply_markup(
        reply_markup=calendar_kb(year, month, available)
    )
    await callback.answer()


@router.callback_query(F.data == "ignore")
async def ignore_callback(callback: CallbackQuery):
    """Silently ignore non-clickable calendar cells."""
    await callback.answer()


# --------------- Date selected ---------------

@router.callback_query(F.data.startswith("cal_date:"))
async def date_selected(callback: CallbackQuery, state: FSMContext):
    """User picked a date — show available time slots."""
    _, date_str = callback.data.split(":")
    slots = await db.get_available_times(date_str)

    if not slots:
        await callback.answer("На эту дату нет свободных слотов.", show_alert=True)
        return

    await state.update_data(selected_date=date_str)
    await state.set_state(BookingStates.select_time)

    # Format date for display
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    display_date = dt.strftime("%d.%m.%Y")

    await callback.message.edit_text(
        f"🕐 <b>Свободное время на {display_date}:</b>\n\nВыберите удобное время:",
        reply_markup=time_slots_kb(slots, date_str),
        parse_mode="HTML",
    )
    await callback.answer()


# --------------- Time slot selected ---------------

@router.callback_query(F.data.startswith("slot:"))
async def slot_selected(callback: CallbackQuery, state: FSMContext):
    """User picked a time slot — ask for name."""
    _, slot_id_str = callback.data.split(":")
    slot_id = int(slot_id_str)

    slot = await db.get_slot_by_id(slot_id)
    if not slot or slot["is_booked"]:
        await callback.answer("Этот слот уже занят!", show_alert=True)
        return

    await state.update_data(slot_id=slot_id, selected_time=slot["time"])
    await state.set_state(BookingStates.enter_name)

    # Remove old inline message and any leftover reply keyboard
    await callback.message.delete()
    await callback.message.answer(
        "👤 <b>Введите ваше имя:</b>",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardRemove(),
    )
    await callback.answer()


# --------------- Name input ---------------

@router.message(BookingStates.enter_name, F.contact)
async def process_name_contact(message: Message, state: FSMContext):
    """User sent contact instead of name — extract both name and phone."""
    contact = message.contact
    name = contact.first_name or "Клиент"
    phone = contact.phone_number

    await state.update_data(client_name=name, client_phone=phone)
    await state.set_state(BookingStates.confirm)

    data = await state.get_data()

    # Guard: FSM data may be lost
    if "selected_date" not in data or "selected_time" not in data:
        await message.answer(
            "⚠️ Сессия устарела. Пожалуйста, начните запись заново.",
            reply_markup=ReplyKeyboardRemove(),
        )
        await message.answer("Вернуться в меню:", reply_markup=back_to_menu_kb())
        await state.clear()
        return

    dt = datetime.strptime(data["selected_date"], "%Y-%m-%d")
    display_date = dt.strftime("%d.%m.%Y")

    await message.answer(
        f"📋 <b>Подтвердите запись:</b>\n\n"
        f"📅 Дата: <b>{display_date}</b>\n"
        f"🕐 Время: <b>{data['selected_time']}</b>\n"
        f"👤 Имя: <b>{name}</b>\n"
        f"📱 Телефон: <b>{phone}</b>",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode="HTML",
    )
    await message.answer(
        "👇 Нажмите для подтверждения:",
        reply_markup=confirm_booking_kb(),
    )


@router.message(BookingStates.enter_name)
async def process_name(message: Message, state: FSMContext):
    """Save name, ask for phone."""
    if not message.text:
        await message.answer("❌ Пожалуйста, отправьте текстовое сообщение с вашим именем.")
        return
    name = message.text.strip()
    if len(name) < 2 or len(name) > 50:
        await message.answer("❌ Пожалуйста, введите корректное имя (2-50 символов).")
        return

    await state.update_data(client_name=name)
    await state.set_state(BookingStates.enter_phone)

    # Offer a quick "share contact" button
    contact_kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📱 Отправить номер", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
    await message.answer(
        "📱 <b>Отправьте номер телефона:</b>\n\n"
        "Нажмите кнопку ниже или введите вручную.",
        parse_mode="HTML",
        reply_markup=contact_kb,
    )


# --------------- Phone input ---------------

@router.message(BookingStates.enter_phone, F.contact)
async def process_contact(message: Message, state: FSMContext):
    """Handle shared contact — extract phone automatically."""
    phone = message.contact.phone_number
    await _save_phone_and_confirm(message, state, phone)


@router.message(BookingStates.enter_phone)
async def process_phone(message: Message, state: FSMContext):
    """Save manually entered phone."""
    if not message.text:
        await message.answer("❌ Пожалуйста, отправьте текстовое сообщение с вашим номером телефона.")
        return
    phone = message.text.strip()
    # Basic phone validation
    digits_only = "".join(c for c in phone if c.isdigit())
    if len(digits_only) < 10:
        await message.answer(
            "❌ Пожалуйста, введите корректный номер телефона (минимум 10 цифр)."
        )
        return

    await _save_phone_and_confirm(message, state, phone)


async def _save_phone_and_confirm(message: Message, state: FSMContext, phone: str):
    """Common logic: save phone and show confirmation."""
    await state.update_data(client_phone=phone)
    await state.set_state(BookingStates.confirm)

    data = await state.get_data()

    # Guard: FSM data may be lost after bot restart
    if "selected_date" not in data or "selected_time" not in data:
        await message.answer(
            "⚠️ Сессия устарела. Пожалуйста, начните запись заново.",
            reply_markup=ReplyKeyboardRemove(),
        )
        await message.answer("Вернуться в меню:", reply_markup=back_to_menu_kb())
        await state.clear()
        return

    dt = datetime.strptime(data["selected_date"], "%Y-%m-%d")
    display_date = dt.strftime("%d.%m.%Y")

    # Remove the reply keyboard and show inline confirmation
    await message.answer(
        f"📋 <b>Подтвердите запись:</b>\n\n"
        f"📅 Дата: <b>{display_date}</b>\n"
        f"🕐 Время: <b>{data['selected_time']}</b>\n"
        f"👤 Имя: <b>{data['client_name']}</b>\n"
        f"📱 Телефон: <b>{data['client_phone']}</b>",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode="HTML",
    )
    await message.answer(
        "👇 Нажмите для подтверждения:",
        reply_markup=confirm_booking_kb(),
    )


# --------------- Confirm booking ---------------

@router.callback_query(F.data == "confirm_booking")
async def confirm_booking(callback: CallbackQuery, state: FSMContext):
    """Finalize booking: save to DB, notify admin, post to channel."""
    data = await state.get_data()

    # Guard: FSM state may be lost after bot restart
    if "slot_id" not in data:
        await callback.message.edit_text(
            "⚠️ Сессия устарела. Пожалуйста, начните запись заново.",
            reply_markup=back_to_menu_kb(),
            parse_mode="HTML",
        )
        await state.clear()
        await callback.answer()
        return

    # Double-check slot availability (race condition protection)
    slot = await db.get_slot_by_id(data["slot_id"])
    if not slot or slot["is_booked"]:
        await callback.message.edit_text(
            "❌ К сожалению, этот слот уже занят. Попробуйте выбрать другое время.",
            reply_markup=back_to_menu_kb(),
            parse_mode="HTML",
        )
        await state.clear()
        await callback.answer()
        return

    # Save booking
    booking_id = await db.book_slot(
        user_id=callback.from_user.id,
        slot_id=data["slot_id"],
        name=data["client_name"],
        phone=data["client_phone"],
    )
    
    # Track the funnel conversion
    await db.mark_booked(callback.from_user.id)
    await db.log_interaction(callback.from_user.id, "telegram_booking_success")

    dt = datetime.strptime(data["selected_date"], "%Y-%m-%d")
    display_date = dt.strftime("%d.%m.%Y")

    # Confirm to user — send photo with details
    success_text = (
        f"✅ <b>Запись подтверждена!</b>\n\n"
        f"Спасибо, что выбираете нас ❤️\n"
        f"Вы записаны на <b>{display_date}</b> в <b>{data['selected_time']}</b>.\n\n"
        f"📍 Наша студия находится по адресу:\n"
        f"<b>г. Москва, улица Полярная 54, корпус 5</b>\n"
        f"(10 минут от станции метро 🚇 Медведково).\n\n"
        f"Мы обязательно напомним вам о записи!\n\n"
        f"Для отмены нажмите «📋 Мои записи» в меню."
    )
    
    await callback.message.delete()
    if SUCCESS_IMAGE.exists():
        photo = FSInputFile(str(SUCCESS_IMAGE))
        await callback.message.answer_photo(
            photo=photo,
            caption=success_text,
            reply_markup=back_to_menu_kb(),
            parse_mode="HTML",
        )
    else:
        await callback.message.answer(
            success_text,
            reply_markup=back_to_menu_kb(),
            parse_mode="HTML",
        )

    # Notify admin
    admin_text = (
        f"📌 <b>Новая запись (Телеграм)!</b>\n\n"
        f"👤 Имя: {data['client_name']}\n"
        f"📱 Телефон: {data['client_phone']}\n"
        f"📅 Дата: {display_date}\n"
        f"🕐 Время: {data['selected_time']}\n"
        f"🆔 Telegram ID: <code>{callback.from_user.id}</code>"
    )
    try:
        await callback.bot.send_message(ADMIN_ID, admin_text, parse_mode="HTML")
    except Exception:
        pass

    # Post to channel
    if CHANNEL_ID:
        channel_text = (
            f"📝 <b>Новая запись</b>\n\n"
            f"📅 {display_date} в {data['selected_time']}\n"
            f"Слот занят ✅"
        )
        try:
            await callback.bot.send_message(CHANNEL_ID, channel_text, parse_mode="HTML")
        except Exception:
            pass

    # Schedule reminders and feedback
    schedule_reminder(
        callback.bot, booking_id,
        callback.from_user.id,
        data["selected_date"], data["selected_time"],
        dp_storage=state.storage,
    )

    await state.clear()
    await callback.answer("Запись подтверждена! ✅")


# --------------- Cancel during booking flow ---------------

@router.callback_query(F.data == "cancel_booking_flow")
async def cancel_booking_flow(callback: CallbackQuery, state: FSMContext):
    """Cancel the booking process and return to menu."""
    await state.clear()
    await callback.message.edit_text(
        "❌ Процесс записи отменен.\n\nВернуться назад:",
        reply_markup=back_to_menu_kb(),
        parse_mode="HTML",
    )
    await callback.answer()
