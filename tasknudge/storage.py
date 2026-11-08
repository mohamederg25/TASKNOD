"""SQLite persistence for tasks and completion history."""

from __future__ import annotations

import sqlite3
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Any, Optional

from tasknudge.models import Priority, Task
from tasknudge.paths import database_path
from tasknudge.util import advance_repeat, is_due_today, is_task_overdue, local_now

SCHEMA = """
CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    notes TEXT NOT NULL DEFAULT '',
    priority INTEGER NOT NULL DEFAULT 1 CHECK(priority BETWEEN 0 AND 2),
    due_at TEXT,
    due_has_time INTEGER NOT NULL DEFAULT 0,
    repeat_rule TEXT CHECK(repeat_rule IN ('daily', 'weekly') OR repeat_rule IS NULL),
    created_at TEXT NOT NULL,
    completed INTEGER NOT NULL DEFAULT 0,
    completed_at TEXT,
    last_shown_at TEXT,
    due_notified_for TEXT,
    snooze_until TEXT
);

CREATE TABLE IF NOT EXISTS completions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    completed_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_tasks_open ON tasks(completed, due_at);
CREATE INDEX IF NOT EXISTS idx_completions_time ON completions(completed_at);
"""


def _iso(value: Optional[datetime]) -> Optional[str]:
    if value is None:
        return None
    return value.replace(microsecond=0).isoformat()


