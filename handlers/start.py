import html
import logging

from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup, Update, User
from telegram.constants import KeyboardButtonStyle, ParseMode
from telegram.error import TelegramError
from telegram.ext import ContextTypes

from db import get_session
from services import get_user_channel

logger = logging.getLogger(__name__)

# Shown on the bot's profile and when the bot is shared (max 120 characters).
SHORT_DESCRIPTION = (
    "Build in public on Telegram: auto-watermark your channel, weekly recaps, year progress posts and streak stats."
)

# Shown in an empty chat before the user presses Start (max 512 characters).
DESCRIPTION = (
    "Poster Boi helps devs and content creators build in public on Telegram.\n\n"
    "🖼 Auto-sign every channel post with your watermark\n"
    "📅 Monday recaps: what you shipped and what's moving\n"
    "📈 Year progress posts in 9 styles\n"
    "📊 Streaks, attendance and activity stats\n\n"
    "Add me as an admin to your channel, press Start and you're set up in a minute."
)

HELP_TEXT = (
    "📖 <b>How Poster Boi works</b>\n\n"
    "<b>1. Connect your channel</b> · 🖼 Watermark\n"
    "• Add me to your channel as an admin with <i>Post messages</i> and <i>Edit messages</i> on.\n"
    "• Tap 🖼 Watermark, then forward any post from the channel or send its @username.\n"
    "• Send the text to sign your posts with, like your @handle.\n"
    "From then on every new post (text, photo, video, file…) gets it added at the end. "
    "Older posts aren't touched.\n\n"
    "<b>2. Weekly recap</b> · 📅 Week Count\n"
    "• Turn it on and pick where the count starts: week 1, or the number you're already at.\n"
    "• Every Monday at 9:00 I'll ask about your last week: what you finished, what you moved forward, and a photo.\n"
    "• You see a preview first. Nothing goes out until you tap ✅ Post.\n"
    "• Section headings are picked at random from 300, so no two weeks look the same.\n"
    "Missed Monday? Tap ✍️ Write recap now any time that week.\n\n"
    "<b>3. Year progress</b> · 📈 Progress\n"
    "• Pick a style: bar, moons, week grid, countdown and more.\n"
    "• Choose how often I post it: daily, Mondays, monthly, or every 1%.\n"
    "• 📤 Post now sends it right away. Your style also appears in the weekly recap.\n\n"
    "<b>4. Your stats</b> · 📊 Stat Teller\n"
    "• Weeks posted vs missed, your streak, progress posts, and how active you are next to other users.\n"
    "• 📤 Post to channel shares them when you want to flex.\n\n"
    "<b>Good to know</b>\n"
    "• 🔒 buttons unlock once your channel is connected.\n"
    "• Only admins of a channel can set it up.\n"
    "• ⬅️ Menu brings you back from anywhere."
)


def _menu_text(user: User, channel_title: str | None) -> str:
    intro = (
        f"👋 <b>Hey {html.escape(user.first_name)}!</b>\n\n"
        "I'm <b>Poster Boi</b>, your sidekick for building in public on Telegram.\n\n"
        "🖼 <b>Watermark</b> signs every post in your channel\n"
        "📅 <b>Week Count</b> turns Mondays into a weekly recap\n"
        "📈 <b>Progress</b> posts how far through the year you are\n"
        "📊 <b>Stat Teller</b> shows how consistent you've been\n\n"
    )
    if channel_title:
        return intro + f"📢 Connected to <b>{html.escape(channel_title)}</b>"
    return intro + "👉 Start with <b>🖼 Watermark</b> to connect your channel. That unlocks everything else."


async def render_menu(user: User) -> tuple[str, InlineKeyboardMarkup]:
    async with get_session() as session:
        channel = await get_user_channel(session, user.id)

    if channel is not None:
        week_button = InlineKeyboardButton("📅 Week Count", callback_data="week:open", style=KeyboardButtonStyle.SUCCESS)
        progress_button = InlineKeyboardButton("📈 Progress", callback_data="prog:open", style=KeyboardButtonStyle.SUCCESS)
        stats_button = InlineKeyboardButton("📊 Stat Teller", callback_data="stats:open", style=KeyboardButtonStyle.PRIMARY)
    else:
        week_button = InlineKeyboardButton("🔒 Week Count", callback_data="menu:locked")
        progress_button = InlineKeyboardButton("🔒 Progress", callback_data="menu:locked")
        stats_button = InlineKeyboardButton("🔒 Stat Teller", callback_data="menu:locked")

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("🖼 Watermark", callback_data="menu:watermark", style=KeyboardButtonStyle.PRIMARY),
                week_button,
            ],
            [progress_button, stats_button],
            [InlineKeyboardButton("❓ How it works", callback_data="menu:help")],
        ]
    )
    channel_title = (channel.channel_title or str(channel.channel_id)) if channel else None
    return _menu_text(user, channel_title), keyboard


def back_to_menu_button() -> InlineKeyboardButton:
    return InlineKeyboardButton("⬅️ Menu", callback_data="menu:home")


HELP_KEYBOARD = InlineKeyboardMarkup([[back_to_menu_button()]])


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text, keyboard = await render_menu(update.effective_user)
    await update.message.reply_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(HELP_TEXT, reply_markup=HELP_KEYBOARD, parse_mode=ParseMode.HTML)


async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query.data == "menu:locked":
        await query.answer("🔒 Set up your channel with 🖼 Watermark first to unlock this.", show_alert=True)
        return
    if query.data == "menu:help":
        await query.answer()
        await query.edit_message_text(HELP_TEXT, reply_markup=HELP_KEYBOARD, parse_mode=ParseMode.HTML)
        return

    if query.data == "menu:home":
        await query.answer()
    else:
        # A button from an older version of the menu: swap in the current menu.
        await query.answer("Menu updated, tap again")
    text, keyboard = await render_menu(update.effective_user)
    await query.edit_message_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)


async def expired_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.callback_query.answer("This button has expired.")


async def update_bot_profile(bot: Bot) -> None:
    """Keeps the bot's Telegram description in sync with the code."""
    try:
        if (await bot.get_my_short_description()).short_description != SHORT_DESCRIPTION:
            await bot.set_my_short_description(SHORT_DESCRIPTION)
        if (await bot.get_my_description()).description != DESCRIPTION:
            await bot.set_my_description(DESCRIPTION)
    except TelegramError:
        logger.exception("Couldn't update the bot description")
