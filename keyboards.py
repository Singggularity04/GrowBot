"""Inline keyboards — every screen ends with a CTA button."""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import DIKIDI_LINK
from texts import SERVICES, FAQ_ITEMS, QUIZ_Q3_OPTIONS


# ─────────────────── Start menu ───────────────────

def start_kb() -> InlineKeyboardMarkup:
    """Main menu: 4 buttons capturing attention."""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="⚡ Записаться быстро", callback_data="quick_book"))
    builder.row(InlineKeyboardButton(text="🧠 Помочь выбрать", callback_data="quiz_start"))
    builder.row(
        InlineKeyboardButton(text="📸 Примеры работ", callback_data="portfolio"),
        InlineKeyboardButton(text="❓ Задать вопрос", callback_data="faq"),
    )
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


# ─────────────────── Booking CTA ───────────────────

def book_now_kb() -> InlineKeyboardMarkup:
    """Single big button linking to Dikidi."""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(
        text="📅 Записаться — выбрать время",
        url=DIKIDI_LINK,
    ))
    builder.row(InlineKeyboardButton(
        text="✅ Я записалась!",
        callback_data="i_booked",
    ))
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="menu"))
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
    builder.row(InlineKeyboardButton(
        text="📅 Записаться — выбрать время",
        url=DIKIDI_LINK,
    ))
    builder.row(InlineKeyboardButton(
        text="✅ Я записалась!",
        callback_data="i_booked",
    ))
    builder.row(InlineKeyboardButton(text="🔙 В меню", callback_data="menu"))
    return builder.as_markup()


# ─────────────────── Portfolio ───────────────────

def portfolio_nav_kb(current: int, total: int) -> InlineKeyboardMarkup:
    """Portfolio navigation: prev/next + book CTA."""
    builder = InlineKeyboardBuilder()

    nav_buttons = []
    if current > 0:
        nav_buttons.append(InlineKeyboardButton(text="◀️", callback_data=f"port:{current - 1}"))
    nav_buttons.append(InlineKeyboardButton(text=f"{current + 1}/{total}", callback_data="ignore"))
    if current < total - 1:
        nav_buttons.append(InlineKeyboardButton(text="▶️", callback_data=f"port:{current + 1}"))
    builder.row(*nav_buttons)

    builder.row(InlineKeyboardButton(
        text="📅 Хочу так же! Записаться",
        url=DIKIDI_LINK,
    ))
    builder.row(InlineKeyboardButton(
        text="✅ Я записалась!",
        callback_data="i_booked",
    ))
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
    builder.row(InlineKeyboardButton(
        text="📅 Записаться",
        url=DIKIDI_LINK,
    ))
    builder.row(InlineKeyboardButton(
        text="✅ Я записалась!",
        callback_data="i_booked",
    ))
    builder.row(
        InlineKeyboardButton(text="❓ Другой вопрос", callback_data="faq"),
        InlineKeyboardButton(text="🔙 Меню", callback_data="menu"),
    )
    return builder.as_markup()


# ─────────────────── Trust ───────────────────

def trust_kb() -> InlineKeyboardMarkup:
    """Trust block — CTA."""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(
        text="📅 Записаться",
        url=DIKIDI_LINK,
    ))
    builder.row(InlineKeyboardButton(
        text="✅ Я записалась!",
        callback_data="i_booked",
    ))
    builder.row(InlineKeyboardButton(text="🔙 В меню", callback_data="menu"))
    return builder.as_markup()


# ─────────────────── Follow-up ───────────────────

def followup_kb() -> InlineKeyboardMarkup:
    """Follow-up message keyboard — just booking CTA."""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(
        text="📅 Записаться — выбрать время",
        url=DIKIDI_LINK,
    ))
    builder.row(InlineKeyboardButton(
        text="✅ Я записалась!",
        callback_data="i_booked",
    ))
    return builder.as_markup()


# ─────────────────── Back to menu ───────────────────

def back_to_menu_kb() -> InlineKeyboardMarkup:
    """Simply back to menu."""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🔙 В меню", callback_data="menu"))
    return builder.as_markup()
