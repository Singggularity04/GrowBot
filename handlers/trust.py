"""Handler: Trust block — builds confidence and leads to booking."""

from aiogram import Router, F
from aiogram.types import CallbackQuery

import database as db
from texts import TRUST_MESSAGE
from keyboards import trust_kb

router = Router()


@router.callback_query(F.data == "trust")
async def show_trust(callback: CallbackQuery) -> None:
    """Show trust block: sterility, accuracy, experience."""
    await callback.answer()
    await db.log_interaction(callback.from_user.id, "trust")
    await callback.message.edit_text(TRUST_MESSAGE, reply_markup=trust_kb())
