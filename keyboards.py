"""Inline keyboards — every screen ends with a CTA button."""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import DIKIDI_LINK
from texts import SERVICES, FAQ_ITEMS, QUIZ_Q3_OPTIONS


# ─────────────────── Start menu ───────────────────

def start_engagement_kb() -> InlineKeyboardMarkup:
    """Main menu: 4 buttons capturing attention."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📅 Записаться", callback_data="style_choice"),
        InlineKeyboardButton(text="📸 Посмотреть работы", callback_data="portfolio")
    )
    builder.row(InlineKeyboardButton(text="🧠 Помочь выбрать", callback_data="quiz_start"))
    builder.row(InlineKeyboardButton(text="📋 Мои записи", callback_data="my_bookings"))
    builder.row(InlineKeyboardButton(text="❓ Задать вопрос", callback_data="faq"))
    return builder.as_markup()


# ─────────────────── Services list ───────────────────

def services_kb() -> InlineKeyboardMarkup:
    """List of services for quick booking."""
    builder = InlineKeyboardBuilder()
    for key, svc in SERVICES.items():
        builder.row(InlineKeyboardButton(
            text=f"{svc['name']} — {svc['short']}",
            callback_data=f"svc:{key}",
        ))
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="menu"))
    return builder.as_markup()


def service_detail_kb(service_key: str) -> InlineKeyboardMarkup:
    """Service details with CTA + back."""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(
        text="✅ Записаться на эту услугу",
        callback_data=f"pre_book:{service_key}",
    ))
    builder.row(
        InlineKeyboardButton(text="🔙 К услугам", callback_data="quick_book"),
        InlineKeyboardButton(text="🏠 Меню", callback_data="menu"),
    )
    return builder.as_markup()


# ─────────────────── Booking CTA (Merged) ───────────────────

def booking_choice_kb() -> InlineKeyboardMarkup:
    """Choice: Book via Telegram Calendar OR via Dikidi link."""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📅 Выбрать время", callback_data="booking_telegram"))
    builder.row(InlineKeyboardButton(text="🔗 Записаться через Dikidi", url=DIKIDI_LINK))
    builder.row(InlineKeyboardButton(text="✅ Я записалась!", callback_data="i_booked"))
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="menu"))
    return builder.as_markup()

# ─────────────────── Sales Funnel ───────────────────

def style_choice_kb() -> InlineKeyboardMarkup:
    """Style choice before booking."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🌸 Нежный", callback_data="style:tender"),
        InlineKeyboardButton(text="🔥 Яркий", callback_data="style:bright")
    )
    builder.row(
        InlineKeyboardButton(text="💎 Классика", callback_data="style:classic"),
        InlineKeyboardButton(text="✨ Дизайн", callback_data="style:design")
    )
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="menu"))
    return builder.as_markup()

def upsell_kb() -> InlineKeyboardMarkup:
    """Upsell yes/no options."""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="✅ Да", callback_data="upsell:yes"))
    builder.row(InlineKeyboardButton(text="❌ Нет, спасибо", callback_data="upsell:no"))
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="style_choice"))
    return builder.as_markup()


# ─────────────────── Quiz keyboards ───────────────────

def quiz_services_kb() -> InlineKeyboardMarkup:
    """Quiz step 1 — pick a service."""
    builder = InlineKeyboardBuilder()
    for key, svc in SERVICES.items():
        builder.row(InlineKeyboardButton(
            text=svc["name"],
            callback_data=f"quiz_svc:{key}",
        ))
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="menu"))
    return builder.as_markup()


