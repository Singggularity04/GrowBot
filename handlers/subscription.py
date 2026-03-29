"""Subscription check utility — gates booking behind channel membership."""

from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery

from config import CHANNEL_ID, CHANNEL_LINK
from keyboards import subscription_kb, start_engagement_kb
from texts import START_ENGAGEMENT

router = Router()


async def check_subscription(bot: Bot, user_id: int) -> bool:
    """Return True if user is subscribed to the required channel."""
    if not CHANNEL_ID:
        return True  # No channel configured — skip check

    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        return member.status in ("member", "administrator", "creator")
    except Exception:
        return False


@router.callback_query(F.data == "check_subscription")
async def on_check_subscription(callback: CallbackQuery):
    """Re-check subscription after user clicks 'Проверить подписку'."""
    is_subscribed = await check_subscription(callback.bot, callback.from_user.id)

    if is_subscribed:
        await callback.message.edit_text(
            f"✅ <b>Подписка подтверждена!</b>\n\n{START_ENGAGEMENT}",
            reply_markup=start_engagement_kb(),
            parse_mode="HTML",
        )
    else:
        await callback.answer("❌ Вы ещё не подписались на канал!", show_alert=True)
