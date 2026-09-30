import html
import logging
import re
from datetime import date, datetime, time, timedelta

from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup, LinkPreviewOptions, Message, Update
from telegram.constants import KeyboardButtonStyle, MessageLimit, ParseMode
from telegram.error import Forbidden, TelegramError
from telegram.ext import CallbackQueryHandler, ContextTypes, ConversationHandler, MessageHandler, filters

import year_progress
from config import TIMEZONE
from db import get_session
from handlers.start import back_to_menu_button
from models import WeeklyCount
from services import (
    activate_weekly_count,
    deactivate_weekly_count,
    get_progress_style,
    get_user_channel,
    get_weekly_count,
    list_active_weekly_counts,
    log_activity,
    mark_recap_headings_used,
    pick_recap_heading,
)

logger = logging.getLogger(__name__)

MONDAY_PROMPT_TIME = time(9, 0, tzinfo=TIMEZONE)
MONDAY = 1  # PTB job days: 0 = Sunday
MAX_START_COUNT = 10_000

AWAITING_COUNT = 0
AWAITING_COMPLETION, AWAITING_PROGRESS, AWAITING_IMAGE, PREVIEW = range(1, 5)

NO_PREVIEW = LinkPreviewOptions(is_disabled=True)


def _keyboard(*rows: list[InlineKeyboardButton]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(list(rows))


MENU_KEYBOARD = _keyboard([back_to_menu_button()])


# --- week math ---------------------------------------------------------------


def current_monday() -> date:
    today = datetime.now(TIMEZONE).date()
    return today - timedelta(days=today.weekday())


def week_count_for(row: WeeklyCount, monday: date) -> int:
    return row.start_count + (monday - row.start_monday).days // 7


def weeks_left_in_year(monday: date) -> int:
    return (date(monday.year + 1, 1, 1) - monday).days // 7


# --- Week Count screen -------------------------------------------------------


async def _render_screen(user_id: int) -> tuple[str, InlineKeyboardMarkup]:
    async with get_session() as session:
        channel = await get_user_channel(session, user_id)
        row = await get_weekly_count(session, user_id)

    monday = current_monday()
    iso_week = monday.isocalendar().week
    channel_title = html.escape(channel.channel_title or str(channel.channel_id))

    if row is not None and row.active:
        text = (
            "📅 <b>Week Count</b>\n\n"
            f"Week <b>{iso_week}</b> of {monday.year} · your week <b>[{week_count_for(row, monday)}]</b>\n"
            f"⏳ {weeks_left_in_year(monday)} weeks left in {monday.year}\n"
            f"📢 {channel_title}\n\n"
            "Every Monday at 9:00 I'll ask for your weekly recap and post it to your channel."
        )
        keyboard = _keyboard(
            [InlineKeyboardButton("✍️ Write recap now", callback_data="week:recap", style=KeyboardButtonStyle.PRIMARY)],
            [InlineKeyboardButton("⏸ Turn off", callback_data="week:off", style=KeyboardButtonStyle.DANGER)],
            [back_to_menu_button()],
        )
    else:
        text = (
            "📅 <b>Week Count</b>\n\n"
            "Turn this on and I'll count your weeks. Every Monday I'll ask what you finished, "
            f"what you moved forward and for an image, then post a recap to {channel_title}.\n\n"
            f"This is week <b>{iso_week}</b> of {monday.year}. What number should this week be in your count?"
        )
        keyboard = _keyboard(
            [InlineKeyboardButton("▶️ Start at week 1", callback_data="week:start1", style=KeyboardButtonStyle.SUCCESS)],
            [InlineKeyboardButton("🔢 I already have a count", callback_data="week:custom")],
            [back_to_menu_button()],
        )
    return text, keyboard


async def _show_screen_in_place(update: Update) -> None:
    text, keyboard = await _render_screen(update.effective_user.id)
    await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)


async def _send_screen(update: Update) -> None:
    text, keyboard = await _render_screen(update.effective_user.id)
    await update.effective_chat.send_message(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)


async def _has_channel(user_id: int) -> bool:
    async with get_session() as session:
        return await get_user_channel(session, user_id) is not None


