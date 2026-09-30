from telegram import Update
from telegram.ext import ContextTypes

from db import get_session
from services import get_or_create_preference


async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    tg_user = update.effective_user
    async with get_session() as session:
        pref = await get_or_create_preference(session, tg_user.id, tg_user.username)

    await update.message.reply_text(
        "Your watermark settings:\n"
        f"Text: {pref.watermark_text}\n"
        f"Position: {pref.position}\n"
        f"Opacity: {pref.opacity}\n"
        f"Font size: {pref.font_size}\n"
        f"Color: {pref.color}\n\n"
        "Use /preference to change these."
    )
