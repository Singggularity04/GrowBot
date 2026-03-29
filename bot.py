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


async def main() -> None:
    """Initialize everything and start long-polling."""
    if not BOT_TOKEN:
        logging.error("BOT_TOKEN is not set. Create .env file with BOT_TOKEN=...")
        return

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

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
    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stdout,
    )
    asyncio.run(main())
