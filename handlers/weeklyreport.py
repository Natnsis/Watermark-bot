from telegram import Update
from telegram.ext import ContextTypes

from db import get_session
from services import disable_weekly_report, enable_weekly_report, get_or_create_user


async def weeklyreport_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    tg_user = update.effective_user
    args = context.args

    async with get_session() as session:
        user = await get_or_create_user(session, tg_user.id, tg_user.username)

        if not args:
            if user.weekly_enabled:
                await update.message.reply_text(
                    "Weekly recap is ON.\n"
                    f"Next post will be week {user.weekly_next_number} [{user.weekly_next_bracket}].\n"
                    "Send `/weeklyreport off` to disable."
                )
            else:
                await update.message.reply_text(
                    "Weekly recap is OFF.\n"
                    "Turn it on with `/weeklyreport on <week_number> <bracket_number>`, "
                    "e.g. `/weeklyreport on 39 91` — these are the numbers your *next* post should show."
                )
            return

        if args[0] == "off":
            await disable_weekly_report(session, tg_user.id)
            await update.message.reply_text("Weekly recap turned off.")
            return

        if args[0] == "on" and len(args) == 3 and args[1].isdigit() and args[2].isdigit():
            await enable_weekly_report(session, tg_user.id, int(args[1]), int(args[2]))
            await update.message.reply_text(
                f"Weekly recap turned on, starting at week {args[1]} [{args[2]}].\n"
                "Every Sunday evening I'll ask for your wins, and post the card every Monday morning."
            )
            return

    await update.message.reply_text("Usage: /weeklyreport, /weeklyreport on <number> <bracket>, /weeklyreport off")
