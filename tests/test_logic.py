"""Tests for the non-GUI core: storage, configuration and date helpers."""

from __future__ import annotations

import tempfile
import unittest
from datetime import date, datetime, time, timedelta
from pathlib import Path

from tasknudge.config import Config
from tasknudge.models import Priority, Task
from tasknudge.storage import TaskStore
from tasknudge.util import (
    advance_repeat,
    clamp,
    due_description,
    in_quiet_hours,
    is_due_today,
    is_task_overdue,
    plural,
)


class StorageTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.store = TaskStore(Path(self._tmp.name) / "tasks.db")
        self.addCleanup(self.store.close)

    def test_add_normalizes_fields_and_reads_back(self) -> None:
        task = self.store.add_task(Task(title="  Water plants  ", priority=99))

        self.assertIsNotNone(task.id)
        self.assertEqual(task.title, "Water plants")
        self.assertEqual(task.priority, int(Priority.HIGH))
        self.assertIsNotNone(task.created_at)
        self.assertFalse(task.completed)

    def test_add_rejects_bad_input(self) -> None:
        with self.assertRaises(ValueError):
            self.store.add_task(Task(title="   "))
        with self.assertRaises(ValueError):
            self.store.add_task(Task(title="Daily", repeat_rule="daily"))
        with self.assertRaises(ValueError):
            self.store.add_task(
                Task(
                    title="Weekly",
                    due_at=datetime.now(),
                    repeat_rule="monthly",
                )
            )

    def test_list_orders_open_before_completed_and_by_due_date(self) -> None:
        self.store.add_task(Task(title="Later", due_at=datetime.now() + timedelta(days=5)))
        self.store.add_task(Task(title="Soon", due_at=datetime.now() + timedelta(days=1)))
        self.store.add_task(Task(title="Someday"))
        done = self.store.add_task(Task(title="Done"))
        self.store.complete_task(done.id)

        titles = [task.title for task in self.store.list_tasks()]

        self.assertEqual(titles, ["Soon", "Later", "Someday", "Done"])
        self.assertEqual(
            [task.title for task in self.store.list_tasks(include_completed=False)],
            ["Soon", "Later", "Someday"],
        )

    def test_complete_and_reopen_keep_statistics_truthful(self) -> None:
        task = self.store.add_task(Task(title="One"))

        completed, recurring = self.store.complete_task(task.id)
        self.assertTrue(completed.completed)
        self.assertFalse(recurring)
        self.assertEqual(self.store.statistics()["completed_today"], 1)

        reopened = self.store.reopen_task(task.id)
        self.assertFalse(reopened.completed)
        self.assertEqual(self.store.statistics()["completed_today"], 0)

    def test_delete_removes_completion_history(self) -> None:
        task = self.store.add_task(Task(title="Temporary"))
        self.store.complete_task(task.id)
        self.store.delete_task(task.id)

        self.assertIsNone(self.store.get_task(task.id))
        row = self.store.connection.execute("SELECT COUNT(*) FROM completions").fetchone()
        self.assertEqual(int(row[0]), 0)

    def test_timed_repeat_advances_past_now(self) -> None:
        now = datetime(2026, 11, 8, 12, 0)
        task = self.store.add_task(
            Task(
                title="Daily stand-up",
                due_at=datetime(2026, 11, 6, 9, 0),
                due_has_time=True,
                repeat_rule="daily",
            )
        )

        updated, recurring = self.store.complete_task(task.id, now=now)

        self.assertTrue(recurring)
        self.assertFalse(updated.completed)
        self.assertEqual(updated.due_at, datetime(2026, 11, 9, 9, 0))
        self.assertGreater(updated.due_at, now)

    def test_date_only_repeat_advances_calendar_days(self) -> None:
        now = datetime(2026, 11, 8, 12, 0)
        task = self.store.add_task(
            Task(title="Weekly review", due_at=datetime(2026, 11, 2), repeat_rule="weekly")
        )

        updated, recurring = self.store.complete_task(task.id, now=now)

        self.assertTrue(recurring)
        self.assertEqual(updated.due_at, datetime(2026, 11, 9))
        self.assertFalse(updated.due_has_time)

    def test_snooze_and_record_shown_manage_reminder_state(self) -> None:
        now = datetime(2026, 11, 8, 12, 0)
        task = self.store.add_task(
            Task(title="Later", due_at=now + timedelta(hours=1), due_has_time=True)
        )

        self.store.record_shown(task.id, due_at=task.due_at)
        self.assertEqual(self.store.get_task(task.id).due_notified_for, task.due_at)

        self.store.snooze_task(task.id, 15, now=now)
        snoozed = self.store.get_task(task.id)
        self.assertEqual(snoozed.snooze_until, now + timedelta(minutes=15))
        self.assertIsNone(snoozed.due_notified_for)

        self.store.record_shown(task.id, due_at=task.due_at)
        self.assertIsNone(self.store.get_task(task.id).snooze_until)

    def test_editing_the_schedule_clears_runtime_state(self) -> None:
        now = datetime(2026, 11, 8, 12, 0)
        task = self.store.add_task(
            Task(title="Timed", due_at=now + timedelta(minutes=5), due_has_time=True)
        )
        self.store.record_shown(task.id, due_at=task.due_at)
        self.store.snooze_task(task.id, 10, now=now)
        self.assertIsNotNone(self.store.get_task(task.id).snooze_until)

        task = self.store.get_task(task.id)
        task.due_at = now + timedelta(days=1)
        updated = self.store.update_task(task)

        self.assertIsNone(updated.snooze_until)
        self.assertIsNone(updated.due_notified_for)

    def test_statistics_count_today_week_streak_and_chart(self) -> None:
        now = datetime(2026, 11, 8, 12, 0)  # Sunday
        for _ in range(2):
            task = self.store.add_task(Task(title="Win"))
            self.store.complete_task(task.id, now=now)
        yesterday = self.store.add_task(Task(title="Old win"))
        self.store.complete_task(yesterday.id, now=now - timedelta(days=1))

        stats = self.store.statistics(now)

        self.assertEqual(stats["completed_today"], 2)
        self.assertEqual(stats["completed_week"], 3)
        self.assertEqual(stats["streak"], 2)
        self.assertEqual(len(stats["week_chart"]), 7)
        self.assertEqual(stats["week_chart"][-1], (date(2026, 11, 8), 2))
        self.assertEqual(stats["week_chart"][-2], (date(2026, 11, 7), 1))

    def test_summary_counts_open_tasks(self) -> None:
        now = datetime(2026, 11, 8, 12, 0)
        self.store.add_task(Task(title="Overdue", due_at=now - timedelta(days=1)))
        self.store.add_task(
            Task(title="Today", due_at=now + timedelta(hours=1), due_has_time=True)
        )
        self.store.add_task(Task(title="High", priority=int(Priority.HIGH)))

        self.assertEqual(
            self.store.summary_tasks(now),
            {"open": 3, "overdue": 1, "due_today": 1, "high_priority": 1},
        )