def _from_iso(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


class TaskStore:
    """All task reads and writes live here so the UI never touches SQL."""

    def __init__(self, path: Optional[Path] = None) -> None:
        self.path = path or database_path()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(str(self.path), timeout=10)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.execute("PRAGMA journal_mode = WAL")
        self.connection.execute("PRAGMA synchronous = NORMAL")
        self.connection.executescript(SCHEMA)
        self.connection.commit()

    def close(self) -> None:
        try:
            self.connection.commit()
            self.connection.close()
        except sqlite3.Error:
            pass

    @staticmethod
    def _task_from_row(row: sqlite3.Row) -> Task:
        return Task(
            id=row["id"],
            title=row["title"],
            notes=row["notes"] or "",
            priority=int(row["priority"]),
            due_at=_from_iso(row["due_at"]),
            due_has_time=bool(row["due_has_time"]),
            repeat_rule=row["repeat_rule"],
            created_at=_from_iso(row["created_at"]),
            completed=bool(row["completed"]),
            completed_at=_from_iso(row["completed_at"]),
            last_shown_at=_from_iso(row["last_shown_at"]),
            due_notified_for=_from_iso(row["due_notified_for"]),
            snooze_until=_from_iso(row["snooze_until"]),
        )

    def get_task(self, task_id: int) -> Optional[Task]:
        row = self.connection.execute(
            "SELECT * FROM tasks WHERE id = ?", (task_id,)
        ).fetchone()
        return self._task_from_row(row) if row else None

    def list_tasks(self, include_completed: bool = True) -> list[Task]:
        where = "" if include_completed else "WHERE completed = 0"
        rows = self.connection.execute(
            f"""
            SELECT * FROM tasks
            {where}
            ORDER BY completed ASC,
                     CASE WHEN due_at IS NULL THEN 1 ELSE 0 END ASC,
                     due_at ASC,
                     priority DESC,
                     id ASC
            """
        ).fetchall()
        return [self._task_from_row(row) for row in rows]

    @staticmethod
    def _validate_user_fields(task: Task) -> None:
        task.title = (task.title or "").strip()
        if not task.title:
            raise ValueError("A task needs a title.")
        task.priority = max(int(Priority.LOW), min(int(Priority.HIGH), int(task.priority)))
        if task.due_at is None:
            task.due_has_time = False
        if task.repeat_rule and task.due_at is None:
            raise ValueError("Repeating tasks need a due date.")
        if task.repeat_rule not in (None, "daily", "weekly"):
            raise ValueError("Unknown repeat rule.")

    def add_task(self, task: Task) -> Task:
        self._validate_user_fields(task)
        created = task.created_at or local_now()
        with self.connection:
            cursor = self.connection.execute(
                """
                INSERT INTO tasks (
                    title, notes, priority, due_at, due_has_time, repeat_rule,
                    created_at, completed, completed_at, last_shown_at,
                    due_notified_for, snooze_until
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 0, NULL, NULL, NULL, NULL)
                """,
                (
                    task.title,
                    task.notes or "",
                    task.priority,
                    _iso(task.due_at),
                    int(task.due_has_time),
                    task.repeat_rule,
                    _iso(created),
                ),
            )
        task.id = int(cursor.lastrowid)
        task.created_at = created
        return task

    def update_task(self, task: Task) -> Task:
        if task.id is None:
            raise ValueError("Cannot update a task without an id.")
        self._validate_user_fields(task)
        previous = self.get_task(task.id)
        if previous is None:
            raise ValueError("That task no longer exists.")

        due_changed = (
            previous.due_at != task.due_at
            or previous.due_has_time != task.due_has_time
            or previous.repeat_rule != task.repeat_rule
        )
        clear_runtime = ", due_notified_for = NULL, snooze_until = NULL" if due_changed else ""
        with self.connection:
            self.connection.execute(
                f"""
                UPDATE tasks
                SET title = ?, notes = ?, priority = ?, due_at = ?,
                    due_has_time = ?, repeat_rule = ?
                    {clear_runtime}
                WHERE id = ?
                """,
                (
                    task.title,
                    task.notes or "",
                    task.priority,
                    _iso(task.due_at),
                    int(task.due_has_time),
                    task.repeat_rule,
                    task.id,
                ),
            )
        updated = self.get_task(task.id)
        if updated is None:
            raise RuntimeError("Task disappeared while updating.")
        return updated

    def delete_task(self, task_id: int) -> None:
        with self.connection:
            self.connection.execute("DELETE FROM tasks WHERE id = ?", (task_id,))

    def record_shown(self, task_id: int, due_at: Optional[datetime] = None) -> None:
        """Remember that a reminder was displayed and clear any pending snooze."""

        now = local_now()
        with self.connection:
            self.connection.execute(
                """
                UPDATE tasks
                SET last_shown_at = ?, snooze_until = NULL,
                    due_notified_for = COALESCE(?, due_notified_for)
                WHERE id = ?
                """,
                (_iso(now), _iso(due_at), task_id),
            )

    def snooze_task(self, task_id: int, minutes: int, now: Optional[datetime] = None) -> None:
        now = now or local_now()
        until = now + timedelta(minutes=max(1, int(minutes)))
        with self.connection:
            self.connection.execute(
                """
                UPDATE tasks
                SET snooze_until = ?, due_notified_for = NULL, last_shown_at = ?
                WHERE id = ?
                """,
                (_iso(until), _iso(now), task_id),
            )

    def defer_task(self, task_id: int, minutes: int, now: Optional[datetime] = None) -> None:
        """Requeue a reminder later (used by Skip and auto-dismiss)."""

        self.snooze_task(task_id, minutes, now=now)

    def complete_task(
        self, task_id: int, now: Optional[datetime] = None
    ) -> tuple[Optional[Task], bool]:
        """Complete a task, or advance a repeating task to its next occurrence.

        Returns ``(task, is_recurring)``. For recurring tasks the returned task is
        still open and already has its next due date.
        """

        now = now or local_now()
        task = self.get_task(task_id)
        if task is None:
            return None, False
        if task.completed:
            return task, False

        with self.connection:
            self.connection.execute(
                "INSERT INTO completions (task_id, completed_at) VALUES (?, ?)",
                (task_id, _iso(now)),
            )
            if task.is_repeating and task.due_at is not None:
                next_due = advance_repeat(task.due_at, task.repeat_rule or "daily", now)
                self.connection.execute(
                    """
                    UPDATE tasks
                    SET due_at = ?, completed = 0, completed_at = NULL,
                        snooze_until = NULL, due_notified_for = NULL
                    WHERE id = ?
                    """,
                    (_iso(next_due), task_id),
                )
                return self.get_task(task_id), True

            self.connection.execute(
                """
                UPDATE tasks
                SET completed = 1, completed_at = ?, snooze_until = NULL,
                    due_notified_for = NULL
                WHERE id = ?
                """,
                (_iso(now), task_id),
            )
        return self.get_task(task_id), False

    def reopen_task(self, task_id: int) -> Optional[Task]:
        task = self.get_task(task_id)
        if task is None:
            return None
        with self.connection:
            self.connection.execute(
                """
                UPDATE tasks
                SET completed = 0, completed_at = NULL, snooze_until = NULL
                WHERE id = ?
                """,
                (task_id,),
            )
            # Undo the most recent completion so statistics stay truthful.
            row = self.connection.execute(
                "SELECT id FROM completions WHERE task_id = ? ORDER BY id DESC LIMIT 1",
                (task_id,),
            ).fetchone()
            if row:
                self.connection.execute("DELETE FROM completions WHERE id = ?", (row["id"],))
        return self.get_task(task_id)

    def statistics(self, now: Optional[datetime] = None) -> dict[str, Any]:
        now = now or local_now()
        today = now.date()
        day_start = datetime.combine(today, time.min)
        tomorrow = day_start + timedelta(days=1)
        week_start = datetime.combine(today - timedelta(days=today.weekday()), time.min)
        chart_start = datetime.combine(today - timedelta(days=6), time.min)

        def count_between(start: datetime, end: datetime) -> int:
            row = self.connection.execute(
                """
                SELECT COUNT(*) AS count FROM completions
                WHERE completed_at >= ? AND completed_at < ?
                """,
                (_iso(start), _iso(end)),
            ).fetchone()
            return int(row["count"])

        open_tasks = self.list_tasks(include_completed=False)
        completed_today = count_between(day_start, tomorrow)
        completed_week = count_between(week_start, tomorrow)

        # Current streak: consecutive days with a completion, ending today.
        # Yesterday is allowed as a grace day when nothing is done yet today.
        rows = self.connection.execute(
            """
            SELECT completed_at FROM completions
            WHERE completed_at >= ?
            ORDER BY completed_at DESC
            """,
            (_iso(datetime.combine(today - timedelta(days=365), time.min)),),
        ).fetchall()
        completion_dates: set[date] = set()
        for row in rows:
            moment = _from_iso(row["completed_at"])
            if moment:
                completion_dates.add(moment.date())
        cursor = today if today in completion_dates else today - timedelta(days=1)
        streak = 0
        while cursor in completion_dates:
            streak += 1
            cursor -= timedelta(days=1)

        chart_counts: dict[date, int] = {}
        chart_rows = self.connection.execute(
            """
            SELECT completed_at FROM completions
            WHERE completed_at >= ? AND completed_at < ?
            """,
            (_iso(chart_start), _iso(tomorrow)),
        ).fetchall()
        for row in chart_rows:
            moment = _from_iso(row["completed_at"])
            if moment:
                chart_counts[moment.date()] = chart_counts.get(moment.date(), 0) + 1

        week_chart = [
            (today - timedelta(days=offset), chart_counts.get(today - timedelta(days=offset), 0))
            for offset in range(6, -1, -1)
        ]

        return {
            "open_count": len(open_tasks),
            "overdue_count": sum(1 for task in open_tasks if is_task_overdue(task, now)),
            "due_today_count": sum(1 for task in open_tasks if is_due_today(task, now)),
            "completed_today": completed_today,
            "completed_week": completed_week,
            "streak": streak,
            "week_chart": week_chart,
        }

    def summary_tasks(self, now: Optional[datetime] = None) -> dict[str, int]:
        now = now or local_now()
        open_tasks = self.list_tasks(include_completed=False)
        return {
            "open": len(open_tasks),
            "overdue": sum(1 for task in open_tasks if is_task_overdue(task, now)),
            "due_today": sum(
                1
                for task in open_tasks
                if task.due_at is not None and task.due_at.date() == now.date()
            ),
            "high_priority": sum(
                1 for task in open_tasks if task.priority == int(Priority.HIGH)
            ),
        }
