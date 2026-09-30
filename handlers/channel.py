from telegram import MessageOriginChannel, Update
from telegram.constants import ChatMemberStatus
from telegram.error import TelegramError
from telegram.ext import CommandHandler, ContextTypes, ConversationHandler, MessageHandler, filters

from db import get_session
from services import get_or_create_user, set_user_channel

AWAITING_CHANNEL = 0


async def setchannel_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "Forward any message from your channel here, or send its @username or numeric chat id.\n"
        "Make sure the bot is an admin of that channel first."
    )
    return AWAITING_CHANNEL


async def receive_channel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    message = update.message
    origin = message.forward_origin
    chat_ref: str | int | None = None

    if isinstance(origin, MessageOriginChannel):
        chat_ref = origin.chat.id
    elif message.text:
        text = message.text.strip()
        chat_ref = int(text) if text.lstrip("-").isdigit() else text

    if chat_ref is None:
        await update.message.reply_text("I didn't recognize that. Forward a channel message or send its @username.")
        return AWAITING_CHANNEL

    try:
        chat = await context.bot.get_chat(chat_ref)
        member = await context.bot.get_chat_member(chat.id, context.bot.id)
    except TelegramError as exc:
        await update.message.reply_text(f"Couldn't look that up: {exc.message}. Try again.")
        return AWAITING_CHANNEL

    if member.status not in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER):
        await update.message.reply_text(
            "I'm not an admin in that channel yet. Add the bot as an admin there, then try again."
        )
        return AWAITING_CHANNEL

    tg_user = update.effective_user
    async with get_session() as session:
        await get_or_create_user(session, tg_user.id, tg_user.username)
        await set_user_channel(session, tg_user.id, chat.id, chat.title)

    await update.message.reply_text(f"Channel set to {chat.title or chat.id}. I'll post here from now on.")
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Cancelled.")
    return ConversationHandler.END


channel_conversation = ConversationHandler(
    entry_points=[CommandHandler("setchannel", setchannel_start)],
    states={
        AWAITING_CHANNEL: [MessageHandler(filters.TEXT & ~filters.COMMAND | filters.FORWARDED, receive_channel)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)
