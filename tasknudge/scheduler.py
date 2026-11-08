"""Reminder timing: random nudges, exact due times, quiet hours and summaries."""

from __future__ import annotations

import logging
import random
from datetime import datetime, timedelta
from typing import Optional

from PyQt6.QtCore import QObject, QTimer, pyqtSignal

from tasknudge.config import Config
from tasknudge.fullscreen import is_fullscreen_app_active
from tasknudge.models import Priority, Task
from tasknudge.storage import TaskStore
from tasknudge.util import in_quiet_hours, is_due_today, is_task_overdue, local_now

log = logging.getLogger(__name__)


class Scheduler(QObject):
    reminder_ready = pyqtSignal(int)  # task id
    summary_ready = pyqtSignal()

    def __init__(
        self,
        config: Config,
        store: TaskStore,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self.config = config
        self.store = store
        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self.tick)
        self._next_random_at: Optional[datetime] = None
        self._next_wake_at: Optional[datetime] = None
        self._popup_active = False
        self._fullscreen_retry_at: Optional[datetime] = None

    def start(self) -> None:
        self.schedule_next_random()
        self._next_wake_at = None
        self._timer.start()

    def stop(self) -> None:
        self._timer.stop()

    def reconfigure(self) -> None:
        self.wake()
        if not self._popup_active:
            self.schedule_next_random()

    def wake(self) -> None:
        """Force the next timer tick to re-read tasks immediately."""

        self._next_wake_at = None
        self._fullscreen_retry_at = None

    def schedule_next_random(self, now: Optional[datetime] = None) -> None:
        now = now or local_now()
        low = max(1, int(self.config.interval_min_minutes)) * 60
        high = max(low, int(self.config.interval_max_minutes) * 60)
        seconds = random.uniform(low, high)
        self._next_random_at = now + timedelta(seconds=seconds)

    def set_paused(self, paused: bool) -> None:
        self.config.paused = paused
        if not paused and not self._popup_active:
            self.schedule_next_random()
            self.wake()

    def popup_closed(self) -> None:
        self._popup_active = False
        self.schedule_next_random()
        self.wake()

    def _is_quiet(self, now: datetime) -> bool:
        if not self.config.quiet_hours_enabled:
            return False
        return in_quiet_hours(
            now, self.config.quiet_start_time, self.config.quiet_end_time
        )

    def _summary_is_due(self, now: datetime) -> bool:
        return (
            self.config.morning_summary_enabled
            and self.config.last_summary_date != now.date().isoformat()
            and now.time() >= self.config.summary_time
        )

    @staticmethod
    def _random_weight(task: Task, now: datetime) -> float:
        priority_weight = {
            int(Priority.LOW): 1.0,
            int(Priority.MEDIUM): 2.1,
            int(Priority.HIGH): 4.8,
        }.get(task.priority, 2.1)

        if is_task_overdue(task, now):
            urgency = 4.0
        elif is_due_today(task, now):
            urgency = 2.4
        elif task.due_at and 0 <= (task.due_at - now).total_seconds() <= 2 * 86400:
            urgency = 1.45
        else:
            urgency = 1.0

        if task.last_shown_at is None:
            recency = 1.35
        else:
            minutes = max(0.0, (now - task.last_shown_at).total_seconds() / 60)
            if minutes < 15:
                recency = 0.22
            elif minutes < 60:
                recency = 0.60
            elif minutes < 240:
                recency = 1.0
            else:
                recency = 1.3
        return priority_weight * urgency * recency

    def _due_candidates(self, tasks: list[Task], now: datetime) -> list[Task]:
        candidates: list[Task] = []
        seen: set[int] = set()
        for task in tasks:
            if task.id is None or task.id in seen:
                continue
            if task.snooze_until is not None and task.snooze_until > now:
                continue

            exact_due = (
                task.due_has_time
                and task.due_at is not None
                and task.due_at <= now
                and task.due_notified_for != task.due_at
            )
            snooze_due = task.snooze_until is not None and task.snooze_until <= now
            if exact_due or snooze_due:
                candidates.append(task)
                seen.add(task.id)

        candidates.sort(
            key=lambda item: (
                -item.priority,
                item.due_at or datetime.max,
                item.snooze_until or datetime.max,
                item.id or 0,
            )
        )
        return candidates

    def _random_candidates(self, tasks: list[Task], now: datetime) -> list[Task]:
        candidates: list[Task] = []
        for task in tasks:
            if task.id is None:
                continue
            if task.due_has_time:
                # Timed tasks belong at their time, never in the random pool.
                continue
            if task.snooze_until is not None and task.snooze_until > now:
                continue
            candidates.append(task)
        return candidates

    def _pick_random(self, tasks: list[Task], now: datetime) -> Optional[Task]:
        candidates = self._random_candidates(tasks, now)
        if not candidates:
            return None
        weights = [max(0.01, self._random_weight(task, now)) for task in candidates]
        return random.choices(candidates, weights=weights, k=1)[0]

    def _fullscreen_is_blocking(self, now: datetime) -> bool:
        if self._fullscreen_retry_at and now < self._fullscreen_retry_at:
            return True
        if is_fullscreen_app_active():
            # Recheck periodically rather than polling the OS every second.
            self._fullscreen_retry_at = now + timedelta(seconds=45)
            log.debug("Reminder held while a fullscreen app is active")
            return True
        self._fullscreen_retry_at = None
        return False

    def _compute_next_wake(self, tasks: list[Task], now: datetime) -> Optional[datetime]:
        candidates: list[datetime] = []
        if self._next_random_at is not None:
            candidates.append(self._next_random_at)

        if self.config.morning_summary_enabled and (
            self.config.last_summary_date != now.date().isoformat()
        ):
            summary_at = datetime.combine(now.date(), self.config.summary_time)
            candidates.append(max(now, summary_at))

        for task in tasks:
            if task.snooze_until is not None:
                candidates.append(max(now, task.snooze_until))
            elif (
                task.due_has_time
                and task.due_at is not None
                and task.due_notified_for != task.due_at
            ):
                candidates.append(max(now, task.due_at))

        return min(candidates) if candidates else None

    def tick(self, now: Optional[datetime] = None) -> None:
        """Timer callback. ``now`` is injectable for tests."""

        now = now or local_now()
        if self.config.paused or self._popup_active:
            return
        if self._is_quiet(now):
            return
        if self._next_wake_at is not None and now < self._next_wake_at:
            return

        tasks = self.store.list_tasks(include_completed=False)
        summary_due = self._summary_is_due(now)
        due_candidates = self._due_candidates(tasks, now)
        random_due = self._next_random_at is not None and now >= self._next_random_at

        if not (summary_due or due_candidates or random_due):
            self._next_wake_at = self._compute_next_wake(tasks, now)
            return

        # Nothing should appear over a game, fullscreen video, slideshow, or
        # during an OS "quiet time".
        if self._fullscreen_is_blocking(now):
            self._next_wake_at = self._fullscreen_retry_at
            return

        if summary_due:
            self._popup_active = True
            self._next_wake_at = None
            self.config.last_summary_date = now.date().isoformat()
            self.summary_ready.emit()
            return

        if due_candidates:
            task = due_candidates[0]
            if task.id is None:
                return
            self.store.record_shown(
                task.id, due_at=task.due_at if task.due_has_time else None
            )
            self._popup_active = True
            self._next_wake_at = None
            self.reminder_ready.emit(task.id)
            return

        task = self._pick_random(tasks, now)
        if task is None or task.id is None:
            self.schedule_next_random(now)
            self._next_wake_at = self._next_random_at
            return
        self.store.record_shown(task.id)
        self._popup_active = True
        self._next_wake_at = None
        self.reminder_ready.emit(task.id)
