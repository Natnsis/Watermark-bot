from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models import (
    ChannelWatermark,
    Preference,
    ProgressStyle,
    Project,
    ProjectLogEntry,
    RecapHeading,
    RecapHeadingUse,
    User,
    WeeklyCount,
)


async def get_or_create_user(session: AsyncSession, user_id: int, username: str | None) -> User:
    user = await session.get(User, user_id)
    if user is None:
        user = User(id=user_id, username=username)
        session.add(user)
        await session.commit()
    return user


async def get_or_create_preference(session: AsyncSession, user_id: int, username: str | None = None) -> Preference:
    await get_or_create_user(session, user_id, username)
    result = await session.execute(select(Preference).where(Preference.user_id == user_id))
    pref = result.scalar_one_or_none()
    if pref is None:
        pref = Preference(user_id=user_id)
        session.add(pref)
        await session.commit()
        await session.refresh(pref)
    return pref


# --- channel -----------------------------------------------------------------


async def set_user_channel(session: AsyncSession, user_id: int, channel_id: int, channel_title: str | None) -> User:
    user = await session.get(User, user_id)
    assert user is not None, "get_or_create_user must be called first"
    user.channel_id = channel_id
    user.channel_title = channel_title
    await session.commit()
    return user


# --- weekly report -------------------------------------------------------------


async def enable_weekly_report(session: AsyncSession, user_id: int, start_number: int, start_bracket: int) -> User:
    user = await session.get(User, user_id)
    assert user is not None, "get_or_create_user must be called first"
    user.weekly_enabled = True
    user.weekly_next_number = start_number
    user.weekly_next_bracket = start_bracket
    await session.commit()
    return user


async def disable_weekly_report(session: AsyncSession, user_id: int) -> User:
    user = await session.get(User, user_id)
    assert user is not None, "get_or_create_user must be called first"
    user.weekly_enabled = False
    user.weekly_stage = None
    user.weekly_completion_draft = None
    user.weekly_progress_draft = None
    await session.commit()
    return user


async def start_weekly_stage(session: AsyncSession, user_id: int) -> User:
    user = await session.get(User, user_id)
    assert user is not None, "get_or_create_user must be called first"
    user.weekly_stage = "completion"
    user.weekly_completion_draft = None
    user.weekly_progress_draft = None
    await session.commit()
    return user


async def append_weekly_line(session: AsyncSession, user_id: int, line: str) -> User:
    user = await session.get(User, user_id)
    assert user is not None, "get_or_create_user must be called first"
    if user.weekly_stage == "completion":
        user.weekly_completion_draft = f"{user.weekly_completion_draft or ''}{line}\n"
    elif user.weekly_stage == "progress":
        user.weekly_progress_draft = f"{user.weekly_progress_draft or ''}{line}\n"
    await session.commit()
    return user


async def advance_weekly_stage(session: AsyncSession, user_id: int) -> User:
    user = await session.get(User, user_id)
    assert user is not None, "get_or_create_user must be called first"
    if user.weekly_stage == "completion":
        user.weekly_stage = "progress"
    elif user.weekly_stage == "progress":
        user.weekly_stage = None
    await session.commit()
    return user


async def clear_weekly_draft(session: AsyncSession, user_id: int) -> User:
    user = await session.get(User, user_id)
    assert user is not None, "get_or_create_user must be called first"
    user.weekly_stage = None
    user.weekly_completion_draft = None
    user.weekly_progress_draft = None
    await session.commit()
    return user


async def advance_weekly_counters(session: AsyncSession, user_id: int) -> User:
    user = await session.get(User, user_id)
    assert user is not None, "get_or_create_user must be called first"
    if user.weekly_next_number is not None:
        user.weekly_next_number += 1
    if user.weekly_next_bracket is not None:
        user.weekly_next_bracket += 1
    await session.commit()
    return user


async def users_with_weekly_enabled(session: AsyncSession) -> list[User]:
    result = await session.execute(select(User).where(User.weekly_enabled.is_(True)))
    return list(result.scalars().all())


# --- projects --------------------------------------------------------------


