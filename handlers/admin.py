"""Handler: Admin — stats and broadcast (admin-only)."""

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message

from config import ADMIN_ID
import database as db

router = Router()


def _is_admin(user_id: int) -> bool:
    """Check if user is the admin."""
    return user_id == ADMIN_ID


@router.message(Command("stats"))
async def cmd_stats(message: Message) -> None:
    """Show funnel statistics (admin only)."""
    if not _is_admin(message.from_user.id):
        return

    stats = await db.get_stats()
    actions_text = "\n".join(
        f"  • {action}: {count}" for action, count in stats["actions"].items()
    )

    await message.answer(
        f"📊 <b>Статистика GROW BOT</b>\n\n"
        f"👥 Всего пользователей: <b>{stats['total_users']}</b>\n"
        f"✅ Записались: <b>{stats['booked_users']}</b>\n"
        f"📈 Конверсия: <b>{stats['conversion']}%</b>\n\n"
        f"<b>Действия:</b>\n{actions_text or '  Нет данных'}"
    )
