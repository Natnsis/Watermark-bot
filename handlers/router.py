from datetime import datetime

from telegram import Update
from telegram.ext import ContextTypes

from config import TIMEZONE
from db import get_session
from services import (
    advance_weekly_stage,
    append_weekly_line,
    get_or_create_user,
    record_todays_log,
    set_project_awaiting,
)


async def generic_text_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    tg_user = update.effective_user
    text = update.message.text.strip()

    async with get_session() as session:
        user = await get_or_create_user(session, tg_user.id, tg_user.username)

        if user.weekly_stage is not None:
            if text == "/next" and user.weekly_stage == "completion":
                await advance_weekly_stage(session, tg_user.id)
                await update.message.reply_text(
                    "Now send your *Progress wins* (moving something forward), one per line. "
                    "Send /done when finished.",
                    parse_mode="Markdown",
                )
                return
            if text == "/done" and user.weekly_stage == "progress":
                await advance_weekly_stage(session, tg_user.id)
                await update.message.reply_text("Recap saved. I'll post it Monday morning.")
                return
            await append_weekly_line(session, tg_user.id, text)
            await update.message.reply_text("Added.")
            return

        if user.awaiting_project_log_id is not None:
            today = datetime.now(TIMEZONE).date()
            await record_todays_log(session, user.awaiting_project_log_id, today, text)
            await set_project_awaiting(session, tg_user.id, None)
            await update.message.reply_text("Logged. See you tomorrow.")
            return

    await update.message.reply_text("Not sure what to do with that. Try /help for commands.")
