import html
import logging
from datetime import date, datetime, time

from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import KeyboardButtonStyle, ParseMode
from telegram.error import TelegramError
from telegram.ext import CallbackQueryHandler, ContextTypes

from config import TIMEZONE
from db import get_session
from handlers.start import back_to_menu_button
from services import (
    get_progress_settings,
    get_user_channel,
    list_scheduled_progress,
    log_activity,
    set_last_posted_percent,
    set_progress_schedule,
    set_progress_style,
)
from year_progress import DEFAULT_STYLE, STYLES, percent_done, render

logger = logging.getLogger(__name__)

POST_TIME = time(9, 0, tzinfo=TIMEZONE)

# key -> (button label, description on the Progress screen)
SCHEDULES = {
    "off": ("⏸ Off", "Off"),
    "daily": ("Every day", "Every day at 9:00"),
    "weekly": ("Every Monday", "Every Monday at 9:00"),
    "monthly": ("Every month", "1st of every month at 9:00"),
    "percent": ("Every 1%", "Each time the year passes another 1%"),
}

LOCKED_ALERT = "🔒 Set up your channel with 🖼 Watermark first to unlock this."


def _today() -> date:
    return datetime.now(TIMEZONE).date()


def build_progress_post(style: str | None, day: date, watermark: str | None) -> str:
    text = f"<b>{day.year}</b>\n{html.escape(render(style, day))}"
    if watermark:
        text += f"\n\n{html.escape(watermark)}"
    return text


async def post_progress(bot: Bot, user_id: int) -> str:
    """Posts the year progress to the user's channel and returns the channel title."""
    async with get_session() as session:
        channel = await get_user_channel(session, user_id)
        settings = await get_progress_settings(session, user_id)
        today = _today()
        await bot.send_message(
            channel.channel_id,
            build_progress_post(settings.style if settings else None, today, channel.watermark_text),
            parse_mode=ParseMode.HTML,
        )
        await set_last_posted_percent(session, user_id, percent_done(today))
        await log_activity(session, user_id, "progress_post")
    return channel.channel_title or str(channel.channel_id)


# --- screens -----------------------------------------------------------------


def _main_screen(style: str, schedule: str, channel_title: str) -> tuple[str, InlineKeyboardMarkup]:
    text = (
        "📈 <b>Year progress</b>\n\n"
        f"{html.escape(render(style, _today()))}\n\n"
        f"{html.escape(STYLES[style][0])}\n"
        f"⏰ {SCHEDULES[schedule][1]}\n"
        f"📢 {html.escape(channel_title)}"
    )
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("🎨 Style", callback_data="prog:styles"),
                InlineKeyboardButton("⏰ Schedule", callback_data="prog:schedule"),
            ],
            [InlineKeyboardButton("📤 Post now", callback_data="prog:post", style=KeyboardButtonStyle.SUCCESS)],
            [back_to_menu_button()],
        ]
    )
    return text, keyboard


def _styles_screen(selected: str) -> tuple[str, InlineKeyboardMarkup]:
    today = _today()
    previews = "\n\n".join(
        f"<b>{html.escape(label)}</b>\n{html.escape(render(key, today))}" for key, (label, _) in STYLES.items()
    )
    buttons = [
        InlineKeyboardButton(f"✅ {label}" if key == selected else label, callback_data=f"prog:style:{key}")
        for key, (label, _) in STYLES.items()
    ]
    rows = [buttons[i : i + 3] for i in range(0, len(buttons), 3)]
    rows.append([InlineKeyboardButton("⬅️ Back", callback_data="prog:open")])
    return f"🎨 <b>Pick a style</b>\n\n{previews}", InlineKeyboardMarkup(rows)


def _schedule_screen(selected: str) -> tuple[str, InlineKeyboardMarkup]:
    buttons = [
        InlineKeyboardButton(f"✅ {label}" if key == selected else label, callback_data=f"prog:every:{key}")
        for key, (label, _) in SCHEDULES.items()
    ]
    rows = [[buttons[0]], buttons[1:3], buttons[3:5], [InlineKeyboardButton("⬅️ Back", callback_data="prog:open")]]
    return "⏰ <b>How often should I post it to your channel?</b>", InlineKeyboardMarkup(rows)


async def progress_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user_id = update.effective_user.id
    action, _, value = query.data.removeprefix("prog:").partition(":")

    async with get_session() as session:
        channel = await get_user_channel(session, user_id)
        if channel is None:
            await query.answer(LOCKED_ALERT, show_alert=True)
            return

        settings = await get_progress_settings(session, user_id)
        style = (settings.style if settings else None) or DEFAULT_STYLE
        schedule = settings.schedule if settings else "off"

        if action == "style" and value in STYLES:
            await set_progress_style(session, user_id, value)
            await query.answer(f"{STYLES[value][0]} selected")
            # Right after picking a style, ask how often to post it.
            text, keyboard = _schedule_screen(schedule)
        elif action == "every" and value in SCHEDULES:
            await set_progress_schedule(session, user_id, value)
            await query.answer("Saved ✅")
            text, keyboard = _main_screen(style, value, channel.channel_title or str(channel.channel_id))
        elif action == "styles":
            await query.answer()
            text, keyboard = _styles_screen(style)
        elif action == "schedule":
            await query.answer()
            text, keyboard = _schedule_screen(schedule)
        elif action == "post":
            try:
                channel_title = await post_progress(context.bot, user_id)
            except TelegramError:
                logger.exception("Couldn't post year progress for %s", user_id)
                await query.answer('I couldn\'t post. Make sure I\'m an admin with "Post messages" on.', show_alert=True)
                return
            await query.answer(f"Posted to {channel_title} ✅")
            return
        else:
            await query.answer()
            text, keyboard = _main_screen(style, schedule, channel.channel_title or str(channel.channel_id))

    await query.edit_message_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)


progress_handler = CallbackQueryHandler(progress_callback, pattern=r"^prog:")


# --- scheduled posts ---------------------------------------------------------


def _is_due(schedule: str, today: date, last_posted_percent: int | None) -> bool:
    if schedule == "daily":
        return True
    if schedule == "weekly":
        return today.weekday() == 0
    if schedule == "monthly":
        return today.day == 1
    if schedule == "percent":
        return last_posted_percent is None or percent_done(today) != last_posted_percent
    return False


async def scheduled_progress_posts(context: ContextTypes.DEFAULT_TYPE) -> None:
    async with get_session() as session:
        rows = await list_scheduled_progress(session)

    today = _today()
    for row in rows:
        if not _is_due(row.schedule, today, row.last_posted_percent):
            continue
        try:
            await post_progress(context.bot, row.user_id)
        except Exception:
            logger.exception("Scheduled year progress post failed for %s", row.user_id)


def schedule_progress_posts(application) -> None:
    application.job_queue.run_daily(scheduled_progress_posts, time=POST_TIME, name="progress_posts")
