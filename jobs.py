from __future__ import annotations

import logging
import random
from datetime import date, datetime, time, timedelta

from telegram.error import TelegramError
from telegram.ext import Application, ContextTypes

from config import TIMEZONE
from db import get_session
from models import User
from report_image import render_weekly_card
import services

logger = logging.getLogger(__name__)

SKIPPED_JOKES = [
    "Did absolutely nothing. Professional-grade procrastination.",
    "Took the day off from ambition entirely.",
    "Skipped like a stone across a very still lake.",
    "Went completely dark. Even the todo list gave up looking.",
    "Achieved a personal best in doing nothing.",
    "Rested. Deeply. Suspiciously deeply.",
    "Chose vibes over velocity today.",
    "Nothing to report — the project took a nap too.",
]


def _today() -> date:
    return datetime.now(TIMEZONE).date()


def register_jobs(application: Application) -> None:
    jq = application.job_queue
    jq.run_daily(send_weekly_prompt, time=time(18, 0, tzinfo=TIMEZONE), days=(6,), name="weekly_prompt")
    jq.run_daily(post_weekly_report, time=time(9, 0, tzinfo=TIMEZONE), days=(0,), name="weekly_post")
    jq.run_daily(
        daily_project_checkin, time=time(20, 0, tzinfo=TIMEZONE), days=tuple(range(7)), name="project_checkin"
    )


async def send_weekly_prompt(context: ContextTypes.DEFAULT_TYPE) -> None:
    async with get_session() as session:
        users = await services.users_with_weekly_enabled(session)
        for user in users:
            await services.start_weekly_stage(session, user.id)
            try:
                await context.bot.send_message(
                    chat_id=user.id,
                    text=(
                        "Time for this week's recap!\n\n"
                        "Send your *Completion wins* (closing loops), one per line. "
                        "Send /next when you're done with this section."
                    ),
                    parse_mode="Markdown",
                )
            except TelegramError:
                logger.warning("Could not DM user %s for weekly prompt", user.id)


async def post_weekly_report(context: ContextTypes.DEFAULT_TYPE) -> None:
    async with get_session() as session:
        users = await services.users_with_weekly_enabled(session)
        for user in users:
            if user.weekly_stage is not None or not user.weekly_completion_draft:
                try:
                    await context.bot.send_message(
                        chat_id=user.id,
                        text="You didn't finish this week's recap in time, so nothing was posted. Next Sunday I'll ask again.",
                    )
                except TelegramError:
                    logger.warning("Could not DM user %s about a skipped weekly report", user.id)
                await services.clear_weekly_draft(session, user.id)
                continue

            if not user.channel_id:
                try:
                    await context.bot.send_message(
                        chat_id=user.id,
                        text="Your recap is ready but you haven't set a channel yet. Use /setchannel, then I'll post it next week.",
                    )
                except TelegramError:
                    logger.warning("Could not DM user %s about missing channel", user.id)
                continue

            completion = [line for line in (user.weekly_completion_draft or "").splitlines() if line.strip()]
            progress = [line for line in (user.weekly_progress_draft or "").splitlines() if line.strip()]
            image_bytes = render_weekly_card(
                user.weekly_next_number, user.weekly_next_bracket, completion, progress
            )

            try:
                await context.bot.send_photo(chat_id=user.channel_id, photo=image_bytes)
            except TelegramError:
                logger.exception("Failed to post weekly report for user %s", user.id)
                continue

            await services.advance_weekly_counters(session, user.id)
            await services.clear_weekly_draft(session, user.id)


async def daily_project_checkin(context: ContextTypes.DEFAULT_TYPE) -> None:
    today = _today()
    yesterday = today - timedelta(days=1)

    async with get_session() as session:
        pending = await services.pending_log_entries(session, before=today)
        for entry in pending:
            await services.mark_entry_skipped(session, entry.id, random.choice(SKIPPED_JOKES))

        for project in await services.active_projects(session):
            user = await session.get(User, project.user_id)
            if user is None:
                continue

            if today > project.end_date:
                since = (
                    project.last_checkin_date + timedelta(days=1)
                    if project.last_checkin_date
                    else project.start_date
                )
                entries = await services.entries_since(session, project.id, since, project.end_date)
                report = services.compile_project_report(project, entries) + "\n\nProject complete!"
                if user.channel_id:
                    try:
                        await context.bot.send_message(chat_id=user.channel_id, text=report)
                    except TelegramError:
                        logger.exception("Failed to post final report for project %s", project.id)
                await services.complete_project(session, project.id)
                continue

            day_number = (today - project.start_date).days + 1
            await services.get_or_create_log_entry(session, project.id, today)
            await services.set_project_awaiting(session, user.id, project.id)
            try:
                await context.bot.send_message(
                    chat_id=user.id,
                    text=f"Project '{project.name}' — Day {day_number}: what did you do today?",
                )
            except TelegramError:
                logger.warning("Could not DM user %s for project checkin", user.id)

            last = project.last_checkin_date or project.start_date
            next_checkin = last + timedelta(weeks=project.checkin_interval_weeks)
            since = (project.last_checkin_date + timedelta(days=1)) if project.last_checkin_date else project.start_date
            if today >= next_checkin and yesterday >= since and user.channel_id:
                entries = await services.entries_since(session, project.id, since, yesterday)
                report = services.compile_project_report(project, entries)
                try:
                    await context.bot.send_message(chat_id=user.channel_id, text=report)
                except TelegramError:
                    logger.exception("Failed to post checkin report for project %s", project.id)
                await services.set_last_checkin(session, project.id, yesterday)