async def week_screen_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user_id = update.effective_user.id
    if not await _has_channel(user_id):
        await query.answer("🔒 Set up your channel with 🖼 Watermark first to unlock this.", show_alert=True)
        return

    if query.data == "week:start1":
        async with get_session() as session:
            await activate_weekly_count(session, user_id, 1, current_monday())
        await query.answer("Week Count is on ✅")
    elif query.data == "week:off":
        async with get_session() as session:
            await deactivate_weekly_count(session, user_id)
        await query.answer("Week Count is off")
    elif query.data == "week:skip":
        await query.answer()
        await query.edit_message_text("Skipped this week. See you next Monday 👋", reply_markup=MENU_KEYBOARD)
        return
    else:
        await query.answer()
    await _show_screen_in_place(update)


week_screen_handler = CallbackQueryHandler(week_screen_callback, pattern=r"^week:(open|start1|off|skip|count_cancel)$")


# --- "I already have a count" ------------------------------------------------


async def custom_count_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    monday = current_monday()
    await query.edit_message_text(
        f"This is week {monday.isocalendar().week} of {monday.year}.\n\n"
        "Send the number this week should have in your count, for example 92.",
        reply_markup=_keyboard([InlineKeyboardButton("✖️ Cancel", callback_data="week:count_cancel")]),
    )
    return AWAITING_COUNT


async def receive_count(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    if not text.isdigit() or not 1 <= int(text) <= MAX_START_COUNT:
        await update.message.reply_text(
            "Send just a number, like 92.",
            reply_markup=_keyboard([InlineKeyboardButton("✖️ Cancel", callback_data="week:count_cancel")]),
        )
        return AWAITING_COUNT

    async with get_session() as session:
        await activate_weekly_count(session, update.effective_user.id, int(text), current_monday())
    await _send_screen(update)
    return ConversationHandler.END


async def custom_count_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.callback_query.answer()
    await _show_screen_in_place(update)
    return ConversationHandler.END


count_conversation = ConversationHandler(
    entry_points=[CallbackQueryHandler(custom_count_start, pattern=r"^week:custom$")],
    states={AWAITING_COUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_count)]},
    fallbacks=[CallbackQueryHandler(custom_count_cancel, pattern=r"^week:count_cancel$")],
    allow_reentry=True,
)


# --- weekly recap ------------------------------------------------------------


RECAP_KEYS = ("recap_completion", "recap_progress", "recap_photo", "recap_headings")
SECTIONS = ("completion", "progress")
CANCEL_BUTTON = InlineKeyboardButton("✖️ Cancel", callback_data="recap:cancel")


def _bullets(text: str) -> list[str]:
    lines = (line.strip().lstrip("-•*").strip() for line in text.splitlines())
    return [f"- {html.escape(line)}" for line in lines if line]


def build_recap_post(
    count: int, monday: date, sections: list[tuple[str, str]], watermark: str | None, progress_style: str | None = None
) -> str:
    """`sections` is a list of (heading, answer) pairs."""
    last_week = (monday - timedelta(days=7)).isocalendar().week
    parts = [
        "It's Monday once more\n"
        f"Good luck with week {monday.isocalendar().week} [{count}]\n"
        f"{html.escape(year_progress.render(progress_style, monday))}",
        f"Week {last_week} feats :",
    ]
    for heading, answer in sections:
        bullets = _bullets(answer)
        if bullets:
            parts.append(f"<blockquote>{html.escape(heading)}</blockquote>\n" + "\n".join(bullets))
    if watermark:
        parts.append(html.escape(watermark))
    return "\n\n".join(parts)


def _visible_length(html_text: str) -> int:
    return len(html.unescape(re.sub(r"<[^>]+>", "", html_text)))


async def send_recap(
    bot: Bot, chat_id: int, text: str, photo: str | None, reply_markup: InlineKeyboardMarkup | None = None
) -> Message:
    if photo and _visible_length(text) <= MessageLimit.CAPTION_LENGTH:
        return await bot.send_photo(chat_id, photo, caption=text, parse_mode=ParseMode.HTML, reply_markup=reply_markup)
    if photo:
        await bot.send_photo(chat_id, photo)
    return await bot.send_message(
        chat_id, text, parse_mode=ParseMode.HTML, link_preview_options=NO_PREVIEW, reply_markup=reply_markup
    )


