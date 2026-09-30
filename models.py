from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)

    channel_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    channel_title: Mapped[str | None] = mapped_column(String(255), nullable=True)

    weekly_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    weekly_next_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    weekly_next_bracket: Mapped[int | None] = mapped_column(Integer, nullable=True)
    weekly_stage: Mapped[str | None] = mapped_column(String(20), nullable=True)
    weekly_completion_draft: Mapped[str | None] = mapped_column(Text, nullable=True)
    weekly_progress_draft: Mapped[str | None] = mapped_column(Text, nullable=True)

    awaiting_project_log_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("projects.id"), nullable=True
    )

    preference: Mapped["Preference"] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )


class Preference(Base):
    __tablename__ = "preferences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), unique=True)
    watermark_text: Mapped[str] = mapped_column(String(255), default="@YourBrand")
    position: Mapped[str] = mapped_column(String(20), default="bottom-right")
    opacity: Mapped[float] = mapped_column(Float, default=0.6)
    font_size: Mapped[int] = mapped_column(Integer, default=32)
    color: Mapped[str] = mapped_column(String(20), default="#FFFFFF")

    user: Mapped["User"] = relationship(back_populates="preference")


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    name: Mapped[str] = mapped_column(String(255))
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    checkin_interval_weeks: Mapped[int] = mapped_column(Integer)
    last_checkin_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    entries: Mapped[list["ProjectLogEntry"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )


class ProjectLogEntry(Base):
    __tablename__ = "project_log_entries"
    __table_args__ = (UniqueConstraint("project_id", "log_date", name="uq_project_log_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(Integer, ForeignKey("projects.id"))
    log_date: Mapped[date] = mapped_column(Date)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_skipped: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    project: Mapped["Project"] = relationship(back_populates="entries")


class ChannelWatermark(Base):
    __tablename__ = "channel_watermarks"

    channel_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    channel_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    watermark_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class WeeklyCount(Base):
    __tablename__ = "weekly_counts"

    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    # The week that started on `start_monday` is week number `start_count`.
    start_count: Mapped[int] = mapped_column(Integer)
    start_monday: Mapped[date] = mapped_column(Date)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
