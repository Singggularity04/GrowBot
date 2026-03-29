"""Booking cancellation handler."""

from datetime import datetime

from aiogram import Router, F
from aiogram.types import CallbackQuery

import database as db
from keyboards import cancel_confirm_kb, back_to_menu_kb
from scheduler import cancel_reminder
from config import ADMIN_ID, CHANNEL_ID

router = Router()


@router.callback_query(F.data == "my_bookings")
async def show_my_bookings(callback: CallbackQuery):
    """Show the user's active booking, if any."""
    booking = await db.get_booking_by_user(callback.from_user.id)

    if not booking:
        text = "📋 <b>У вас нет активных записей.</b>"
        if callback.message.photo:
            await callback.message.delete()
            await callback.message.answer(text, reply_markup=main_menu_kb(), parse_mode="HTML")
        else:
            await callback.message.edit_text(text, reply_markup=main_menu_kb(), parse_mode="HTML")
        await callback.answer()
        return

    dt = datetime.strptime(booking["date"], "%Y-%m-%d")
    display_date = dt.strftime("%d.%m.%Y")

    text = (
        f"📋 <b>Ваша запись:</b>\n\n"
        f"📅 Дата: <b>{display_date}</b>\n"
        f"🕐 Время: <b>{booking['time']}</b>\n"
        f"👤 Имя: <b>{booking['name']}</b>\n"
        f"📱 Телефон: <b>{booking['phone']}</b>\n\n"
        f"Хотите отменить запись?"
    )
    if callback.message.photo:
        await callback.message.delete()
        await callback.message.answer(text, reply_markup=cancel_confirm_kb(booking["id"]), parse_mode="HTML")
    else:
        await callback.message.edit_text(text, reply_markup=cancel_confirm_kb(booking["id"]), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("do_cancel:"))
async def do_cancel(callback: CallbackQuery):
    """Confirm booking cancellation — free slot and remove reminder."""
    _, booking_id_str = callback.data.split(":")
    booking_id = int(booking_id_str)

    # Get booking info before cancellation (for notification)
    booking = await db.get_booking_by_id(booking_id)
    slot_info = await db.cancel_booking(booking_id)

    if slot_info:
        cancel_reminder(booking_id)

        await callback.message.edit_text(
            "✅ <b>Запись успешно отменена.</b>\n"
            "Слот снова доступен для бронирования.",
            reply_markup=back_to_menu_kb(),
            parse_mode="HTML",
        )

        # Notify admin about cancellation
        if booking:
            dt = datetime.strptime(booking["date"], "%Y-%m-%d")
            display_date = dt.strftime("%d.%m.%Y")
            admin_text = (
                f"❌ <b>Отмена записи</b>\n\n"
                f"👤 {booking['name']}\n"
                f"📅 {display_date} в {booking['time']}\n"
                f"📱 {booking['phone']}"
            )
            try:
                await callback.bot.send_message(ADMIN_ID, admin_text, parse_mode="HTML")
            except Exception:
                pass

            # Notify channel
            if CHANNEL_ID:
                channel_text = (
                    f"🔓 <b>Слот освободился</b>\n\n"
                    f"📅 {display_date} в {booking['time']}\n"
                    f"Доступен для записи ✅"
                )
                try:
                    await callback.bot.send_message(CHANNEL_ID, channel_text, parse_mode="HTML")
                except Exception:
                    pass
    else:
        await callback.message.edit_text(
            "⚠️ Запись уже отменена или не существует.",
            reply_markup=back_to_menu_kb(),
            parse_mode="HTML",
        )

    await callback.answer()
