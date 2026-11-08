"""Data models shared by storage, UI and scheduling."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import IntEnum
from typing import Optional


class Priority(IntEnum):
    LOW = 0
    MEDIUM = 1
    HIGH = 2


PRIORITY_LABELS: dict[int, str] = {
    Priority.LOW: "Low",
    Priority.MEDIUM: "Medium",
    Priority.HIGH: "High",
}

PRIORITY_SHORT_LABELS: dict[int, str] = {
    Priority.LOW: "LOW",
    Priority.MEDIUM: "MED",
    Priority.HIGH: "HIGH",
}

PRIORITY_COLORS: dict[int, str] = {
    Priority.LOW: "#7f9aab",
    Priority.MEDIUM: "#f2bd73",
    Priority.HIGH: "#ff8d7d",
}

REPEAT_LABELS: dict[str, str] = {
    "daily": "Daily",
    "weekly": "Weekly",
}


@dataclass
class Task:
    id: Optional[int] = None
    title: str = ""
    notes: str = ""
    priority: int = int(Priority.MEDIUM)
    due_at: Optional[datetime] = None
    due_has_time: bool = False
    repeat_rule: Optional[str] = None
    created_at: Optional[datetime] = None
    completed: bool = False
    completed_at: Optional[datetime] = None
    last_shown_at: Optional[datetime] = None
    due_notified_for: Optional[datetime] = None
    snooze_until: Optional[datetime] = None

    @property
    def priority_label(self) -> str:
        return PRIORITY_LABELS.get(self.priority, "Medium")

    @property
    def repeat_label(self) -> str:
        return REPEAT_LABELS.get(self.repeat_rule or "", "—")

    @property
    def is_repeating(self) -> bool:
        return self.repeat_rule in ("daily", "weekly")
