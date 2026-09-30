import logging

from telegram import ChatMemberAdministrator, InlineKeyboardButton, InlineKeyboardMarkup, Message, MessageOriginChannel, Update
from telegram.constants import ChatMemberStatus, ChatType, MessageLimit
from telegram.error import TelegramError
from telegram.ext import (
    ApplicationHandlerStop,
    CallbackQueryHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from db import get_session
from handlers.start import back_to_menu_button
from services import get_channel_watermark, save_channel, set_channel_watermark

logger = logging.getLogger(__name__)

AWAITING_CHANNEL, AWAITING_WATERMARK = range(2)
MAX_WATERMARK_LENGTH = 200
SEPARATOR = "\n\n"
CANCEL_KEYBOARD = InlineKeyboardMarkup([[InlineKeyboardButton("✖️ Cancel", callback_data="wm:cancel")]])


async def watermark_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.callback_query.answer()
    await update.effective_chat.send_message(
        "Which channel?\n\n"
        "Forward any post from your channel here, or send its @username.",
        reply_markup=CANCEL_KEYBOARD,
    )
    return AWAITING_CHANNEL


async def receive_channel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    message = update.message
    origin = message.forward_origin

    if isinstance(origin, MessageOriginChannel):
        chat_ref: str | int = origin.chat.id
    elif message.text and message.text.strip().startswith("@"):
        chat_ref = message.text.strip()
    else:
        await message.reply_text("Forward a post from your channel, or send its @username.", reply_markup=CANCEL_KEYBOARD)
        return AWAITING_CHANNEL

    try:
        chat = await context.bot.get_chat(chat_ref)
    except TelegramError:
        await message.reply_text("I can't find that channel. Check the username, or forward a post instead.", reply_markup=CANCEL_KEYBOARD)
        return AWAITING_CHANNEL

    if chat.type != ChatType.CHANNEL:
        await message.reply_text("That's not a channel. Forward a post from a channel, or send its @username.", reply_markup=CANCEL_KEYBOARD)
        return AWAITING_CHANNEL

    try:
        bot_member = await context.bot.get_chat_member(chat.id, context.bot.id)
    except TelegramError:
        bot_member = None
    if not isinstance(bot_member, ChatMemberAdministrator) or not bot_member.can_edit_messages:
        await message.reply_text(
            f"Add me as an admin in {chat.title} with the \"Edit messages\" permission, "
            "then send the channel again.",
            reply_markup=CANCEL_KEYBOARD,
        )
        return AWAITING_CHANNEL

    user_member = await context.bot.get_chat_member(chat.id, update.effective_user.id)
    if user_member.status not in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER):
        await message.reply_text(f"You need to be an admin of {chat.title} to set its watermark.", reply_markup=CANCEL_KEYBOARD)
        return AWAITING_CHANNEL

    async with get_session() as session:
        await save_channel(session, update.effective_user.id, chat.id, chat.title)
    context.user_data["watermark_channel_id"] = chat.id

    await message.reply_text(
        f"Got it: {chat.title}\n\n"
        "Now send the watermark text. I'll add it to the end of every new post.",
        reply_markup=CANCEL_KEYBOARD,
    )
    return AWAITING_WATERMARK


async def receive_watermark(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    if len(text) > MAX_WATERMARK_LENGTH:
        await update.message.reply_text(
            f"Keep it under {MAX_WATERMARK_LENGTH} characters. Try again.", reply_markup=CANCEL_KEYBOARD
        )
        return AWAITING_WATERMARK

    channel_id = context.user_data.pop("watermark_channel_id")
    async with get_session() as session:
        await set_channel_watermark(session, channel_id, text)

    await update.message.reply_text(
        f"Saved ✅\n\nNew posts in your channel will end with:\n\n{text}\n\n📅 Week Count is now unlocked.",
        reply_markup=InlineKeyboardMarkup([[back_to_menu_button()]]),
    )
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.pop("watermark_channel_id", None)
    await update.callback_query.answer()
    await update.callback_query.edit_message_text("Cancelled.", reply_markup=InlineKeyboardMarkup([[back_to_menu_button()]]))
    return ConversationHandler.END


watermark_conversation = ConversationHandler(
    entry_points=[CallbackQueryHandler(watermark_start, pattern=r"^menu:watermark$")],
    states={
        AWAITING_CHANNEL: [MessageHandler((filters.TEXT & ~filters.COMMAND) | filters.FORWARDED, receive_channel)],
        AWAITING_WATERMARK: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_watermark)],
    },
    fallbacks=[CallbackQueryHandler(cancel, pattern=r"^wm:cancel$")],
    allow_reentry=True,
)


async def watermark_channel_post(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Channel updates (including our own edits) are handled only here, never by the private-chat handlers.
    post = update.channel_post
    if post is not None:
        await _add_watermark(post)
    raise ApplicationHandlerStop


async def _add_watermark(post: Message) -> None:
    async with get_session() as session:
        watermark = await get_channel_watermark(session, post.chat_id)
    if not watermark:
        return

    try:
        if post.text:
            if post.text.endswith(watermark):
                return
            new_text = post.text + SEPARATOR + watermark
            if len(new_text) > MessageLimit.MAX_TEXT_LENGTH:
                return
            await post.edit_text(
                new_text,
                entities=post.entities,
                link_preview_options=post.link_preview_options,
            )
        elif post.photo or post.video or post.document or post.audio or post.animation or post.voice:
            # In an album only the captioned item carries the caption, so leave the rest alone.
            if post.media_group_id and not post.caption:
                return
            caption = post.caption or ""
            if caption.endswith(watermark):
                return
            new_caption = caption + SEPARATOR + watermark if caption else watermark
            if len(new_caption) > MessageLimit.CAPTION_LENGTH:
                return
            await post.edit_caption(
                new_caption,
                caption_entities=post.caption_entities,
                show_caption_above_media=post.show_caption_above_media,
            )
    except TelegramError:
        logger.exception("Couldn't add watermark to post %s in %s", post.message_id, post.chat_id)


channel_post_handler = MessageHandler(filters.UpdateType.CHANNEL_POSTS, watermark_channel_post)
