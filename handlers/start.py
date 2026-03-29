"""Handler: /start — welcome message, user registration, follow-up scheduling."""

from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

import database as db
from texts import START_MESSAGE, START_ENGAGEMENT, BOOKING_CONFIRMED, UNKNOWN_MESSAGE
from keyboards import start_engagement_kb, back_to_menu_kb
from scheduler import schedule_funnel, cancel_reminder

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    """Greet user, register in DB, start follow-up funnel."""
    await state.clear()

    # Register user
    await db.register_user(
        user_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
    )
    await db.log_interaction(message.from_user.id, "start")

    # Send welcome hook followed by engagement
    await message.answer(START_MESSAGE)
    await message.answer(START_ENGAGEMENT, reply_markup=start_engagement_kb())

    # Schedule follow-up messages for users who don't book
    await schedule_funnel(message.bot, message.from_user.id)


@router.callback_query(F.data == "menu")
async def back_to_menu(callback: CallbackQuery, state: FSMContext) -> None:
    """Return to main menu."""
    await state.clear()
    await callback.answer()
    
    try:
        await callback.message.delete()
    except Exception:
        pass
    
    await callback.message.answer(START_MESSAGE)
    await callback.message.answer(START_ENGAGEMENT, reply_markup=start_engagement_kb())


@router.callback_query(F.data == "i_booked")
async def user_booked(callback: CallbackQuery) -> None:
    """User confirms they booked via Dikidi — cancel follow-ups."""
    await callback.answer("Отлично! 🎉")
    await db.mark_booked(callback.from_user.id)
    await db.log_interaction(callback.from_user.id, "booked")
    
    # Cancel all pending follow-up messages
    await db.cancel_followups(callback.from_user.id)
    from scheduler import scheduler
    for stage in (1, 2):
        try:
            scheduler.remove_job(f"funnel_{callback.from_user.id}_{stage}")
        except:
            pass
            
    await callback.message.edit_text(BOOKING_CONFIRMED, reply_markup=back_to_menu_kb())


@router.callback_query(F.data == "ignore")
async def ignore_callback(callback: CallbackQuery) -> None:
    """Silently ignore non-interactive buttons."""
    await callback.answer()
