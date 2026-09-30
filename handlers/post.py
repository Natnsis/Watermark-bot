from io import BytesIO

from telegram import Update
from telegram.ext import ContextTypes

from db import get_session
from services import get_or_create_user


async def post_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    watermarked = context.user_data.get("last_watermarked")
    if watermarked is None:
        await update.message.reply_text("Send me a photo first, then use /post to publish it.")
        return

    tg_user = update.effective_user
    async with get_session() as session:
        user = await get_or_create_user(session, tg_user.id, tg_user.username)

    if not user.channel_id:
        await update.message.reply_text("No channel set yet. Use /setchannel to connect your channel first.")
        return

    await context.bot.send_photo(chat_id=user.channel_id, photo=BytesIO(watermarked))
    await update.message.reply_text("Posted!")
