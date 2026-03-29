"""Fallback handler — catches any unrecognized messages."""

from aiogram import Router
from aiogram.types import Message

from texts import UNKNOWN_MESSAGE
from keyboards import start_kb

router = Router()


@router.message()
async def fallback(message: Message) -> None:
    """Redirect unknown messages back to the menu."""
    await message.answer(UNKNOWN_MESSAGE, reply_markup=start_kb())
