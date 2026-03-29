"""Handler: Quick booking — service list → details → Dikidi link."""

from aiogram import Router, F
from aiogram.types import CallbackQuery

import database as db
from texts import SERVICES, PRE_BOOKING
from keyboards import services_kb, service_detail_kb, book_now_kb

router = Router()


@router.callback_query(F.data == "quick_book")
async def show_services(callback: CallbackQuery) -> None:
    """Show list of available services."""
    await callback.answer()
    await db.log_interaction(callback.from_user.id, "view_services")
    await callback.message.edit_text(
        "⚡ <b>Быстрая запись</b>\n\nВыберите услугу 👇",
        reply_markup=services_kb(),
    )


@router.callback_query(F.data.startswith("svc:"))
async def show_service_detail(callback: CallbackQuery) -> None:
    """Show service details with booking CTA."""
    service_key = callback.data.split(":")[1]
    service = SERVICES.get(service_key)
    if not service:
        await callback.answer("Услуга не найдена")
        return

    await callback.answer()
    await db.log_interaction(callback.from_user.id, f"view_{service_key}")
    await callback.message.edit_text(
        service["detail"],
        reply_markup=service_detail_kb(service_key),
    )


@router.callback_query(F.data.startswith("pre_book:"))
async def pre_booking(callback: CallbackQuery) -> None:
    """Motivational message before Dikidi link."""
    await callback.answer()
    await db.log_interaction(callback.from_user.id, "pre_book")
    await callback.message.edit_text(PRE_BOOKING, reply_markup=book_now_kb())