class UtilTests(unittest.TestCase):
    def test_quiet_hours_normal_and_overnight_windows(self) -> None:
        daytime = (time(9, 0), time(17, 0))
        self.assertTrue(in_quiet_hours(datetime(2026, 11, 8, 9, 0), *daytime))
        self.assertTrue(in_quiet_hours(datetime(2026, 11, 8, 16, 59), *daytime))
        self.assertFalse(in_quiet_hours(datetime(2026, 11, 8, 17, 0), *daytime))

        overnight = (time(23, 0), time(8, 0))
        self.assertTrue(in_quiet_hours(datetime(2026, 11, 8, 23, 30), *overnight))
        self.assertTrue(in_quiet_hours(datetime(2026, 11, 9, 7, 59), *overnight))
        self.assertFalse(in_quiet_hours(datetime(2026, 11, 9, 8, 0), *overnight))
        self.assertFalse(in_quiet_hours(datetime(2026, 11, 8, 12, 0), *overnight))

        self.assertFalse(
            in_quiet_hours(
                datetime(2026, 11, 8, 12, 0), time(12, 0), time(12, 0)
            )
        )

    def test_advance_repeat_catches_up(self) -> None:
        self.assertEqual(
            advance_repeat(
                datetime(2026, 11, 1), "daily", datetime(2026, 11, 5, 12, 0)
            ),
            datetime(2026, 11, 6),
        )
        self.assertEqual(
            advance_repeat(
                datetime(2026, 11, 1, 9, 0), "weekly", datetime(2026, 11, 8, 8, 59)
            ),
            datetime(2026, 11, 8, 9, 0),
        )
        self.assertEqual(
            advance_repeat(
                datetime(2026, 11, 8, 9, 0), "daily", datetime(2026, 11, 8, 10, 0)
            ),
            datetime(2026, 11, 9, 9, 0),
        )

    def test_due_description(self) -> None:
        now = datetime(2026, 11, 8, 12, 0)

        self.assertEqual(due_description(Task(title="x"), now), "Anytime")
        self.assertEqual(
            due_description(Task(title="x", due_at=datetime(2026, 11, 8)), now), "Today"
        )
        self.assertEqual(
            due_description(Task(title="x", due_at=datetime(2026, 11, 9)), now),
            "Tomorrow",
        )
        self.assertTrue(
            due_description(Task(title="x", due_at=datetime(2026, 11, 7)), now).startswith(
                "Overdue"
            )
        )

    def test_overdue_and_due_today_respect_time_and_completion(self) -> None:
        now = datetime(2026, 11, 8, 12, 0)
        date_only_today = Task(title="x", due_at=datetime(2026, 11, 8))
        timed_past = Task(
            title="x", due_at=datetime(2026, 11, 8, 11, 0), due_has_time=True
        )
        completed = Task(
            title="x",
            due_at=datetime(2026, 11, 7),
            completed=True,
        )

        self.assertFalse(is_task_overdue(date_only_today, now))
        self.assertTrue(is_due_today(date_only_today, now))
        self.assertTrue(is_task_overdue(timed_past, now))
        self.assertFalse(is_task_overdue(completed, now))
        self.assertFalse(is_due_today(completed, now))

    def test_small_helpers(self) -> None:
        self.assertEqual(clamp(5, 1, 3), 3)
        self.assertEqual(clamp(0, 1, 3), 1)
        self.assertEqual(plural(1, "day"), "1 day")
        self.assertEqual(plural(3, "day"), "3 days")


