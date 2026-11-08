"""Small shared helpers for dates, times and human-friendly labels."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import Iterable, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from tasknudge.models import Task


def local_now() -> datetime:
    """Current local time, truncated to whole seconds."""

    return datetime.now().replace(microsecond=0)


def parse_hhmm(value: str, fallback: time) -> time:
    """Parse a ``HH:MM`` string, falling back if it is malformed."""

    try:
        hour, minute = value.split(":", 1)
        return time(hour=int(hour), minute=int(minute))
    except (ValueError, TypeError):
        return fallback


def time_to_hhmm(value: time) -> str:
    return value.strftime("%H:%M")


def in_quiet_hours(now: datetime, start: time, end: time) -> bool:
    """Return True when ``now`` falls inside the (possibly overnight) window."""

    if start == end:
        return False
    current = now.time()
    if start < end:
        return start <= current < end
    return current >= start or current < end


def advance_repeat(due: datetime, rule: str, now: datetime) -> datetime:
    """Move a recurring task forward until its next occurrence is in the future.

    Date-only tasks are anchored at midnight and advance by calendar days.
    Timed tasks keep their original clock time.
    """

    step = timedelta(days=1 if rule == "daily" else 7)
    next_due = due + step
    if due.hour == 0 and due.minute == 0 and due.second == 0:
        while next_due.date() <= now.date():
            next_due += step
    else:
        while next_due <= now:
            next_due += step
    return next_due


def is_task_overdue(task: "Task", now: Optional[datetime] = None) -> bool:
    """Overdue means a timed task is past its time, or a date has passed."""

    if task.completed or task.due_at is None:
        return False
    now = now or local_now()
    if task.due_has_time:
        return task.due_at < now
    return task.due_at.date() < now.date()


def is_due_today(task: "Task", now: Optional[datetime] = None) -> bool:
    if task.completed or task.due_at is None:
        return False
    now = now or local_now()
    return task.due_at.date() == now.date()


def friendly_time(value: datetime) -> str:
    return value.strftime("%I:%M %p").lstrip("0")


def friendly_date(value: datetime, include_weekday: bool = False) -> str:
    prefix = value.strftime("%a, ") if include_weekday else ""
    return f"{prefix}{value.strftime('%b')} {value.day}"


def due_description(task: "Task", now: Optional[datetime] = None) -> str:
    """Short, friendly due-date text for the task list and popup."""

    if task.due_at is None:
        return "Anytime"

    now = now or local_now()
    due = task.due_at
    today = now.date()
    days = (due.date() - today).days

    if is_task_overdue(task, now):
        if task.due_has_time:
            return f"Overdue · {friendly_date(due)}, {friendly_time(due)}"
        return f"Overdue · {friendly_date(due)}"

    if days == 0:
        day_label = "Today"
    elif days == 1:
        day_label = "Tomorrow"
    elif days == -1:
        day_label = "Yesterday"
    elif 1 < days < 7:
        day_label = due.strftime("%A")
    else:
        day_label = friendly_date(due, include_weekday=True)

    if task.due_has_time:
        return f"{day_label} · {friendly_time(due)}"
    return day_label


def repeat_label(rule: Optional[str]) -> str:
    return {"daily": "Daily", "weekly": "Weekly"}.get(rule or "", "—")


def plural(count: int, singular: str, plural_form: Optional[str] = None) -> str:
    if count == 1:
        return f"{count} {singular}"
    return f"{count} {plural_form or singular + 's'}"


def format_streak(days: int) -> str:
    return plural(days, "day")


def clamp(value: int, low: int, high: int) -> int:
    return max(low, min(high, value))


def first_word_upper(text: str) -> str:
    return text[:1].upper() + text[1:] if text else text


def any_due_on(tasks: Iterable["Task"], target: date) -> Iterable["Task"]:
    for task in tasks:
        if not task.completed and task.due_at and task.due_at.date() == target:
            yield task
