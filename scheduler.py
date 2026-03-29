"""APScheduler-based reminder and funnel system.

Combines the 3-stage follow-up funnel for new users and the 24h/1h
booking reminders / auto-cancellation for scheduled clients.
"""

from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler

import database as db
from config import ADMIN_ID, CHANNEL_ID, MOSCOW_TZ, now_moscow
from config import FOLLOWUP_DELAY_1, FOLLOWUP_DELAY_2
from texts import FOLLOWUP_TEXTS
from keyboards import followup_kb

scheduler = AsyncIOScheduler(timezone=MOSCOW_TZ)

# =========================================================================
# GROW BOT FUNNEL (Follow-ups)
# =========================================================================

async def send_followup(bot, user_id: int, stage: int):
    """Send a specific follow-up stage."""
    # Safety check: if user already booked, abort.
    if await db.is_booked(user_id):
        return

    text = FOLLOWUP_TEXTS.get(stage)
    if not text:
        return

    try:
        await bot.send_message(
            user_id,
            text,
            reply_markup=followup_kb(),
            parse_mode="HTML"
        )
        await db.mark_followup_sent(user_id, stage)
        await db.log_interaction(user_id, f"received_followup_stage_{stage}")
    except Exception:
        pass


def schedule_funnel(bot, user_id: int):
    """Schedule all 3 follow-up stages for a new user."""
    now = now_moscow()

    delays = [
        (1, FOLLOWUP_DELAY_1),
        (2, FOLLOWUP_DELAY_2),
    ]

    for stage, delay_sec in delays:
        fire_at = now + timedelta(seconds=delay_sec)
        job_id = f"funnel_{user_id}_{stage}"

        scheduler.add_job(
            send_followup,
            trigger="date",
            run_date=fire_at,
            args=[bot, user_id, stage],
            id=job_id,
            replace_existing=True,
        )
        # Store in DB for crash recovery
        import asyncio
        asyncio.create_task(db.save_followup(user_id, stage, fire_at.isoformat()))


# =========================================================================
# NAILSBOT BOOKING REMINDERS & AUTO-CANCEL
# =========================================================================

REMINDER_TEMPLATES = {
    24: (
        "🕐 До вашей записи осталось 24 часа.\n"
        "Вы записаны на <b>{date}</b> в <b>{time}</b>.\n\n"
        "📍 Наша студия находится по адресу:\n"
        "<b>г. Москва, улица Полярная 54, корпус 5</b>\n"
        "(10 минут от станции метро 🚇 Медведково).\n\n"
        "Пожалуйста, подтвердите запись: <b>нажмите одну из кнопок "
        "ниже</b> для подтверждения или отмены."
    ),
    1: (
        "🕐 До вашей записи остался 1 час.\n"
        "Вы записаны на <b>{date}</b> в <b>{time}</b>.\n\n"
        "📍 Наша студия находится по адресу:\n"
        "<b>г. Москва, улица Полярная 54, корпус 5</b>\n"
        "(10 минут от станции метро 🚇 Медведково).\n\n"
        "С нетерпением ждём вас ❤️"
    ),
}


async def send_reminder(bot, user_id: int, date_str: str, time_str: str,
                        hours_before: int, booking_id: int = None, dp_storage=None):
    """Send the 24h or 1h reminder message to the user."""
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    display_date = dt.strftime("%d.%m.%Y")

    template = REMINDER_TEMPLATES.get(hours_before, REMINDER_TEMPLATES[1])
    text = template.format(date=display_date, time=time_str)

    try:
        if hours_before == 24:
            from keyboards import reminder_action_kb
            await bot.send_message(user_id, text, reply_markup=reminder_action_kb(booking_id), parse_mode="HTML")
        else:
            await bot.send_message(user_id, text, parse_mode="HTML")
    except Exception:
        return

    # After the 24h reminder, set FSM state to wait for confirmation
    if hours_before == 24 and dp_storage and booking_id:
        try:
            from aiogram.fsm.context import FSMContext
            from aiogram.fsm.storage.base import StorageKey
            from handlers.confirmation import ConfirmationStates

            key = StorageKey(bot_id=bot.id, chat_id=user_id, user_id=user_id)
            state = FSMContext(storage=dp_storage, key=key)
            await state.set_state(ConfirmationStates.waiting_confirmation)
            await state.update_data(booking_id=booking_id, date=date_str, time=time_str)
        except Exception as e:
            print(f"Error setting confirmation state: {e}")


async def send_feedback_request(bot, user_id: int, booking_id: int, dp_storage):
    """Ask for a review 3h after the appointment."""
    from aiogram.fsm.context import FSMContext
    from aiogram.fsm.storage.base import StorageKey
    from handlers.feedback import FeedbackStates

    try:
        await bot.send_message(
            user_id,
            "Как прошёл ваш сеанс? Оставьте нам свой отзыв, "
            "мы будем вам очень благодарны ☺️",
        )
        key = StorageKey(bot_id=bot.id, chat_id=user_id, user_id=user_id)
        state = FSMContext(storage=dp_storage, key=key)
        await state.set_state(FeedbackStates.waiting_review)
    except Exception:
        pass

    try:
        await db.cancel_booking(booking_id)
    except Exception:
        pass


