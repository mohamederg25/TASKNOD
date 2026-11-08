"""Tests for reminder scheduling decisions."""

from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from PyQt6.QtCore import QCoreApplication

from tasknudge.config import Config
from tasknudge.models import Task
from tasknudge.scheduler import Scheduler
from tasknudge.storage import TaskStore

_APP = None


def setUpModule() -> None:
    global _APP
    _APP = QCoreApplication.instance() or QCoreApplication([])


class SchedulerTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.store = TaskStore(Path(self._tmp.name) / "tasks.db")
        self.addCleanup(self.store.close)
        self.config = Config(
            interval_min_minutes=10,
            interval_max_minutes=10,
            quiet_hours_enabled=False,
            morning_summary_enabled=False,
            sound_enabled=False,
            paused=False,
        )
        self.scheduler = Scheduler(self.config, self.store)
        self.addCleanup(self.scheduler.stop)
        self.reminders: list[int] = []
        self.summaries: list[int] = []
        self.scheduler.reminder_ready.connect(self.reminders.append)
        self.scheduler.summary_ready.connect(lambda: self.summaries.append(1))

        # Fullscreen detection talks to the OS; keep tests deterministic.
        fullscreen = patch(
            "tasknudge.scheduler.is_fullscreen_app_active", return_value=False
        )
        fullscreen.start()
        self.addCleanup(fullscreen.stop)

    def test_timed_task_fires_once_at_its_due_time(self) -> None:
        now = datetime(2026, 11, 8, 12, 0)
        due = now - timedelta(minutes=5)
        task = self.store.add_task(
            Task(title="Call back", due_at=due, due_has_time=True)
        )
        self.scheduler._next_random_at = now + timedelta(hours=1)

        self.scheduler.tick(now)

        self.assertEqual(self.reminders, [task.id])
        self.assertEqual(self.store.get_task(task.id).due_notified_for, due)

        self.scheduler.popup_closed()
        self.reminders.clear()
        self.scheduler.tick(now)

        self.assertEqual(self.reminders, [])

    def test_paused_and_quiet_hours_suppress_reminders(self) -> None:
        now = datetime(2026, 11, 8, 12, 0)
        self.store.add_task(
            Task(title="Timed", due_at=now - timedelta(minutes=1), due_has_time=True)
        )

        self.config.paused = True
        self.scheduler.tick(now)
        self.assertEqual(self.reminders, [])

        self.config.paused = False
        self.config.quiet_hours_enabled = True
        self.config.quiet_start = "00:00"
        self.config.quiet_end = "23:59"
        self.scheduler.tick(now)
        self.assertEqual(self.reminders, [])

    def test_quiet_hours_normalize_invalid_windows(self) -> None:
        config = Config(quiet_start="99:99", quiet_end="nonsense").normalize()
        self.assertEqual(config.quiet_start, "23:00")
        self.assertEqual(config.quiet_end, "08:00")

    def test_random_pool_excludes_timed_and_snoozed_tasks(self) -> None:
        now = datetime(2026, 11, 8, 12, 0)
        self.store.add_task(
            Task(
                title="Timed",
                due_at=now + timedelta(days=1),
                due_has_time=True,
            )
        )
        snoozed = self.store.add_task(Task(title="Snoozed"))
        self.store.snooze_task(snoozed.id, 30, now=now)
        free = self.store.add_task(Task(title="Free"))

        candidates = self.scheduler._random_candidates(
            self.store.list_tasks(include_completed=False), now
        )

        self.assertEqual([task.id for task in candidates], [free.id])

    def test_random_nudge_emits_and_records_when_due(self) -> None:
        now = datetime(2026, 11, 8, 12, 0)
        task = self.store.add_task(Task(title="Any time"))
        self.scheduler._next_random_at = now - timedelta(seconds=1)

        self.scheduler.tick(now)

        self.assertEqual(self.reminders, [task.id])
        self.assertIsNotNone(self.store.get_task(task.id).last_shown_at)

    def test_snoozed_task_waits_for_its_deadline(self) -> None:
        now = datetime(2026, 11, 8, 12, 0)
        task = self.store.add_task(Task(title="Later"))
        self.store.snooze_task(task.id, 60, now=now)
        self.scheduler._next_random_at = now - timedelta(seconds=1)

        self.scheduler.tick(now)
        self.assertEqual(self.reminders, [])

        self.scheduler.tick(now + timedelta(minutes=61))
        self.assertEqual(self.reminders, [task.id])

    def test_summary_fires_once_per_day(self) -> None:
        now = datetime(2026, 11, 8, 12, 0)
        self.config.morning_summary_enabled = True
        self.config.morning_summary_time = "00:00"

        self.scheduler.tick(now)
        self.assertEqual(self.summaries, [1])
        self.assertEqual(self.config.last_summary_date, "2026-11-08")

        self.scheduler.popup_closed()
        self.scheduler.tick(now)
        self.assertEqual(self.summaries, [1])

    def test_no_popup_overlaps_an_active_one(self) -> None:
        now = datetime(2026, 11, 8, 12, 0)
        task = self.store.add_task(Task(title="Any time"))
        self.scheduler._next_random_at = now - timedelta(seconds=1)

        self.scheduler.tick(now)
        self.scheduler._next_random_at = now - timedelta(seconds=1)
        self.scheduler.tick(now)

        self.assertEqual(self.reminders, [task.id])


if __name__ == "__main__":
    unittest.main()
