"""Handler: FAQ — short answers that remove fears and lead to booking."""

from aiogram import Router, F
from aiogram.types import CallbackQuery

import database as db
from texts import FAQ_ITEMS, FAQ_HEADER
from keyboards import faq_list_kb, faq_answer_kb

router = Router()


@router.callback_query(F.data == "faq")
async def show_faq(callback: CallbackQuery) -> None:
    """Show FAQ questions list."""
    await callback.answer()
    await db.log_interaction(callback.from_user.id, "faq")
    await callback.message.edit_text(FAQ_HEADER, reply_markup=faq_list_kb())


@router.callback_query(F.data.startswith("faq:"))
async def show_faq_answer(callback: CallbackQuery) -> None:
    """Show answer to selected FAQ question + CTA."""
    question_id = callback.data.split(":")[1]
    await callback.answer()

    # Find the FAQ item
    item = next((q for q in FAQ_ITEMS if q["id"] == question_id), None)
    if not item:
        await callback.answer("Вопрос не найден")
        return

    await db.log_interaction(callback.from_user.id, f"faq_{question_id}")
    await callback.message.edit_text(
        f"<b>{item['question']}</b>\n\n{item['answer']}",
        reply_markup=faq_answer_kb(question_id),
    )