async def create_project(
    session: AsyncSession,
    user_id: int,
    name: str,
    weeks_to_finish: int,
    checkin_interval_weeks: int,
) -> Project:
    today = date.today()
    project = Project(
        user_id=user_id,
        name=name,
        start_date=today,
        end_date=today + timedelta(weeks=weeks_to_finish),
        checkin_interval_weeks=checkin_interval_weeks,
        status="active",
    )
    session.add(project)
    await session.commit()
    await session.refresh(project)
    return project


async def active_projects(session: AsyncSession) -> list[Project]:
    result = await session.execute(select(Project).where(Project.status == "active"))
    return list(result.scalars().all())


async def projects_for_user(session: AsyncSession, user_id: int) -> list[Project]:
    result = await session.execute(select(Project).where(Project.user_id == user_id))
    return list(result.scalars().all())


async def stop_project(session: AsyncSession, project_id: int) -> Project | None:
    project = await session.get(Project, project_id)
    if project is not None:
        project.status = "stopped"
        await session.commit()
    return project


async def get_or_create_log_entry(session: AsyncSession, project_id: int, log_date: date) -> ProjectLogEntry:
    result = await session.execute(
        select(ProjectLogEntry).where(
            ProjectLogEntry.project_id == project_id, ProjectLogEntry.log_date == log_date
        )
    )
    entry = result.scalar_one_or_none()
    if entry is None:
        entry = ProjectLogEntry(project_id=project_id, log_date=log_date)
        session.add(entry)
        await session.commit()
        await session.refresh(entry)
    return entry


async def pending_log_entries(session: AsyncSession, before: date) -> list[ProjectLogEntry]:
    result = await session.execute(
        select(ProjectLogEntry).where(
            ProjectLogEntry.content.is_(None), ProjectLogEntry.log_date < before
        )
    )
    return list(result.scalars().all())


async def record_todays_log(session: AsyncSession, project_id: int, log_date: date, content: str) -> None:
    entry = await get_or_create_log_entry(session, project_id, log_date)
    entry.content = content
    await session.commit()


async def mark_entry_skipped(session: AsyncSession, entry_id: int, joke: str) -> None:
    entry = await session.get(ProjectLogEntry, entry_id)
    assert entry is not None
    entry.content = joke
    entry.is_skipped = True
    await session.commit()


async def entries_since(session: AsyncSession, project_id: int, since: date, until: date) -> list[ProjectLogEntry]:
    result = await session.execute(
        select(ProjectLogEntry)
        .where(
            ProjectLogEntry.project_id == project_id,
            ProjectLogEntry.log_date >= since,
            ProjectLogEntry.log_date <= until,
        )
        .order_by(ProjectLogEntry.log_date)
    )
    return list(result.scalars().all())


def compile_project_report(project: Project, entries: list[ProjectLogEntry]) -> str:
    lines = [f"Project: {project.name}", ""]
    for i, entry in enumerate(entries, start=1):
        marker = "skipped" if entry.is_skipped else "done"
        lines.append(f"Day {i} ({entry.log_date.isoformat()}, {marker}): {entry.content}")
    return "\n".join(lines)


async def set_project_awaiting(session: AsyncSession, user_id: int, project_id: int | None) -> None:
    user = await session.get(User, user_id)
    assert user is not None
    user.awaiting_project_log_id = project_id
    await session.commit()


async def set_last_checkin(session: AsyncSession, project_id: int, checkin_date: date) -> None:
    project = await session.get(Project, project_id)
    assert project is not None
    project.last_checkin_date = checkin_date
    await session.commit()


async def complete_project(session: AsyncSession, project_id: int) -> None:
    project = await session.get(Project, project_id)
    assert project is not None
    project.status = "completed"
    await session.commit()


# --- channel watermark -------------------------------------------------------


async def save_channel(session: AsyncSession, user_id: int, channel_id: int, channel_title: str | None) -> ChannelWatermark:
    row = await session.get(ChannelWatermark, channel_id)
    if row is None:
        row = ChannelWatermark(channel_id=channel_id)
        session.add(row)
    row.user_id = user_id
    row.channel_title = channel_title
    await session.commit()
    return row


async def set_channel_watermark(session: AsyncSession, channel_id: int, watermark_text: str) -> None:
    row = await session.get(ChannelWatermark, channel_id)
    row.watermark_text = watermark_text
    await session.commit()


async def get_channel_watermark(session: AsyncSession, channel_id: int) -> str | None:
    row = await session.get(ChannelWatermark, channel_id)
    return row.watermark_text if row else None


