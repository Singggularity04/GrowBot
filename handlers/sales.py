"""Handler: Sales Funnel (Hook -> Style -> Upsell -> Fears -> Urgency -> CTA)"""

from aiogram import Router, F
from aiogram.types import CallbackQuery

import database as db
from texts import STYLE_CHOICE, STYLE_CONFIRM, UPSELL_PROMPT, FEARS_URGENCY, PRE_BOOKING
from keyboards import style_choice_kb, upsell_kb, booking_choice_kb

router = Router()

# =========================================================================
# STEP 1: STYLE CHOICE
# =========================================================================

@router.callback_query(F.data == "style_choice")
async def prompt_style_choice(callback: CallbackQuery) -> None:
    """Prompt the user to pick a style (Tender, Bright, Classic, Design)."""
    await callback.answer()
    
    # If the message has a photo (from portfolio), delete and send text
    if callback.message.photo:
        await callback.message.delete()
        await callback.message.answer(STYLE_CHOICE, reply_markup=style_choice_kb(), parse_mode="HTML")
    else:
        try:
            await callback.message.edit_text(STYLE_CHOICE, reply_markup=style_choice_kb(), parse_mode="HTML")
        except Exception:
            await callback.message.delete()
            await callback.message.answer(STYLE_CHOICE, reply_markup=style_choice_kb(), parse_mode="HTML")
    
    await db.log_interaction(callback.from_user.id, "view_style_choice")


# =========================================================================
# STEP 2: EFFECT & UPSELL
# =========================================================================

@router.callback_query(F.data.startswith("style:"))
async def process_style_choice(callback: CallbackQuery) -> None:
    """Handle style selection and trigger the micro-sale + upsell."""
    style_key = callback.data.split(":")[1]
    await callback.answer()
    await db.log_interaction(callback.from_user.id, f"chosen_style_{style_key}")

    # Micro-sale: Confirm choice
    await callback.message.edit_text(STYLE_CONFIRM)
    
    # Upsell Prompt
    await callback.message.answer(UPSELL_PROMPT, reply_markup=upsell_kb(), parse_mode="HTML")


# =========================================================================
# STEP 3: OBJECTION HANDLING & URGENCY
# =========================================================================

@router.callback_query(F.data.startswith("upsell:"))
async def process_upsell(callback: CallbackQuery) -> None:
    """Handle the upsell answer and show fears/urgency before final CTA."""
    upsell_ans = callback.data.split(":")[1]
    await callback.answer()
    await db.log_interaction(callback.from_user.id, f"upsell_{upsell_ans}")

    try:
        await callback.message.delete()
    except Exception:
        pass

    # Address fears, show price/time, create urgency
    await callback.message.answer(FEARS_URGENCY, parse_mode="HTML")
    
    # Present final booking options (Telegram / Dikidi)
    await callback.message.answer(PRE_BOOKING, reply_markup=booking_choice_kb(), parse_mode="HTML")
