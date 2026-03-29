"""Handler: Portfolio — show examples of work with navigation."""

import os
from aiogram import Router, F
from aiogram.types import CallbackQuery, FSInputFile

import database as db
from texts import PORTFOLIO_ITEMS, PORTFOLIO_HEADER
from keyboards import portfolio_nav_kb, booking_choice_kb

router = Router()

PHOTOS_DIR = os.path.join(os.path.dirname(__file__), "..", "photos")


async def _send_portfolio_item(callback: CallbackQuery, index: int) -> None:
    """Send a portfolio item — photo if exists, text otherwise."""
    total = len(PORTFOLIO_ITEMS)
    if index < 0 or index >= total:
        index = 0

    item = PORTFOLIO_ITEMS[index]
    photo_path = os.path.join(PHOTOS_DIR, os.path.basename(item["photo"]))
    kb = portfolio_nav_kb(index, total)

    # Try to send photo; fall back to text if file not found
    if os.path.isfile(photo_path):
        photo = FSInputFile(photo_path)
        # Delete old message and send photo (can't edit text → photo)
        await callback.message.delete()
        await callback.message.answer_photo(photo=photo, caption=item["caption"], reply_markup=kb)
    else:
        # Text-only mode (no photos uploaded yet)
        await callback.message.edit_text(item["caption"], reply_markup=kb)


@router.callback_query(F.data == "portfolio")
async def show_portfolio(callback: CallbackQuery) -> None:
    """Show portfolio header then first item."""
    await callback.answer()
    await db.log_interaction(callback.from_user.id, "portfolio")
    await _send_portfolio_item(callback, 0)


@router.callback_query(F.data.startswith("port:"))
async def navigate_portfolio(callback: CallbackQuery) -> None:
    """Navigate between portfolio items."""
    index = int(callback.data.split(":")[1])
    await callback.answer()

    # If current message has a photo, delete and resend
    if callback.message.photo:
        item = PORTFOLIO_ITEMS[index] if index < len(PORTFOLIO_ITEMS) else PORTFOLIO_ITEMS[0]
        photo_path = os.path.join(PHOTOS_DIR, os.path.basename(item["photo"]))
        total = len(PORTFOLIO_ITEMS)
        kb = portfolio_nav_kb(index, total)

        if os.path.isfile(photo_path):
            photo = FSInputFile(photo_path)
            await callback.message.delete()
            await callback.message.answer_photo(photo=photo, caption=item["caption"], reply_markup=kb)
            return

    await _send_portfolio_item(callback, index)
