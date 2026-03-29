"""Booking confirmation handler — triggered by the 24h reminder.

The scheduler sets the user into ConfirmationStates.waiting_confirmation.
User replies:
  +  → confirmed, booking kept
  -  → ask for cancellation reason, then cancel the booking
"""

from datetime import datetime

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

import database as db
from scheduler import cancel_reminder, remove_auto_cancel
from config import ADMIN_ID, CHANNEL_ID

router = Router()


class ConfirmationStates(StatesGroup):
    waiting_confirmation = State()   # waiting for + or -
    waiting_cancel_reason = State()  # waiting for cancellation reason text


# --------------- Confirm (+) ---------------

@router.callback_query(ConfirmationStates.waiting_confirmation, F.data == "rem_confirm")
async def handle_confirm(callback: CallbackQuery, state: FSMContext):
    """User confirmed the booking."""
    data = await state.get_data()
    booking_id = data.get("booking_id")
    
    # User confirmed, so remove the 12h auto-cancel job
    if booking_id:
        remove_auto_cancel(booking_id)

    await state.clear()

    date_str = data.get("date", "")
    time_str = data.get("time", "")

    # Format date for display
    try:
        display_date = datetime.strptime(date_str, "%Y-%m-%d").strftime("%d.%m.%Y")
    except ValueError:
        display_date = date_str

    await callback.message.edit_text(
        f"✅ <b>Запись подтверждена!</b>\n\n"
        f"Ожидаем вас {display_date} в {time_str} ❤️",
        parse_mode="HTML"
    )
    await callback.answer()


# --------------- Cancel (-) ---------------

@router.callback_query(ConfirmationStates.waiting_confirmation, F.data == "rem_cancel")
async def handle_deny(callback: CallbackQuery, state: FSMContext):
    """User wants to cancel — ask for reason first."""
    await state.set_state(ConfirmationStates.waiting_cancel_reason)
    await callback.message.edit_text(
        "Очень жаль, что у вас не получается прийти к нам. "
        "Подскажите пожалуйста, почему отменили запись?"
    )
    await callback.answer()


# --------------- Cancellation reason ---------------

@router.message(ConfirmationStates.waiting_cancel_reason)
async def handle_cancel_reason(message: Message, state: FSMContext):
    """User provided the cancellation reason — cancel booking and thank them."""
    data = await state.get_data()
    booking_id = data.get("booking_id")
    await state.clear()

    # Cancel booking in DB
    if booking_id:
        booking = await db.get_booking_by_id(booking_id)
        slot_info = await db.cancel_booking(booking_id)

        if slot_info:
            cancel_reminder(booking_id)

            # Notify admin about the cancellation + reason
            if booking and ADMIN_ID:
                try:
                    dt = datetime.strptime(booking["date"], "%Y-%m-%d")
                    display_date = dt.strftime("%d.%m.%Y")
                    await message.bot.send_message(
                        ADMIN_ID,
                        f"❌ <b>Отмена записи</b>\n\n"
                        f"👤 {booking['name']}\n"
                        f"📅 {display_date} в {booking['time']}\n"
                        f"📱 {booking['phone']}\n\n"
                        f"💬 <b>Причина:</b> {message.text or '(не указана)'}",
                        parse_mode="HTML",
                    )
                except Exception:
                    pass

            # Notify channel that slot is free
            if booking and CHANNEL_ID:
                try:
                    dt = datetime.strptime(booking["date"], "%Y-%m-%d")
                    display_date = dt.strftime("%d.%m.%Y")
                    await message.bot.send_message(
                        CHANNEL_ID,
                        f"🔓 <b>Слот освободился</b>\n\n"
                        f"📅 {display_date} в {booking['time']}\n"
                        f"Доступен для записи ✅",
                        parse_mode="HTML",
                    )
                except Exception:
                    pass

    await message.answer("Спасибо! Ждем вас в следующий раз.")


# --------------- Unknown input while waiting ---------------

@router.message(ConfirmationStates.waiting_confirmation)
async def handle_unknown_confirmation(message: Message, state: FSMContext):
    """User sent something other than + or - — prompt again."""
    await message.answer(
        "Пожалуйста, используйте <b>кнопки под сообщением</b> с напоминанием, "
        "чтобы подтвердить или отменить запись.",
        parse_mode="HTML",
    )
