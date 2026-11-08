"""Persistent application settings stored as JSON."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, fields
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from tasknudge.paths import config_path
from tasknudge.util import clamp, parse_hhmm

log = logging.getLogger(__name__)


@dataclass
class Config:
    interval_min_minutes: int = 10
    interval_max_minutes: int = 25
    auto_dismiss_seconds: int = 30
    quiet_hours_enabled: bool = True
    quiet_start: str = "23:00"
    quiet_end: str = "08:00"
    sound_enabled: bool = True
    morning_summary_enabled: bool = True
    morning_summary_time: str = "08:00"
    paused: bool = False
    last_summary_date: str = ""

    @property
    def quiet_start_time(self):
        return parse_hhmm(self.quiet_start, datetime.strptime("23:00", "%H:%M").time())

    @property
    def quiet_end_time(self):
        return parse_hhmm(self.quiet_end, datetime.strptime("08:00", "%H:%M").time())

    @property
    def summary_time(self):
        return parse_hhmm(
            self.morning_summary_time, datetime.strptime("08:00", "%H:%M").time()
        )

    def normalize(self) -> "Config":
        self.interval_min_minutes = clamp(int(self.interval_min_minutes), 1, 720)
        self.interval_max_minutes = clamp(int(self.interval_max_minutes), 1, 720)
        if self.interval_min_minutes > self.interval_max_minutes:
            self.interval_min_minutes, self.interval_max_minutes = (
                self.interval_max_minutes,
                self.interval_min_minutes,
            )
        self.auto_dismiss_seconds = clamp(int(self.auto_dismiss_seconds), 5, 600)
        for name in ("quiet_start", "quiet_end", "morning_summary_time"):
            fallback = {
                "quiet_start": "23:00",
                "quiet_end": "08:00",
                "morning_summary_time": "08:00",
            }[name]
            value = parse_hhmm(str(getattr(self, name)), datetime.strptime(fallback, "%H:%M").time())
            setattr(self, name, value.strftime("%H:%M"))
        return self

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Config":
        valid_names = {item.name for item in fields(cls)}
        values = {key: value for key, value in data.items() if key in valid_names}
        config = cls(**values)
        return config.normalize()

    @classmethod
    def load(cls, path: Optional[Path] = None) -> "Config":
        target = path or config_path()
        if not target.exists():
            config = cls()
            config.save(target)
            return config

        try:
            with target.open("r", encoding="utf-8") as handle:
                raw = json.load(handle)
            if not isinstance(raw, dict):
                raise ValueError("settings root must be an object")
            return cls.from_dict(raw)
        except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
            log.warning("Could not read settings from %s: %s", target, exc)
            broken = target.with_name(
                f"{target.name}.broken-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
            )
            try:
                target.replace(broken)
                log.warning("Saved unreadable settings as %s", broken)
            except OSError:
                pass
            config = cls()
            config.save(target)
            return config

    def save(self, path: Optional[Path] = None) -> None:
        self.normalize()
        target = path or config_path()
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_suffix(target.suffix + ".tmp")
        with temporary.open("w", encoding="utf-8") as handle:
            json.dump(self.to_dict(), handle, indent=2)
            handle.write("\n")
        temporary.replace(target)
