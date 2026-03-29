"""Admin panel — manage schedule, slots, and bookings.

Access restricted to ADMIN_ID from config.
"""

from datetime import datetime

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder

import database as db
from config import ADMIN_ID, now_moscow
from keyboards import admin_menu_kb, admin_calendar_kb
from scheduler import cancel_reminder

router = Router()


class AdminStates(StatesGroup):
    add_day_date = State()
    add_slot_date = State()
    add_slot_time = State()
    del_slot_select = State()
    close_day_select = State()
    cancel_booking_select = State()
    view_schedule_select = State()


def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID


# --------------- /admin command ---------------

@router.message(Command("admin"))
async def cmd_admin(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Доступ запрещён.")
        return

    await message.answer(
        "🛠 <b>Админ-панель</b>\n\nВыберите действие:",
        reply_markup=admin_menu_kb(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "admin_menu")
async def admin_menu(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён.", show_alert=True)
        return

    await state.clear()
    await callback.message.edit_text(
        "🛠 <b>Админ-панель</b>\n\nВыберите действие:",
        reply_markup=admin_menu_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


# --------------- Add work day (bulk slot creation) ---------------

@router.callback_query(F.data == "adm_add_day")
async def adm_add_day(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return

    await state.set_state(AdminStates.add_day_date)
    await callback.message.edit_text(
        "📅 <b>Добавление рабочего дня</b>\n\n"
        "Введите дату в формате <code>ДД.ММ.ГГГГ</code>\n"
        "Например: <code>15.04.2026</code>\n\n"
        "Будут созданы слоты: 09:00 – 18:00 (каждый час).",
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(AdminStates.add_day_date)
async def adm_add_day_process(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    try:
        dt = datetime.strptime(message.text.strip(), "%d.%m.%Y")
        date_str = dt.strftime("%Y-%m-%d")
    except ValueError:
        await message.answer("❌ Неверный формат даты. Используйте <code>ДД.ММ.ГГГГ</code>", parse_mode="HTML")
        return

    # Create hourly slots from 09:00 to 18:00
    default_times = [f"{h:02d}:00" for h in range(9, 19)]
    for t in default_times:
        await db.add_slot(date_str, t)

    display_date = dt.strftime("%d.%m.%Y")
    await message.answer(
        f"✅ Рабочий день <b>{display_date}</b> добавлен.\n"
        f"Создано слотов: <b>{len(default_times)}</b> (09:00 – 18:00)",
        reply_markup=admin_menu_kb(),
        parse_mode="HTML",
    )
    await state.clear()


# --------------- Add single slot ---------------

@router.callback_query(F.data == "adm_add_slot")
async def adm_add_slot(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return

    await state.set_state(AdminStates.add_slot_date)
    await callback.message.edit_text(
        "🕐 <b>Добавление слота</b>\n\n"
        "Введите дату и время в формате:\n"
        "<code>ДД.ММ.ГГГГ ЧЧ:ММ</code>\n\n"
        "Например: <code>15.04.2026 14:30</code>",
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(AdminStates.add_slot_date)
async def adm_add_slot_process(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    try:
        parts = message.text.strip()
        dt = datetime.strptime(parts, "%d.%m.%Y %H:%M")
        date_str = dt.strftime("%Y-%m-%d")
        time_str = dt.strftime("%H:%M")
    except ValueError:
        await message.answer(
            "❌ Неверный формат. Используйте <code>ДД.ММ.ГГГГ ЧЧ:ММ</code>",
            parse_mode="HTML",
        )
        return

    await db.add_slot(date_str, time_str)
    display_date = dt.strftime("%d.%m.%Y")

    await message.answer(
        f"✅ Слот <b>{display_date}</b> в <b>{time_str}</b> добавлен.",
        reply_markup=admin_menu_kb(),
        parse_mode="HTML",
    )
    await state.clear()


# --------------- Delete slot ---------------

@router.callback_query(F.data == "adm_del_slot")
async def adm_del_slot(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return

    now = now_moscow()
    dates = await db.get_all_dates_with_slots()
    await state.set_state(AdminStates.del_slot_select)
    await callback.message.edit_text(
        "🗑 <b>Удаление слота</b>\n\nВыберите дату:",
        reply_markup=admin_calendar_kb(now.year, now.month, dates, "adm_del"),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("adm_del_nav:"))
async def adm_del_nav(callback: CallbackQuery):
    _, ym = callback.data.split(":")
    year, month = map(int, ym.split("-"))
    dates = await db.get_all_dates_with_slots()
    await callback.message.edit_reply_markup(
        reply_markup=admin_calendar_kb(year, month, dates, "adm_del")
    )
    await callback.answer()


@router.callback_query(F.data.startswith("adm_del:"))
async def adm_del_date_selected(callback: CallbackQuery):
    """Show unbooked slots for deletion."""
    _, date_str = callback.data.split(":")
    slots = await db.get_available_times(date_str)

    if not slots:
        await callback.answer("На эту дату нет свободных слотов для удаления.", show_alert=True)
        return

    builder = InlineKeyboardBuilder()
    for s in slots:
        builder.row(
            InlineKeyboardButton(
                text=f"🗑 {s['time']}",
                callback_data=f"adm_del_confirm:{s['id']}"
            )
        )
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="admin_menu"))

    dt = datetime.strptime(date_str, "%Y-%m-%d")
    await callback.message.edit_text(
        f"🗑 Удалить слот на <b>{dt.strftime('%d.%m.%Y')}</b>:",
        reply_markup=builder.as_markup(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("adm_del_confirm:"))
async def adm_del_confirm(callback: CallbackQuery, state: FSMContext):
    _, slot_id_str = callback.data.split(":")
    await db.delete_slot(int(slot_id_str))
    await state.clear()
    await callback.message.edit_text(
        "✅ Слот удалён.",
        reply_markup=admin_menu_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


# --------------- Close day ---------------

@router.callback_query(F.data == "adm_close_day")
async def adm_close_day(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return

    now = now_moscow()
    dates = await db.get_all_dates_with_slots()
    await state.set_state(AdminStates.close_day_select)
    await callback.message.edit_text(
        "🚫 <b>Закрытие дня</b>\n\nВыберите дату для закрытия:",
        reply_markup=admin_calendar_kb(now.year, now.month, dates, "adm_close"),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("adm_close_nav:"))
async def adm_close_nav(callback: CallbackQuery):
    _, ym = callback.data.split(":")
    year, month = map(int, ym.split("-"))
    dates = await db.get_all_dates_with_slots()
    await callback.message.edit_reply_markup(
        reply_markup=admin_calendar_kb(year, month, dates, "adm_close")
    )
    await callback.answer()


@router.callback_query(F.data.startswith("adm_close:"))
async def adm_close_date_selected(callback: CallbackQuery, state: FSMContext):
    _, date_str = callback.data.split(":")
    await db.close_day(date_str)
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    await state.clear()

    await callback.message.edit_text(
        f"🚫 День <b>{dt.strftime('%d.%m.%Y')}</b> закрыт.\n"
        f"Все слоты на этот день недоступны.",
        reply_markup=admin_menu_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


# --------------- Cancel client booking ---------------

@router.callback_query(F.data == "adm_cancel_booking")
async def adm_cancel_booking(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return

    now = now_moscow()
    dates = await db.get_all_dates_with_slots()
    await state.set_state(AdminStates.cancel_booking_select)
    await callback.message.edit_text(
        "❌ <b>Отмена записи клиента</b>\n\nВыберите дату:",
        reply_markup=admin_calendar_kb(now.year, now.month, dates, "adm_cbook"),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("adm_cbook_nav:"))
async def adm_cbook_nav(callback: CallbackQuery):
    _, ym = callback.data.split(":")
    year, month = map(int, ym.split("-"))
    dates = await db.get_all_dates_with_slots()
    await callback.message.edit_reply_markup(
        reply_markup=admin_calendar_kb(year, month, dates, "adm_cbook")
    )
    await callback.answer()


@router.callback_query(F.data.startswith("adm_cbook:"))
async def adm_cbook_date_selected(callback: CallbackQuery):
    """Show bookings on selected date for cancellation."""
    _, date_str = callback.data.split(":")
    bookings = await db.get_bookings_for_date(date_str)

    if not bookings:
        await callback.answer("На эту дату нет записей.", show_alert=True)
        return

    builder = InlineKeyboardBuilder()
    for b in bookings:
        builder.row(
            InlineKeyboardButton(
                text=f"❌ {b['time']} — {b['name']}",
                callback_data=f"adm_cbook_do:{b['id']}"
            )
        )
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="admin_menu"))

    dt = datetime.strptime(date_str, "%Y-%m-%d")
    await callback.message.edit_text(
        f"❌ Записи на <b>{dt.strftime('%d.%m.%Y')}</b>:\n\nВыберите для отмены:",
        reply_markup=builder.as_markup(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("adm_cbook_do:"))
async def adm_cbook_do(callback: CallbackQuery, state: FSMContext):
    """Admin cancels a client's booking — notifies the client."""
    _, booking_id_str = callback.data.split(":")
    booking_id = int(booking_id_str)

    booking = await db.get_booking_by_id(booking_id)
    slot = await db.cancel_booking(booking_id)

    if slot and booking:
        cancel_reminder(booking_id)

        dt = datetime.strptime(booking["date"], "%Y-%m-%d")
        display_date = dt.strftime("%d.%m.%Y")

        # Notify client
        try:
            await callback.bot.send_message(
                booking["user_id"],
                f"❌ <b>Ваша запись отменена администратором</b>\n\n"
                f"📅 {display_date} в {booking['time']}\n\n"
                f"Вы можете записаться на другое время.",
                parse_mode="HTML",
            )
        except Exception:
            pass

        await callback.message.edit_text(
            f"✅ Запись <b>{booking['name']}</b> на {display_date} {booking['time']} отменена.",
            reply_markup=admin_menu_kb(),
            parse_mode="HTML",
        )
    else:
        await callback.message.edit_text(
            "⚠️ Запись уже удалена или не существует.",
            reply_markup=admin_menu_kb(),
            parse_mode="HTML",
        )

    await state.clear()
    await callback.answer()


# --------------- View schedule ---------------

@router.callback_query(F.data == "adm_view_schedule")
async def adm_view_schedule(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return

    now = now_moscow()
    dates = await db.get_all_dates_with_slots()
    await state.set_state(AdminStates.view_schedule_select)
    await callback.message.edit_text(
        "📋 <b>Просмотр расписания</b>\n\nВыберите дату:",
        reply_markup=admin_calendar_kb(now.year, now.month, dates, "adm_sched"),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("adm_sched_nav:"))
async def adm_sched_nav(callback: CallbackQuery):
    _, ym = callback.data.split(":")
    year, month = map(int, ym.split("-"))
    dates = await db.get_all_dates_with_slots()
    await callback.message.edit_reply_markup(
        reply_markup=admin_calendar_kb(year, month, dates, "adm_sched")
    )
    await callback.answer()


@router.callback_query(F.data.startswith("adm_sched:"))
async def adm_sched_date_selected(callback: CallbackQuery, state: FSMContext):
    """Show full schedule for the selected date."""
    _, date_str = callback.data.split(":")
    all_slots = await db.get_all_slots_for_date(date_str)
    bookings = await db.get_bookings_for_date(date_str)

    dt = datetime.strptime(date_str, "%Y-%m-%d")
    display_date = dt.strftime("%d.%m.%Y")

    if not all_slots:
        text = f"📋 <b>Расписание на {display_date}</b>\n\nСлотов нет."
    else:
        # Build a lookup of booked slot_ids
        booked_map = {b["slot_id"]: b for b in bookings}

        lines = [f"📋 <b>Расписание на {display_date}</b>\n"]
        for s in all_slots:
            if s["is_closed"]:
                lines.append(f"🚫 {s['time']} — Закрыт")
            elif s["id"] in booked_map:
                b = booked_map[s["id"]]
                lines.append(
                    f"🔴 {s['time']} — {b['name']} ({b['phone']})"
                )
            else:
                lines.append(f"🟢 {s['time']} — Свободно")
        text = "\n".join(lines)

    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="admin_menu"))

    await callback.message.edit_text(
        text, reply_markup=builder.as_markup(), parse_mode="HTML"
    )
    await state.clear()
    await callback.answer()


# --------------- Funnel Stats ---------------

@router.message(Command("stats"))
async def cmd_stats(message: Message) -> None:
    """Show funnel statistics (admin only)."""
    if not is_admin(message.from_user.id):
        return

    await _send_stats(message)


@router.callback_query(F.data == "adm_stats")
async def adm_stats_callback(callback: CallbackQuery) -> None:
    """Show funnel stats from the admin menu."""
    if not is_admin(callback.from_user.id):
        return

    await _send_stats(callback.message, edit=True)
    await callback.answer()


async def _send_stats(message: Message, edit: bool = False):
    """Fetch and format funnel stats."""
    stats = await db.get_stats()
    actions_text = "\n".join(
        f"  • {action}: {count}" for action, count in stats["actions"].items()
    )

    text = (
        f"📊 <b>Статистика воронок GROW BOT</b>\n\n"
        f"👥 Всего пользователей: <b>{stats['total_users']}</b>\n"
        f"✅ Записались (Telegram + Dikidi): <b>{stats['booked_users']}</b>\n"
        f"📈 Конверсия: <b>{stats['conversion']}%</b>\n\n"
        f"<b>Действия (клики):</b>\n{actions_text or '  Нет данных'}"
    )

    from keyboards import admin_menu_kb
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🔙 В админку", callback_data="admin_menu"))

    if edit:
        await message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")
    else:
        await message.answer(text, reply_markup=builder.as_markup(), parse_mode="HTML")
