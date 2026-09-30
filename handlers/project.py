from telegram import Update
from telegram.ext import CommandHandler, ContextTypes, ConversationHandler, MessageHandler, filters

from db import get_session
from services import create_project, get_or_create_user, projects_for_user, stop_project

NAME, WEEKS, INTERVAL = range(3)


async def newproject_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("What's the project called?")
    return NAME


async def receive_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["project_name"] = update.message.text.strip()
    await update.message.reply_text("How many weeks until you want it finished? (send a number)")
    return WEEKS


async def receive_weeks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    if not text.isdigit() or int(text) < 1:
        await update.message.reply_text("Send a whole number of weeks, e.g. 8.")
        return WEEKS
    context.user_data["project_weeks"] = int(text)
    await update.message.reply_text(
        "How often should I post a compiled check-in report to your channel? (in weeks, e.g. 4)"
    )
    return INTERVAL


async def receive_interval(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    if not text.isdigit() or int(text) < 1:
        await update.message.reply_text("Send a whole number of weeks, e.g. 4.")
        return INTERVAL

    tg_user = update.effective_user
    async with get_session() as session:
        await get_or_create_user(session, tg_user.id, tg_user.username)
        project = await create_project(
            session,
            tg_user.id,
            context.user_data["project_name"],
            context.user_data["project_weeks"],
            int(text),
        )

    await update.message.reply_text(
        f"Project '{project.name}' started. Deadline: {project.end_date}.\n"
        "I'll DM you every evening asking what you did, and post a compiled report to your channel "
        f"every {text} week(s)."
    )
    context.user_data.clear()
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    await update.message.reply_text("Cancelled.")
    return ConversationHandler.END


async def projects_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    tg_user = update.effective_user
    async with get_session() as session:
        projects = await projects_for_user(session, tg_user.id)

    if not projects:
        await update.message.reply_text("No projects yet. Start one with /newproject.")
        return

    lines = []
    for p in projects:
        lines.append(f"#{p.id} {p.name} — {p.status}, deadline {p.end_date}, check-in every {p.checkin_interval_weeks}w")
    await update.message.reply_text("\n".join(lines))


async def stopproject_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text("Usage: /stopproject <id> (see /projects for ids)")
        return

    async with get_session() as session:
        project = await stop_project(session, int(context.args[0]))

    if project is None:
        await update.message.reply_text("No project with that id.")
    else:
        await update.message.reply_text(f"Stopped '{project.name}'.")


newproject_conversation = ConversationHandler(
    entry_points=[CommandHandler("newproject", newproject_start)],
    states={
        NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_name)],
        WEEKS: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_weeks)],
        INTERVAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_interval)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)
