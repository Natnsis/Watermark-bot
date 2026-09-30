"""Different ways of showing how far through the year a given day is."""

from collections.abc import Callable
from datetime import date

DEFAULT_STYLE = "countdown"
MOON_PHASES = "🌑🌒🌓🌔🌕"


def _fraction(day: date) -> float:
    start = date(day.year, 1, 1)
    return (day - start).days / (date(day.year + 1, 1, 1) - start).days


def percent_done(day: date) -> int:
    return int(_fraction(day) * 100)


def _percent(day: date) -> str:
    return f"{percent_done(day)}%"


def _meter(day: date, width: int, filled: str, empty: str) -> str:
    done = round(_fraction(day) * width)
    return filled * done + empty * (width - done) + f" {_percent(day)}"


def _moons(day: date) -> str:
    progress = _fraction(day) * 10
    full = int(progress)
    if full == 10:
        return "🌕" * 10 + f" {_percent(day)}"
    phase = MOON_PHASES[round((progress - full) * 4)]
    return "🌕" * full + phase + "🌑" * (9 - full) + f" {_percent(day)}"


def _road(day: date) -> str:
    position = round(_fraction(day) * 14)
    return "Jan " + "━" * position + "●" + "─" * (14 - position) + f" Dec  {_percent(day)}"


def _week_grid(day: date) -> str:
    weeks_done = min((day - date(day.year, 1, 1)).days // 7, 52)
    cells = "■" * weeks_done + "□" * (52 - weeks_done)
    rows = [cells[i : i + 13] for i in range(0, 52, 13)]
    return "\n".join(rows) + f"\n{weeks_done}/52 weeks done"


def _countdown(day: date) -> str:
    days_left = (date(day.year + 1, 1, 1) - day).days
    weeks_left = days_left // 7
    return (
        f"⏳ {days_left} day{'s' if days_left != 1 else ''} · "
        f"{weeks_left} week{'s' if weeks_left != 1 else ''} left in {day.year}"
    )


def _headline(day: date) -> str:
    return f"📅 {day.year} is {_percent(day)} done"


# key -> (button label, renderer)
STYLES: dict[str, tuple[str, Callable[[date], str]]] = {
    "countdown": ("⏳ Countdown", _countdown),
    "headline": ("📅 Headline", _headline),
    "bar": ("▓ Bar", lambda day: _meter(day, 10, "▓", "░")),
    "slim": ("▰ Slim bar", lambda day: _meter(day, 16, "▰", "▱")),
    "dots": ("● Dots", lambda day: _meter(day, 10, "●", "○")),
    "squares": ("🟩 Squares", lambda day: _meter(day, 10, "🟩", "⬜")),
    "moons": ("🌓 Moons", _moons),
    "road": ("━● Road", _road),
    "weeks": ("■ Week grid", _week_grid),
}


def render(style: str | None, day: date) -> str:
    _, renderer = STYLES.get(style or DEFAULT_STYLE, STYLES[DEFAULT_STYLE])
    return renderer(day)