async def _recap_text(user_id: int, user_data: dict) -> tuple[str, int, str]:
    """Returns the post HTML, the channel id and the channel title."""
    async with get_session() as session:
        row = await get_weekly_count(session, user_id)
        channel = await get_user_channel(session, user_id)
        progress_style = await get_progress_style(session, user_id)
    monday = current_monday()
    headings = user_data["recap_headings"]
    text = build_recap_post(
        week_count_for(row, monday),
        monday,
        [(headings[section][1], user_data.get(f"recap_{section}", "")) for section in SECTIONS],
        channel.watermark_text,
        progress_style,
    )
    return text, channel.channel_id, channel.channel_title or str(channel.channel_id)


async def _ask_completion(chat_send) -> int:
    last_week = (current_monday() - timedelta(days=7)).isocalendar().week
    await chat_send(
        f"✍️ <b>Week {last_week} recap</b> · step 1 of 3\n\n"
        "<b>Completion wins</b> // closing loops\n"
        "What did you finish last week? One per line.",
        parse_mode=ParseMode.HTML,
        reply_markup=_keyboard([CANCEL_BUTTON]),
    )
    return AWAITING_COMPLETION


async def recap_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    async with get_session() as session:
        row = await get_weekly_count(session, update.effective_user.id)
        channel = await get_user_channel(session, update.effective_user.id)
    if row is None or not row.active or channel is None:
        await query.answer("Turn on 📅 Week Count first.", show_alert=True)
        return ConversationHandler.END

    await query.answer()
    await query.edit_message_reply_markup(None)
    return await _begin_recap(update, context)


