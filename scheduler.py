"""Follow-up scheduler — automatically nurtures users who didn't book.

Three-stage funnel:
  Stage 1 (3 min)  — "Вы не завершили запись"
  Stage 2 (15 min) — "Свободных окон мало"
  Stage 3 (2 hr)   — "Обычно к этому времени уже всё занято"
"""

from datetime import timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler

import database as db
from config import MOSCOW_TZ, now_moscow, FOLLOWUP_DELAY_1, FOLLOWUP_DELAY_2, FOLLOWUP_DELAY_3
from texts import FOLLOWUP_1, FOLLOWUP_2, FOLLOWUP_3

scheduler = AsyncIOScheduler(timezone=MOSCOW_TZ)

# Stage → (delay_seconds, message_text)
STAGES = {
    1: (FOLLOWUP_DELAY_1, FOLLOWUP_1),
    2: (FOLLOWUP_DELAY_2, FOLLOWUP_2),
    3: (FOLLOWUP_DELAY_3, FOLLOWUP_3),
}


async def _send_followup(bot, user_id: int, stage: int) -> None:
    """Send a follow-up message if user hasn't booked yet."""
    # Check if user already booked — skip if so
    if await db.is_booked(user_id):
        await db.mark_followup_sent(user_id, stage)
        return

    _, text = STAGES[stage]

    try:
        # Import here to avoid circular imports
        from keyboards import followup_kb
        await bot.send_message(user_id, text, reply_markup=followup_kb())
    except Exception:
        pass  # User may have blocked the bot

    await db.mark_followup_sent(user_id, stage)
    await db.log_interaction(user_id, f"followup_{stage}")


async def schedule_followups(bot, user_id: int) -> None:
    """Schedule all 3 follow-up messages for a new user."""
    now = now_moscow()

    # Cancel any existing follow-ups first (in case of /start restart)
    cancel_followups(user_id)
    await db.cancel_followups(user_id)

    for stage, (delay, _) in STAGES.items():
        fire_at = now + timedelta(seconds=delay)
        job_id = f"fu_{user_id}_{stage}"

        scheduler.add_job(
            _send_followup,
            trigger="date",
            run_date=fire_at,
            args=[bot, user_id, stage],
            id=job_id,
            replace_existing=True,
        )

        # Save to DB for crash recovery
        await db.save_followup(user_id, stage, fire_at.isoformat())


def cancel_followups(user_id: int) -> None:
    """Cancel all pending follow-up jobs for a user."""
    for stage in STAGES:
        job_id = f"fu_{user_id}_{stage}"
        try:
            scheduler.remove_job(job_id)
        except Exception:
            pass  # Job may not exist


async def restore_followups(bot) -> None:
    """Restore pending follow-ups from DB after bot restart."""
    from datetime import datetime

    pending = await db.get_pending_followups()
    now = now_moscow()

    for item in pending:
        fire_at = datetime.fromisoformat(item["fire_at"])
        # Make timezone-aware if necessary
        if fire_at.tzinfo is None:
            fire_at = MOSCOW_TZ.localize(fire_at)

        # Skip past follow-ups
        if fire_at <= now:
            await db.mark_followup_sent(item["user_id"], item["stage"])
            continue

        job_id = f"fu_{item['user_id']}_{item['stage']}"
        scheduler.add_job(
            _send_followup,
            trigger="date",
            run_date=fire_at,
            args=[bot, item["user_id"], item["stage"]],
            id=job_id,
            replace_existing=True,
        )