def quiz_experience_kb() -> InlineKeyboardMarkup:
    """Quiz step 2 — first time or experienced."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🆕 Первый раз", callback_data="quiz_exp:first"),
        InlineKeyboardButton(text="👍 Уже делала", callback_data="quiz_exp:experienced"),
    )
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="quiz_start"))
    return builder.as_markup()


def quiz_priority_kb() -> InlineKeyboardMarkup:
    """Quiz step 3 — what matters most."""
    builder = InlineKeyboardBuilder()
    for key, label in QUIZ_Q3_OPTIONS.items():
        builder.row(InlineKeyboardButton(
            text=label,
            callback_data=f"quiz_pri:{key}",
        ))
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="quiz_start"))
    return builder.as_markup()


def quiz_result_kb() -> InlineKeyboardMarkup:
    """After recommendation — book now."""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📅 Записаться прямо в Telegram", callback_data="booking_telegram"))
    builder.row(InlineKeyboardButton(text="🔗 Записаться через Dikidi", url=DIKIDI_LINK))
    builder.row(InlineKeyboardButton(text="✅ Я записалась!", callback_data="i_booked"))
    builder.row(InlineKeyboardButton(text="🔙 В меню", callback_data="menu"))
    return builder.as_markup()


# ─────────────────── Portfolio ───────────────────

def portfolio_nav_kb(current: int, total: int) -> InlineKeyboardMarkup:
    """Portfolio navigation: prev/next + book CTA."""
    builder = InlineKeyboardBuilder()

    builder.row(InlineKeyboardButton(text="✅ Да", callback_data="style_choice"))
    
    next_index = current + 1 if current < total - 1 else 0
    builder.row(InlineKeyboardButton(text="🔄 Сначала посмотреть варианты", callback_data=f"port:{next_index}"))

    nav_buttons = []
    if current > 0:
        nav_buttons.append(InlineKeyboardButton(text="◀️", callback_data=f"port:{current - 1}"))
    nav_buttons.append(InlineKeyboardButton(text=f"{current + 1}/{total}", callback_data="ignore"))
    if current < total - 1:
        nav_buttons.append(InlineKeyboardButton(text="▶️", callback_data=f"port:{current + 1}"))
    builder.row(*nav_buttons)

    builder.row(InlineKeyboardButton(text="🔙 В меню", callback_data="menu"))
    return builder.as_markup()


# ─────────────────── FAQ ───────────────────

def faq_list_kb() -> InlineKeyboardMarkup:
    """List of FAQ questions."""
    builder = InlineKeyboardBuilder()
    for item in FAQ_ITEMS:
        builder.row(InlineKeyboardButton(
            text=item["question"],
            callback_data=f"faq:{item['id']}",
        ))
    builder.row(InlineKeyboardButton(text="🛡 Почему нам доверяют", callback_data="trust"))
    builder.row(InlineKeyboardButton(text="🔙 В меню", callback_data="menu"))
    return builder.as_markup()


def faq_answer_kb(question_id: str) -> InlineKeyboardMarkup:
    """After FAQ answer — CTA + back."""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📅 Записаться", callback_data="booking_telegram"))
    builder.row(InlineKeyboardButton(text="🔗 Через Dikidi", url=DIKIDI_LINK))
    builder.row(InlineKeyboardButton(text="✅ Я записалась!", callback_data="i_booked"))
    builder.row(
        InlineKeyboardButton(text="❓ Другой вопрос", callback_data="faq"),
        InlineKeyboardButton(text="🔙 Меню", callback_data="menu"),
    )
    return builder.as_markup()


# ─────────────────── Trust ───────────────────

def trust_kb() -> InlineKeyboardMarkup:
    """Trust block — CTA."""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📅 Записаться", callback_data="booking_telegram"))
    builder.row(InlineKeyboardButton(text="🔗 Через Dikidi", url=DIKIDI_LINK))
    builder.row(InlineKeyboardButton(text="✅ Я записалась!", callback_data="i_booked"))
    builder.row(InlineKeyboardButton(text="🔙 В меню", callback_data="menu"))
    return builder.as_markup()


# ─────────────────── Follow-up ───────────────────

def followup_kb() -> InlineKeyboardMarkup:
    """Follow-up message keyboard — just booking CTA."""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📅 Записаться прямо в Telegram", callback_data="booking_telegram"))
    builder.row(InlineKeyboardButton(text="🔗 Записаться через Dikidi", url=DIKIDI_LINK))
    builder.row(InlineKeyboardButton(text="✅ Я записалась!", callback_data="i_booked"))
    return builder.as_markup()


# ─────────────────── Back to menu ───────────────────

def back_to_menu_kb() -> InlineKeyboardMarkup:
    """Simply back to menu."""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🔙 В меню", callback_data="menu"))
    return builder.as_markup()


# =========================================================================
# NAILSBOT KEYBOARDS (Calendar, Admin, Subscription, Cancellation)
# =========================================================================

import calendar
from datetime import datetime
from config import now_moscow, CHANNEL_LINK

# ─────────────────── Subscription ───────────────────

def subscription_kb() -> InlineKeyboardMarkup:
    """Force user to subscribe before booking."""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📢 Подписаться на канал", url=CHANNEL_LINK))
    builder.row(InlineKeyboardButton(text="✅ Проверить подписку", callback_data="check_subscription"))
    return builder.as_markup()


# ─────────────────── User Calendar & Booking ───────────────────

MONTH_NAMES = {
    1: "Январь", 2: "Февраль", 3: "Март", 4: "Апрель",
    5: "Май", 6: "Июнь", 7: "Июль", 8: "Август",
    9: "Сентябрь", 10: "Октябрь", 11: "Ноябрь", 12: "Декабрь"
}

def _build_calendar_core(year: int, month: int, available_dates: list[str], prefix: str):
    builder = InlineKeyboardBuilder()
    now = now_moscow()

    # Prev/Next month calculated
    prev_m = month - 1 if month > 1 else 12
    prev_y = year if month > 1 else year - 1
    next_m = month + 1 if month < 12 else 1
    next_y = year if month < 12 else year + 1

    # Header: < Month Year >
    builder.row(
        InlineKeyboardButton(text="<", callback_data=f"{prefix}_nav:{prev_y}-{prev_m}"),
        InlineKeyboardButton(text=f"{MONTH_NAMES[month]} {year}", callback_data="ignore"),
        InlineKeyboardButton(text=">", callback_data=f"{prefix}_nav:{next_y}-{next_m}"),
    )

    # Weekdays
    builder.row(
        InlineKeyboardButton(text="Пн", callback_data="ignore"),
        InlineKeyboardButton(text="Вт", callback_data="ignore"),
        InlineKeyboardButton(text="Ср", callback_data="ignore"),
        InlineKeyboardButton(text="Чт", callback_data="ignore"),
        InlineKeyboardButton(text="Пт", callback_data="ignore"),
        InlineKeyboardButton(text="Сб", callback_data="ignore"),
        InlineKeyboardButton(text="Вс", callback_data="ignore"),
    )

    # Days
    cal = calendar.monthcalendar(year, month)
    for week in cal:
        row = []
        for day in week:
            if day == 0:
                row.append(InlineKeyboardButton(text=" ", callback_data="ignore"))
                continue

            date_str = f"{year}-{month:02d}-{day:02d}"
            
            # For user calendar: only show available future dates
            if prefix == "cal":
                cal_dt = datetime(year, month, day).date()
                if cal_dt < now.date() or date_str not in available_dates:
                    text = " "  # Hide unavailable days
                    cb_data = "ignore"
                else:
                    text = str(day)
                    cb_data = f"{prefix}_date:{date_str}"
            else:
                # Admin calendars (can see past/all dates, but highlight available)
                if date_str in available_dates:
                    text = f"•{day}•"
                else:
                    text = str(day)
                cb_data = f"{prefix}:{date_str}"
                
            row.append(InlineKeyboardButton(text=text, callback_data=cb_data))
        builder.row(*row)
        
    return builder


def calendar_kb(year: int, month: int, available_dates: list[str]) -> InlineKeyboardMarkup:
    """User calendar for booking."""
    builder = _build_calendar_core(year, month, available_dates, "cal")
    builder.row(InlineKeyboardButton(text="🔙 Отмена", callback_data="cancel_booking_flow"))
    return builder.as_markup()


def time_slots_kb(slots: list[dict], date_str: str) -> InlineKeyboardMarkup:
    """Show available time slots for a specific date."""
    builder = InlineKeyboardBuilder()
    
    # Arrange time buttons in rows of 2 or 3
    row = []
    for s in slots:
        row.append(InlineKeyboardButton(
            text=s["time"],
            callback_data=f"slot:{s['id']}"
        ))
        if len(row) == 3:
            builder.row(*row)
            row = []
    if row:
        builder.row(*row)
        
    # Reconstruct year/month for back button
    y, m, _ = date_str.split("-")
    builder.row(InlineKeyboardButton(text="🔙 К выбору даты", callback_data=f"booking_back:{y}-{m}"))
    return builder.as_markup()


def confirm_booking_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="✅ Подтвердить запись", callback_data="confirm_booking"))
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_booking_flow"))
    return builder.as_markup()


def cancel_confirm_kb(booking_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="❌ Да, отменить запись", callback_data=f"do_cancel:{booking_id}"))
    builder.row(InlineKeyboardButton(text="🔙 Оставить как есть", callback_data="menu"))
    return builder.as_markup()


def reminder_action_kb(booking_id: int) -> InlineKeyboardMarkup:
    """24-hour reminder confirmation/cancellation."""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="✅ Подтвердить приход", callback_data="rem_confirm"))
    builder.row(InlineKeyboardButton(text="❌ Отменить запись", callback_data="rem_cancel"))
    return builder.as_markup()


# ─────────────────── Admin Panel ───────────────────

def admin_menu_kb() -> InlineKeyboardMarkup:
    """Admin main menu."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="➕ Доб. день", callback_data="adm_add_day"),
        InlineKeyboardButton(text="➕ Доб. слот", callback_data="adm_add_slot"),
    )
    builder.row(
        InlineKeyboardButton(text="🗑 Удал. слот", callback_data="adm_del_slot"),
        InlineKeyboardButton(text="🚫 Закр. день", callback_data="adm_close_day"),
    )
    builder.row(
        InlineKeyboardButton(text="📋 Расписание", callback_data="adm_view_schedule"),
        InlineKeyboardButton(text="📊 Воронка", callback_data="adm_stats"),
    )
    builder.row(InlineKeyboardButton(text="❌ Отменить запись клиента", callback_data="adm_cancel_booking"))
    return builder.as_markup()


def admin_calendar_kb(year: int, month: int, available_dates: list[str], prefix: str) -> InlineKeyboardMarkup:
    """Admin calendar (shows all dates, highlights those with slots)."""
    builder = _build_calendar_core(year, month, available_dates, prefix)
    builder.row(InlineKeyboardButton(text="🔙 В админку", callback_data="admin_menu"))
    return builder.as_markup()