async def _begin_recap(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    for key in RECAP_KEYS:
        context.user_data.pop(key, None)
    async with get_session() as session:
        headings = {section: await pick_recap_heading(session, update.effective_user.id, section) for section in SECTIONS}
    context.user_data["recap_headings"] = {section: (h.id, h.text) for section, h in headings.items()}
    return await _ask_completion(update.effective_chat.send_message)


async def receive_completion(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["recap_completion"] = update.message.text
    await update.message.reply_text(
        "Step 2 of 3\n\n<b>Progress wins</b> // moving something forward\nWhat did you move forward? One per line.",
        parse_mode=ParseMode.HTML,
        reply_markup=_keyboard([InlineKeyboardButton("Skip ➡️", callback_data="recap:skip_progress")], [CANCEL_BUTTON]),
    )
    return AWAITING_PROGRESS


async def _ask_image(chat_send) -> int:
    await chat_send(
        "Step 3 of 3\n\n🖼 Send an image for the post.",
        reply_markup=_keyboard([InlineKeyboardButton("Skip image ➡️", callback_data="recap:skip_image")], [CANCEL_BUTTON]),
    )
    return AWAITING_IMAGE


async def receive_progress(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["recap_progress"] = update.message.text
    return await _ask_image(update.message.reply_text)


async def skip_progress(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.callback_query.answer()
    await update.callback_query.edit_message_reply_markup(None)
    context.user_data["recap_progress"] = ""
    return await _ask_image(update.effective_chat.send_message)


async def _show_preview(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text, _, channel_title = await _recap_text(update.effective_user.id, context.user_data)
    await update.effective_chat.send_message(f"👀 Preview. This is how it will look in {channel_title}:")
    await send_recap(
        context.bot,
        update.effective_chat.id,
        text,
        context.user_data.get("recap_photo"),
        reply_markup=_keyboard(
            [InlineKeyboardButton("✅ Post to channel", callback_data="recap:post", style=KeyboardButtonStyle.SUCCESS)],
            [InlineKeyboardButton("🔄 Start over", callback_data="recap:restart"), CANCEL_BUTTON],
        ),
    )
    return PREVIEW


async def receive_image(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["recap_photo"] = update.message.photo[-1].file_id
    return await _show_preview(update, context)


async def not_an_image(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "Send it as a photo, or skip the image.",
        reply_markup=_keyboard([InlineKeyboardButton("Skip image ➡️", callback_data="recap:skip_image")], [CANCEL_BUTTON]),
    )
    return AWAITING_IMAGE


async def skip_image(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.callback_query.answer()
    await update.callback_query.edit_message_reply_markup(None)
    context.user_data.pop("recap_photo", None)
    return await _show_preview(update, context)


async def post_recap(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    text, channel_id, channel_title = await _recap_text(update.effective_user.id, context.user_data)
    try:
        await send_recap(context.bot, channel_id, text, context.user_data.get("recap_photo"))
    except TelegramError:
        logger.exception("Couldn't post weekly recap to %s", channel_id)
        await query.answer(
            f"I couldn't post to {channel_title}. Make sure I'm an admin there with \"Post messages\" on, then try again.",
            show_alert=True,
        )
        return PREVIEW

    async with get_session() as session:
        heading_ids = [heading_id for heading_id, _ in context.user_data["recap_headings"].values()]
        await mark_recap_headings_used(session, update.effective_user.id, heading_ids)
        await log_activity(session, update.effective_user.id, "recap_post", current_monday())

    await query.answer("Posted ✅")
    await query.edit_message_reply_markup(None)
    for key in RECAP_KEYS:
        context.user_data.pop(key, None)
    await update.effective_chat.send_message(f"Posted to {channel_title} ✅ Have a great week!", reply_markup=MENU_KEYBOARD)
    return ConversationHandler.END


async def restart_recap(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.callback_query.answer()
    await update.callback_query.edit_message_reply_markup(None)
    return await _begin_recap(update, context)


async def cancel_recap(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.callback_query.answer()
    await update.callback_query.edit_message_reply_markup(None)
    for key in RECAP_KEYS:
        context.user_data.pop(key, None)
    await update.effective_chat.send_message("Recap cancelled.", reply_markup=MENU_KEYBOARD)
    return ConversationHandler.END


recap_conversation = ConversationHandler(
    entry_points=[CallbackQueryHandler(recap_start, pattern=r"^week:recap$")],
    states={
        AWAITING_COMPLETION: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_completion)],
        AWAITING_PROGRESS: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, receive_progress),
            CallbackQueryHandler(skip_progress, pattern=r"^recap:skip_progress$"),
        ],
        AWAITING_IMAGE: [
            MessageHandler(filters.PHOTO, receive_image),
            CallbackQueryHandler(skip_image, pattern=r"^recap:skip_image$"),
            MessageHandler(~filters.COMMAND, not_an_image),
        ],
        PREVIEW: [
            CallbackQueryHandler(post_recap, pattern=r"^recap:post$"),
            CallbackQueryHandler(restart_recap, pattern=r"^recap:restart$"),
        ],
    },
    fallbacks=[CallbackQueryHandler(cancel_recap, pattern=r"^recap:cancel$")],
    allow_reentry=True,
)


# --- Monday prompt -----------------------------------------------------------


async def monday_prompt(context: ContextTypes.DEFAULT_TYPE) -> None:
    async with get_session() as session:
        rows = await list_active_weekly_counts(session)

    monday = current_monday()
    for row in rows:
        try:
            await context.bot.send_message(
                row.user_id,
                "🗓 <b>It's Monday!</b>\n\n"
                f"Week <b>{monday.isocalendar().week}</b> [{week_count_for(row, monday)}] starts today.\n"
                f"⏳ {weeks_left_in_year(monday)} weeks left in {monday.year}.\n\n"
                "Ready to write last week's recap?",
                parse_mode=ParseMode.HTML,
                reply_markup=_keyboard(
                    [InlineKeyboardButton("✍️ Write recap", callback_data="week:recap", style=KeyboardButtonStyle.PRIMARY)],
                    [InlineKeyboardButton("Skip this week", callback_data="week:skip")],
                ),
            )
        except Forbidden:
            logger.info("User %s blocked the bot; skipping Monday prompt", row.user_id)
        except TelegramError:
            logger.exception("Couldn't send Monday prompt to %s", row.user_id)


def schedule_monday_prompt(application) -> None:
    application.job_queue.run_daily(monday_prompt, time=MONDAY_PROMPT_TIME, days=(MONDAY,), name="monday_prompt")
