"""GROW BOT — Telegram sales funnel for beauty service masters.

Entry point: creates Bot + Dispatcher, initializes DB & Scheduler, starts polling.
"""

import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import BOT_TOKEN
from database import init_db
from scheduler import scheduler, restore_jobs
from handlers import all_routers
from logger_utils import setup_telegram_logging


async def main() -> None:
    """Initialize everything and start long-polling."""
    if not BOT_TOKEN:
        logging.error("BOT_TOKEN is not set. Create .env file with BOT_TOKEN=...")
        return

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    # Enable automatic error reporting to Admin
    setup_telegram_logging(bot, ADMIN_ID)

    dp = Dispatcher()

    # Register all routers in priority order
    for router in all_routers:
        dp.include_router(router)

    # Initialize database
    await init_db()
    logging.info("Database initialized.")

    # Start scheduler and restore pending jobs (funnels and reminders)
    scheduler.start()
    await restore_jobs(bot, dp_storage=dp.storage)
    logging.info("Scheduler started, all pending jobs restored.")

    # Start polling
    logging.info("GROW BOT is starting...")
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logging.critical(f"Fatal error during polling: {e}")
        # Exit with error code to trigger systemd restart
        sys.exit(1)


if __name__ == "__main__":
    import os
    from logging.handlers import RotatingFileHandler
    
    # Create logs directory if not exists
    if not os.path.exists("logs"):
        os.makedirs("logs")

    # ROOT Logger Configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    # 1. Console Handler (for journalctl / SSH)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # 2. Rotating File Handler (The "Auto-Cleaner")
    # Max size: 5MB, keep last 5 files
    file_handler = RotatingFileHandler(
        "logs/bot.log", 
        maxBytes=5*1024*1024, 
        backupCount=5,
        encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Bot stopped by user.")
    except Exception as e:
        logging.critical(f"Core error: {e}")
        sys.exit(1)
