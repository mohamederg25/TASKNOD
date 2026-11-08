"""Varied, friendly copy for the assistant."""

from __future__ import annotations

import random
from typing import Optional, Sequence


class MessageBook:
    """Picks lines without immediately repeating the same one."""

    def __init__(self) -> None:
        self._last: dict[str, str] = {}

    def _pick(self, key: str, options: Sequence[str], **values: object) -> str:
        if not options:
            return ""
        choice = random.choice(options)
        if len(options) > 1 and choice == self._last.get(key):
            choice = random.choice([item for item in options if item != choice])
        self._last[key] = choice
        return choice.format(**values)

    def nudge_intro(
        self,
        *,
        priority: int,
        overdue: bool,
        due_today: bool,
    ) -> str:
        if overdue:
            return self._pick(
                "nudge_overdue",
                [
                    "Past due — no judgment:",
                    "This one slipped by, but it's still here:",
                    "A gentle rescue mission for:",
                    "Overdue and waiting patiently:",
                ],
            )
        if priority >= 2:
            return self._pick(
                "nudge_high",
                [
                    "This one's marked important:",
                    "Worth making room for:",
                    "A high-priority nudge for:",
                    "Your future self would thank you for:",
                ],
            )
        if due_today:
            return self._pick(
                "nudge_today",
                [
                    "On today's list:",
                    "A little today-flavoured nudge:",
                    "Today would be a lovely time for:",
                    "Still on today's list:",
                ],
            )
        return self._pick(
            "nudge_normal",
            [
                "Hey! Still haven't done:",
                "Tiny nudge:",
                "This is still on your list:",
                "A little check-in about:",
                "Psst — this one's waiting:",
                "No pressure, but:",
                "Your tiny task buddy is here for:",
                "Future you says hi about:",
            ],
        )

    def encouragement(self) -> str:
        return self._pick(
            "encouragement",
            [
                "Small steps count.",
                "Two minutes is enough to start.",
                "You've got this.",
                "One thing at a time.",
                "Future you will be delighted.",
                "A little progress is still progress.",
            ],
        )

    def done(self, title: str) -> str:
        return self._pick(
            "done",
            [
                f"Done! “{title}” is off the list.",
                f"Tiny win unlocked: {title} ✓",
                f"Look at you go — {title} is finished.",
                f"That's {title} handled. Nice one!",
                f"Checked off: {title}. Future you says thanks.",
            ],
        )

    def repeated_done(self, title: str, when: str) -> str:
        return self._pick(
            "repeated_done",
            [
                f"Done! {title} will come around again {when}.",
                f"Nice — next {title} is lined up for {when}.",
                f"One down. {title} returns {when}.",
            ],
        )

    def snoozed(self, minutes: int) -> str:
        label = "1 hour" if minutes == 60 else f"{minutes} minutes"
        return self._pick(
            "snoozed",
            [
                f"Okay — back in {label}.",
                f"Snoozed for {label}. I'll pop by later.",
                f"Fine by me. See you in {label}.",
            ],
        )

    def skipped(self) -> str:
        return self._pick(
            "skipped",
            [
                "Skipped for now. No guilt.",
                "Leaving that one for later.",
                "Not now — got it.",
                "Skipped. It'll keep.",
            ],
        )

    def all_done(self) -> str:
        return self._pick(
            "all_done",
            [
                "Your list is clear. Go enjoy the quiet!",
                "Nothing waiting right now. Lovely.",
                "All clear — little victory!",
                "No tasks need you this minute.",
            ],
        )

    def summary_intro(self) -> str:
        return self._pick(
            "summary_intro",
            [
                "Good morning!",
                "Morning, sunshine.",
                "A fresh day, a fresh list.",
                "Rise and shine — gently.",
            ],
        )

    def summary_line(self, open_count: int, due_today: int, overdue: int) -> str:
        if open_count == 0:
            return "Your slate is clear today."
        if open_count == 1:
            line = "You have 1 task today."
        else:
            line = f"You have {open_count} tasks today."
        details: list[str] = []
        if due_today:
            details.append(f"{due_today} due today")
        if overdue:
            details.append(f"{overdue} overdue")
        if details:
            line += "\n" + " · ".join(details) + "."
        return line

    def summary_note(self, completed_today: int, streak: int) -> str:
        if completed_today and streak > 1:
            return f"{completed_today} already done today · {streak}-day streak."
        if completed_today:
            return f"{completed_today} already done today. Nice start."
        if streak > 1:
            return f"Your {streak}-day streak is ready for today."
        return self._pick(
            "summary_note",
            [
                "One small thing is enough to begin.",
                "Pick the easiest one first.",
                "No rush. Just begin somewhere.",
                "Today can be gentle and productive.",
            ],
        )

    def stats_line(self, completed_today: int, streak: int) -> str:
        if completed_today and streak > 1:
            return self._pick(
                "stats_line",
                [
                    f"{streak} days in a row — quietly impressive.",
                    f"{completed_today} today and a {streak}-day streak. Look at you.",
                ],
            )
        if completed_today:
            return self._pick(
                "stats_line",
                [
                    "A completed task is a completed task. Well done.",
                    "Today is already moving. Nice.",
                ],
            )
        if streak > 1:
            return f"Your {streak}-day streak is waiting for a tiny win."
        return self._pick(
            "stats_line",
            [
                "Every streak starts with one small task.",
                "Your first tick of the day is out there.",
            ],
        )
