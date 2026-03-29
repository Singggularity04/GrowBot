"""Feedback handler — collects reviews after appointments."""

from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config import ADMIN_ID

router = Router()


class FeedbackStates(StatesGroup):
    waiting_review = State()


@router.message(FeedbackStates.waiting_review)
async def process_review(message: Message, state: FSMContext):
    """User sent their review — thank them and forward to admin."""
    await state.clear()

    await message.answer(
        "Спасибо за ваш отзыв, мы стараемся делать наш сервис лучше ❤️"
    )

    # Forward review to admin
    if ADMIN_ID:
        try:
            await message.bot.send_message(
                ADMIN_ID,
                f"📝 <b>Новый отзыв</b>\n\n"
                f"👤 От: {message.from_user.full_name} "
                f"(ID: <code>{message.from_user.id}</code>)\n\n"
                f"💬 {message.text or '(медиа)'}",
                parse_mode="HTML",
            )
            # Also forward the original message if it contains media
            if not message.text:
                await message.forward(ADMIN_ID)
        except Exception:
            pass
