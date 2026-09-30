from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from db import get_session
from services import get_or_create_preference
from watermark import POSITIONS

TEXT, POSITION, OPACITY, COLOR = range(4)


def _is_hex_color(value: str) -> bool:
    if not value.startswith("#") or len(value) != 7:
        return False
    try:
        int(value[1:], 16)
        return True
    except ValueError:
        return False


async def preference_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Send the watermark text you'd like to use (e.g. @yourbrand):")
    return TEXT


async def receive_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["watermark_text"] = update.message.text.strip()
    keyboard = [[InlineKeyboardButton(p, callback_data=p)] for p in sorted(POSITIONS)]
    await update.message.reply_text("Choose watermark position:", reply_markup=InlineKeyboardMarkup(keyboard))
    return POSITION


async def receive_position(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data["position"] = query.data
    await query.edit_message_text(f"Position set to {query.data}.")
    await query.message.reply_text("Send opacity as a number between 0.1 and 1.0:")
    return OPACITY


async def receive_opacity(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        opacity = float(update.message.text.strip())
        if not 0.1 <= opacity <= 1.0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("Please send a number between 0.1 and 1.0.")
        return OPACITY
    context.user_data["opacity"] = opacity
    await update.message.reply_text("Send a hex color for the text, e.g. #FFFFFF:")
    return COLOR


async def receive_color(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    color = update.message.text.strip()
    if not _is_hex_color(color):
        await update.message.reply_text("Please send a valid hex color like #FFFFFF.")
        return COLOR

    tg_user = update.effective_user
    async with get_session() as session:
        pref = await get_or_create_preference(session, tg_user.id, tg_user.username)
        pref.watermark_text = context.user_data["watermark_text"]
        pref.position = context.user_data["position"]
        pref.opacity = context.user_data["opacity"]
        pref.color = color
        await session.commit()

    await update.message.reply_text("Your watermark preferences have been saved. Send a photo to try it out!")
    context.user_data.clear()
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    await update.message.reply_text("Cancelled.")
    return ConversationHandler.END


preference_conversation = ConversationHandler(
    entry_points=[CommandHandler("preference", preference_start)],
    states={
        TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_text)],
        POSITION: [CallbackQueryHandler(receive_position)],
        OPACITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_opacity)],
        COLOR: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_color)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)