async def auto_cancel_booking(bot, booking_id: int, user_id: int, dp_storage=None):
    """Automatically cancel booking if not confirmed within 12h of 24h reminder."""
    booking = await db.get_booking_by_id(booking_id)
    slot_info = await db.cancel_booking(booking_id)

    if not slot_info:
        return

    cancel_reminder(booking_id)

    if dp_storage:
        try:
            from aiogram.fsm.context import FSMContext
            from aiogram.fsm.storage.base import StorageKey

            key = StorageKey(bot_id=bot.id, chat_id=user_id, user_id=user_id)
            state = FSMContext(storage=dp_storage, key=key)
            current_state = await state.get_state()
            if current_state and "waiting_confirmation" in current_state:
                await state.clear()
        except Exception:
            pass

    try:
        dt = datetime.strptime(booking["date"], "%Y-%m-%d")
        display_date = dt.strftime("%d.%m.%Y")
        await bot.send_message(
            user_id,
            f"❌ <b>Запись отменена</b>\n\n"
            f"Вы не подтвердили вашу запись на <b>{display_date}</b> в <b>{booking['time']}</b>.\n"
            f"Бронь была автоматически снята.",
            parse_mode="HTML"
        )
    except Exception:
        pass

    if ADMIN_ID and booking:
        try:
            await bot.send_message(
                ADMIN_ID,
                f"⚠️ <b>Автоматическая отмена записи (нет подтверждения)</b>\n\n"
                f"👤 {booking['name']}\n"
                f"📅 {display_date} в {booking['time']}\n"
                f"📱 {booking['phone']}",
                parse_mode="HTML",
            )
        except Exception:
            pass

    if CHANNEL_ID and booking:
        try:
            await bot.send_message(
                CHANNEL_ID,
                f"🔓 <b>Слот освободился</b>\n\n"
                f"📅 {display_date} в {booking['time']}\n"
                f"Доступен для записи ✅",
                parse_mode="HTML",
            )
        except Exception:
            pass


def schedule_reminder(bot, booking_id: int, user_id: int, date_str: str, time_str: str,
                      dp_storage=None):
    """Add reminder jobs 24h and 1h before, and feedback 3h after."""
    dt_str = f"{date_str} {time_str}"
    naive_dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M")
    appointment_dt = MOSCOW_TZ.localize(naive_dt)
    now = now_moscow()

    for hours in (24, 1):
        remind_at = appointment_dt - timedelta(hours=hours)
        if remind_at <= now:
            continue

        job_id = f"reminder_{booking_id}_{hours}h"
        scheduler.add_job(
            send_reminder,
            trigger="date",
            run_date=remind_at,
            args=[bot, user_id, date_str, time_str, hours, booking_id, dp_storage],
            id=job_id,
            replace_existing=True,
        )

        if hours == 24:
            auto_cancel_at = remind_at + timedelta(hours=12)
            if auto_cancel_at > now:
                scheduler.add_job(
                    auto_cancel_booking,
                    trigger="date",
                    run_date=auto_cancel_at,
                    args=[bot, booking_id, user_id, dp_storage],
                    id=f"auto_cancel_{booking_id}",
                    replace_existing=True,
                )

    if dp_storage:
        feedback_at = appointment_dt + timedelta(hours=3)
        if feedback_at > now:
            job_id = f"feedback_{booking_id}"
            scheduler.add_job(
                send_feedback_request,
                trigger="date",
                run_date=feedback_at,
                args=[bot, user_id, booking_id, dp_storage],
                id=job_id,
                replace_existing=True,
            )


def remove_auto_cancel(booking_id: int):
    """Remove the auto-cancel job (called when user confirms)."""
    try:
        scheduler.remove_job(f"auto_cancel_{booking_id}")
    except Exception:
        pass


def cancel_reminder(booking_id: int):
    """Remove scheduled reminders and feedback when booking is cancelled."""
    for job_id in (f"reminder_{booking_id}_24h", f"reminder_{booking_id}_1h",
                   f"feedback_{booking_id}", f"auto_cancel_{booking_id}"):
        try:
            scheduler.remove_job(job_id)
        except Exception:
            pass


async def restore_jobs(bot, dp_storage=None):
    """Restore all pending funnels and reminders from DB after bot restart."""
    now = now_moscow()
    
    # 1. Restore funnels
    pending_followups = await db.get_pending_followups()
    for row in pending_followups:
        fire_at = datetime.fromisoformat(row["fire_at"])
        if fire_at.tzinfo is None:
            fire_at = MOSCOW_TZ.localize(fire_at)

        if fire_at > now:
            job_id = f"funnel_{row['user_id']}_{row['stage']}"
            scheduler.add_job(
                send_followup,
                trigger="date",
                run_date=fire_at,
                args=[bot, row["user_id"], row["stage"]],
                id=job_id,
                replace_existing=True,
            )
        else:
            await db.mark_followup_sent(row["user_id"], row["stage"])

    # 2. Restore booking reminders
    bookings = await db.get_all_future_bookings()
    for booking in bookings:
        schedule_reminder(
            bot,
            booking["id"],
            booking["user_id"],
            booking["date"],
            booking["time"],
            dp_storage=dp_storage,
        )
