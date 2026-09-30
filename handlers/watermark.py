from io import BytesIO

from telegram import Update
from telegram.ext import ContextTypes

from db import get_session
from services import get_or_create_preference
from watermark import apply_text_watermark


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    tg_user = update.effective_user
    photo = update.message.photo[-1]
    tg_file = await photo.get_file()
    buf = BytesIO()
    await tg_file.download_to_memory(buf)
    image_bytes = buf.getvalue()

    async with get_session() as session:
        pref = await get_or_create_preference(session, tg_user.id, tg_user.username)

    watermarked = apply_text_watermark(
        image_bytes,
        text=pref.watermark_text,
        position=pref.position,
        opacity=pref.opacity,
        font_size=pref.font_size,
        color=pref.color,
    )
    context.user_data["last_watermarked"] = watermarked

    await update.message.reply_photo(
        photo=BytesIO(watermarked),
        caption="Here's your watermarked photo. Use /post to publish it.",
    )