class ConfigTests(unittest.TestCase):
    def _path(self) -> tuple[tempfile.TemporaryDirectory, Path]:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        return tmp, Path(tmp.name) / "config.json"

    def test_roundtrip_normalizes_values(self) -> None:
        _tmp, path = self._path()
        config = Config(
            interval_min_minutes=0,
            interval_max_minutes=9999,
            auto_dismiss_seconds=1,
            quiet_start="99:99",
        )
        config.save(path)

        loaded = Config.load(path)

        self.assertEqual(loaded.interval_min_minutes, 1)
        self.assertEqual(loaded.interval_max_minutes, 720)
        self.assertEqual(loaded.auto_dismiss_seconds, 5)
        self.assertEqual(loaded.quiet_start, "23:00")

    def test_intervals_are_swapped_when_reversed(self) -> None:
        config = Config(interval_min_minutes=60, interval_max_minutes=10).normalize()
        self.assertEqual((config.interval_min_minutes, config.interval_max_minutes), (10, 60))

    def test_corrupt_file_is_backed_up_and_replaced(self) -> None:
        tmp, path = self._path()
        path.write_text("{ not valid json", encoding="utf-8")

        loaded = Config.load(path)

        self.assertEqual(loaded.interval_min_minutes, 10)
        self.assertTrue(path.exists())
        self.assertTrue(list(Path(tmp.name).glob("config.json.broken-*")))

    def test_unknown_keys_are_ignored(self) -> None:
        config = Config.from_dict({"sound_enabled": False, "legacy_option": "ignored"})
        self.assertFalse(config.sound_enabled)


if __name__ == "__main__":
    unittest.main()