async def get_user_channel(session: AsyncSession, user_id: int) -> ChannelWatermark | None:
    result = await session.execute(
        select(ChannelWatermark)
        .where(ChannelWatermark.user_id == user_id)
        .order_by(ChannelWatermark.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


# --- week count --------------------------------------------------------------


async def get_weekly_count(session: AsyncSession, user_id: int) -> WeeklyCount | None:
    return await session.get(WeeklyCount, user_id)


async def activate_weekly_count(
    session: AsyncSession, user_id: int, start_count: int, start_monday: date
) -> WeeklyCount:
    row = await session.get(WeeklyCount, user_id)
    if row is None:
        row = WeeklyCount(user_id=user_id)
        session.add(row)
    row.start_count = start_count
    row.start_monday = start_monday
    row.active = True
    await session.commit()
    return row


async def deactivate_weekly_count(session: AsyncSession, user_id: int) -> None:
    row = await session.get(WeeklyCount, user_id)
    if row is not None:
        row.active = False
        await session.commit()


async def list_active_weekly_counts(session: AsyncSession) -> list[WeeklyCount]:
    result = await session.execute(select(WeeklyCount).where(WeeklyCount.active.is_(True)))
    return list(result.scalars().all())


# --- recap headings ----------------------------------------------------------


async def seed_recap_headings(session: AsyncSession, headings_by_section: dict[str, list[str]]) -> None:
    existing = set((await session.execute(select(RecapHeading.section, RecapHeading.text))).all())
    for section, headings in headings_by_section.items():
        for text in headings:
            if (section, text) not in existing:
                session.add(RecapHeading(section=section, text=text))
    await session.commit()


async def pick_recap_heading(session: AsyncSession, user_id: int, section: str) -> RecapHeading:
    """Random heading this user hasn't had yet; once all are used, the cycle starts over."""
    used = select(RecapHeadingUse.heading_id).where(RecapHeadingUse.user_id == user_id)
    query = select(RecapHeading).where(RecapHeading.section == section).order_by(func.random()).limit(1)

    heading = (await session.execute(query.where(RecapHeading.id.not_in(used)))).scalar_one_or_none()
    if heading is None:
        section_ids = select(RecapHeading.id).where(RecapHeading.section == section)
        await session.execute(
            delete(RecapHeadingUse).where(RecapHeadingUse.user_id == user_id, RecapHeadingUse.heading_id.in_(section_ids))
        )
        await session.commit()
        heading = (await session.execute(query)).scalar_one()
    return heading


async def mark_recap_headings_used(session: AsyncSession, user_id: int, heading_ids: list[int]) -> None:
    for heading_id in heading_ids:
        await session.merge(RecapHeadingUse(user_id=user_id, heading_id=heading_id))
    await session.commit()


# --- year progress style -----------------------------------------------------


async def get_progress_style(session: AsyncSession, user_id: int) -> str | None:
    row = await session.get(ProgressStyle, user_id)
    return row.style if row else None


async def get_progress_settings(session: AsyncSession, user_id: int) -> ProgressStyle | None:
    return await session.get(ProgressStyle, user_id)


async def _get_or_create_progress_settings(session: AsyncSession, user_id: int) -> ProgressStyle:
    row = await session.get(ProgressStyle, user_id)
    if row is None:
        row = ProgressStyle(user_id=user_id, schedule="off")
        session.add(row)
    return row


async def set_progress_style(session: AsyncSession, user_id: int, style: str) -> None:
    row = await _get_or_create_progress_settings(session, user_id)
    row.style = style
    await session.commit()


async def set_progress_schedule(session: AsyncSession, user_id: int, schedule: str) -> None:
    row = await _get_or_create_progress_settings(session, user_id)
    row.schedule = schedule
    await session.commit()


async def set_last_posted_percent(session: AsyncSession, user_id: int, percent: int) -> None:
    row = await _get_or_create_progress_settings(session, user_id)
    row.last_posted_percent = percent
    await session.commit()


async def list_scheduled_progress(session: AsyncSession) -> list[ProgressStyle]:
    result = await session.execute(select(ProgressStyle).where(ProgressStyle.schedule != "off"))
    return list(result.scalars().all())
