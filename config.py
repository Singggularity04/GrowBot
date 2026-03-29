"""Bot configuration — loads secrets and settings from .env file."""

import os
from datetime import datetime

import pytz
from dotenv import load_dotenv

load_dotenv()

MOSCOW_TZ = pytz.timezone("Europe/Moscow")

def now_moscow() -> datetime:
    """Current time in Moscow timezone."""
    return datetime.now(MOSCOW_TZ)

# --- Required ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

# --- Optional channel subscription ---
CHANNEL_ID = os.getenv("CHANNEL_ID")
CHANNEL_LINK = os.getenv("CHANNEL_LINK")

# --- Booking link (Dikidi / Yclients / etc.) ---
DIKIDI_LINK = os.getenv("DIKIDI_LINK", "https://dikidi.net")

# --- Master info ---
MASTER_NAME = os.getenv("MASTER_NAME", "Мастер")
MASTER_CITY = os.getenv("MASTER_CITY", "Москва")

# --- Follow-up delays (seconds) ---
FOLLOWUP_DELAY_1 = 3 * 60      # 3 minutes
FOLLOWUP_DELAY_2 = 15 * 60     # 15 minutes
FOLLOWUP_DELAY_3 = 2 * 60 * 60 # 2 hours
