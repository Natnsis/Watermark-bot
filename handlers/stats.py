import html
import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import KeyboardButtonStyle, ParseMode
from telegram.error import BadRequest, TelegramError
from telegram.ext import CallbackQueryHandler, ContextTypes

from config import TIMEZONE
from db import get_session
from handlers.progress import SCHEDULES
from handlers.start import back_to_menu_button
from handlers.week_count import current_monday, week_count_for
from services import (
    count_activity,
    count_users_with_channel,
    get_progress_settings,
    get_recap_weeks,
    get_user_channel,
    get_weekly_count,
)

logger = logging.getLogger(__name__)

ACTIVITY_WINDOW = timedelta(days=30)
LOCKED_ALERT = "🔒 Set up your channel with 🖼 Watermark first to unlock this."


@dataclass
class WeekStats:
    count: int
    since: date
    posted: int
    missed: int
    streak: int

    @property
    def attendance(self) -> int | None:
        total = self.posted + self.missed
        return round(self.posted / total * 100) if total else None


@dataclass
class Stats:
    channel_title: str
    watermark: str | None
    week: WeekStats | None
    progress_total: int
    progress_recent: int
    progress_schedule: str
    my_recent: int
    average_recent: float


def compute_week_stats(start_monday: date, start_count: int, this_monday: date, posted_weeks: set[date]) -> WeekStats:
    """Past weeks without a recap count as missed; the current week only counts once it's posted."""
    weeks = [start_monday + timedelta(weeks=i) for i in range((this_monday - start_monday).days // 7 + 1)]
    past_weeks = weeks[:-1]
    posted = sum(1 for week in weeks if week in posted_weeks)
    missed = sum(1 for week in past_weeks if week not in posted_weeks)

    streak = 0
    cursor = this_monday if this_monday in posted_weeks else this_monday - timedelta(weeks=1)
    while cursor >= start_monday and cursor in posted_weeks:
        streak += 1
        cursor -= timedelta(weeks=1)

    count = start_count + (this_monday - start_monday).days // 7
    return WeekStats(count=count, since=start_monday, posted=posted, missed=missed, streak=streak)


async def gather_stats(user_id: int) -> Stats | None:
    since = datetime.now(TIMEZONE) - ACTIVITY_WINDOW
    async with get_session() as session:
        channel = await get_user_channel(session, user_id)
        if channel is None:
            return None
        weekly = await get_weekly_count(session, user_id)
        progress = await get_progress_settings(session, user_id)

        week = None
        if weekly is not None and weekly.active:
            week = compute_week_stats(
                weekly.start_monday, weekly.start_count, current_monday(), await get_recap_weeks(session, user_id)
            )

        users = await count_users_with_channel(session)
        return Stats(
            channel_title=channel.channel_title or str(channel.channel_id),
            watermark=channel.watermark_text,
            week=week,
            progress_total=await count_activity(session, user_id, "progress_post"),
            progress_recent=await count_activity(session, user_id, "progress_post", since),
            progress_schedule=progress.schedule if progress else "off",
            my_recent=await count_activity(session, user_id, since=since),
            average_recent=(await count_activity(session, since=since)) / users if users else 0,
        )


def _plural(n: int, word: str) -> str:
    return f"{n} {word}{'' if n == 1 else 's'}"


def _comparison(mine: int, average: float) -> str:
    if average == 0:
        return "No activity yet. Post something to get on the board."
    ratio = mine / average
    if ratio >= 1.5:
        return f"{ratio:.1f}× the average 🚀"
    if ratio > 1.05:
        return "Above average 💪"
    if ratio >= 0.95:
        return "Right on average"
    return "Below average. A post or two would change that."


def _week_lines(week: WeekStats) -> list[str]:
    lines = [f"Week [{week.count}] · since {week.since:%d %b %Y}"]
    if week.attendance is None:
        lines.append("No weeks finished yet")
    else:
        lines.append(f"✅ {week.posted} posted · ❌ {week.missed} missed · {week.attendance}% attendance")
    lines.append(f"🔥 Streak: {_plural(week.streak, 'week')}")
    return lines


def render_stats_screen(stats: Stats) -> str:
    parts = ["📊 <b>Your stats</b>"]

    week_section = ["📅 <b>Week Count</b>"]
    week_section += _week_lines(stats.week) if stats.week else ["Off"]
    parts.append("\n".join(week_section))

    parts.append(
        "📈 <b>Progress</b>\n"
        f"{_plural(stats.progress_total, 'post')} · {stats.progress_recent} in the last 30 days\n"
        f"⏰ {SCHEDULES[stats.progress_schedule][1]}"
    )
    parts.append(
        "⚡ <b>Activity, last 30 days</b>\n"
        f"You: {_plural(stats.my_recent, 'post')} · Average: {stats.average_recent:.1f}\n"
        f"{_comparison(stats.my_recent, stats.average_recent)}"
    )
    return "\n\n".join(parts)


def render_stats_post(stats: Stats) -> str:
    lines = ["📊 <b>Stats</b>", ""]
    if stats.week:
        lines += _week_lines(stats.week)
    lines.append(f"📈 {_plural(stats.progress_total, 'progress post')}")
    if stats.average_recent and stats.my_recent / stats.average_recent >= 1.5:
        lines.append(f"⚡ {stats.my_recent / stats.average_recent:.1f}× more active than average")
    if stats.watermark:
        lines += ["", html.escape(stats.watermark)]
    return "\n".join(lines)


STATS_KEYBOARD = InlineKeyboardMarkup(
    [
        [InlineKeyboardButton("📤 Post to channel", callback_data="stats:post", style=KeyboardButtonStyle.SUCCESS)],
        [back_to_menu_button()],
    ]
)


async def stats_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user_id = update.effective_user.id
    stats = await gather_stats(user_id)
    if stats is None:
        await query.answer(LOCKED_ALERT, show_alert=True)
        return

    if query.data == "stats:post":
        async with get_session() as session:
            channel = await get_user_channel(session, user_id)
        try:
            await context.bot.send_message(channel.channel_id, render_stats_post(stats), parse_mode=ParseMode.HTML)
        except TelegramError:
            logger.exception("Couldn't post stats for %s", user_id)
            await query.answer('I couldn\'t post. Make sure I\'m an admin with "Post messages" on.', show_alert=True)
            return
        await query.answer(f"Posted to {stats.channel_title} ✅")
        return

    await query.answer()
    try:
        await query.edit_message_text(render_stats_screen(stats), reply_markup=STATS_KEYBOARD, parse_mode=ParseMode.HTML)
    except BadRequest as exc:
        if "not modified" not in exc.message:
            raise


stats_handler = CallbackQueryHandler(stats_callback, pattern=r"^stats:(open|post)$")
