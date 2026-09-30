from telegram import Update
from telegram.ext import ContextTypes

HELP_TEXT = (
    "/start - register and get started\n"
    "/setchannel - connect the channel I should post to (forward a message from it, bot must be admin)\n"
    "/settings - view your current watermark settings\n"
    "/preference - change watermark text, position, opacity, color\n"
    "/post - post your last watermarked photo to your channel\n"
    "Send any photo to get it watermarked.\n\n"
    "/weeklyreport - show weekly recap status\n"
    "/weeklyreport on <number> <bracket> - turn on the Monday recap card\n"
    "/weeklyreport off - turn it off\n\n"
    "/newproject - start tracking a project with a deadline\n"
    "/projects - list your projects\n"
    "/stopproject <id> - stop tracking a project"
)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(HELP_TEXT)
