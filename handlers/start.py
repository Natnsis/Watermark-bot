from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import KeyboardButtonStyle
from telegram.ext import ContextTypes

from db import get_session
from services import get_user_channel

MENU_TEXT = "hello\n\nChoose an option:"


async def build_menu(user_id: int) -> InlineKeyboardMarkup:
    async with get_session() as session:
        has_channel = await get_user_channel(session, user_id) is not None

    if has_channel:
        week_button = InlineKeyboardButton("📅 Week Count", callback_data="week:open", style=KeyboardButtonStyle.SUCCESS)
        progress_button = InlineKeyboardButton("📈 Progress", callback_data="prog:open", style=KeyboardButtonStyle.SUCCESS)
        stats_button = InlineKeyboardButton("📊 Stat Teller", callback_data="stats:open", style=KeyboardButtonStyle.PRIMARY)
    else:
        week_button = InlineKeyboardButton("🔒 Week Count", callback_data="menu:locked")
        progress_button = InlineKeyboardButton("🔒 Progress", callback_data="menu:locked")
        stats_button = InlineKeyboardButton("🔒 Stat Teller", callback_data="menu:locked")

    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("🖼 Watermark", callback_data="menu:watermark", style=KeyboardButtonStyle.PRIMARY),
                week_button,
            ],
            [
                progress_button,
                stats_button,
            ],
        ]
    )


def back_to_menu_button() -> InlineKeyboardButton:
    return InlineKeyboardButton("⬅️ Menu", callback_data="menu:home")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(MENU_TEXT, reply_markup=await build_menu(update.effective_user.id))


async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query.data == "menu:home":
        await query.answer()
        await query.edit_message_text(MENU_TEXT, reply_markup=await build_menu(update.effective_user.id))
    elif query.data == "menu:locked":
        await query.answer("🔒 Set up your channel with 🖼 Watermark first to unlock this.", show_alert=True)
    else:
        # A button from an older version of the menu: swap in the current menu.
        await query.answer("Menu updated, tap again")
        await query.edit_message_text(MENU_TEXT, reply_markup=await build_menu(update.effective_user.id))


async def expired_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.callback_query.answer("This button has expired.")
