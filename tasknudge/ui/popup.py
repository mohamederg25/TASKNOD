"""Always-on-top, corner-sliding reminder popups."""

from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import (
    QEasingCurve,
    QPoint,
    QPropertyAnimation,
    QTimer,
    Qt,
    pyqtSignal,
)
from PyQt6.QtGui import QColor, QCursor, QGuiApplication
from PyQt6.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QMenu,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from tasknudge.avatar import AvatarWidget
from tasknudge.config import Config
from tasknudge.messages import MessageBook
from tasknudge.models import PRIORITY_COLORS, PRIORITY_SHORT_LABELS, Task
from tasknudge.util import due_description, is_due_today, is_task_overdue, local_now


class AnimatedPopup(QWidget):
    """A frameless translucent card that slides in above the taskbar."""

    closed = pyqtSignal()

    def __init__(
        self,
        width: int,
        height: int,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setFixedSize(width, height)
        self._closed_emitted = False

        shell = QVBoxLayout(self)
        shell.setContentsMargins(17, 17, 17, 17)
        self.card = QFrame()
        self.card.setObjectName("popupCard")
        shadow = QGraphicsDropShadowEffect(self.card)
        shadow.setBlurRadius(42)
        shadow.setOffset(0, 8)
        shadow.setColor(QColor(0, 0, 0, 150))
        self.card.setGraphicsEffect(shadow)
        shell.addWidget(self.card)

        self.animation = QPropertyAnimation(self, b"pos", self)
        self.animation.setDuration(310)
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)

    def _screen_available_geometry(self):
        screen = QGuiApplication.screenAt(QCursor.pos()) or QGuiApplication.primaryScreen()
        return screen.availableGeometry() if screen else None

    def show_with_slide(self) -> None:
        geometry = self._screen_available_geometry()
        if geometry is not None:
            end = QPoint(
                geometry.right() - self.width() + 1 - 10,
                geometry.bottom() - self.height() + 1 - 10,
            )
            start = QPoint(end.x(), end.y() + 27)
            self.animation.stop()
            self.animation.setStartValue(start)
            self.animation.setEndValue(end)
            self.move(start)
        self.show()
        self.raise_()
        if geometry is not None:
            self.animation.start()

    def closeEvent(self, event) -> None:  # type: ignore[override]
        if not self._closed_emitted:
            self._closed_emitted = True
            self.closed.emit()
        super().closeEvent(event)

    def _content_layout(self) -> QVBoxLayout:
        layout = QVBoxLayout(self.card)
        layout.setContentsMargins(20, 18, 20, 15)
        layout.setSpacing(8)
        return layout

    def _close_button(self) -> QPushButton:
        button = QPushButton("×")
        button.setObjectName("closeButton")
        button.setFixedSize(26, 26)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        return button

    @staticmethod
    def _priority_chip_style(color: str) -> str:
        return (
            "background-color: #182b35;"
            f"color: {color};"
            f"border: 1px solid {color};"
            "border-radius: 8px;"
            "padding: 3px 8px;"
            "font-size: 10px;"
            "font-weight: 700;"
        )


class NudgePopup(AnimatedPopup):
    done_requested = pyqtSignal(int)
    snooze_requested = pyqtSignal(int, int)
    skip_requested = pyqtSignal(int)
    open_list_requested = pyqtSignal()
    auto_dismissed = pyqtSignal(int)

    def __init__(
        self,
        task: Task,
        config: Config,
        messages: MessageBook,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(430, 351, parent)
        self.task = task
        self._seconds = max(5, int(config.auto_dismiss_seconds))
        self._remaining = self._seconds
        self._resolved = False

        layout = self._content_layout()
        top = QHBoxLayout()
        top.setSpacing(11)
        top.addWidget(AvatarWidget(59, mood="happy"))
        intro_stack = QVBoxLayout()
        intro_stack.setSpacing(2)
        eyebrow = QLabel("A TINY NUDGE")
        eyebrow.setObjectName("eyebrow")
        now = local_now()
        intro = QLabel(
            messages.nudge_intro(
                priority=task.priority,
                overdue=is_task_overdue(task, now),
                due_today=is_due_today(task, now),
            )
        )
        intro.setObjectName("muted")
        intro.setWordWrap(True)
        intro_stack.addWidget(eyebrow)
        intro_stack.addWidget(intro)
        top.addLayout(intro_stack, 1)
        close_button = self._close_button()
        close_button.setToolTip("Close for now")
        close_button.clicked.connect(self._dismiss)
        top.addWidget(close_button, 0, Qt.AlignmentFlag.AlignTop)
        layout.addLayout(top)

        chips = QHBoxLayout()
        chips.setSpacing(7)
        priority_chip = QLabel(PRIORITY_SHORT_LABELS.get(task.priority, "MED"))
        priority_chip.setStyleSheet(
            self._priority_chip_style(PRIORITY_COLORS.get(task.priority, "#f2bd73"))
        )
        due_chip = QLabel(due_description(task, now))
        due_chip.setObjectName("chip")
        chips.addWidget(priority_chip)
        chips.addWidget(due_chip)
        chips.addStretch(1)
        layout.addLayout(chips)

        title = QLabel(task.title)
        title.setObjectName("taskHeadline")
        title.setWordWrap(True)
        title.setMaximumHeight(55)
        title.setToolTip(task.title)
        title.setTextFormat(Qt.TextFormat.PlainText)
        layout.addWidget(title)

        encouragement = QLabel(messages.encouragement())
        encouragement.setObjectName("hint")
        layout.addWidget(encouragement)
        layout.addStretch(1)

        action_row = QHBoxLayout()
        action_row.setSpacing(8)
        done = QPushButton("Done")
        done.setProperty("variant", "primary")
        done.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        done.clicked.connect(self._mark_done)

        snooze = QPushButton("Snooze ▾")
        snooze.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        snooze_menu = QMenu(snooze)
        for label, minutes in (("5 minutes", 5), ("15 minutes", 15), ("1 hour", 60)):
            action = snooze_menu.addAction(label)
            action.triggered.connect(lambda _checked=False, m=minutes: self._snooze(m))
        snooze.setMenu(snooze_menu)

        skip = QPushButton("Skip")
        skip.setProperty("variant", "ghost")
        skip.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        skip.clicked.connect(self._skip)

        action_row.addWidget(done)
        action_row.addWidget(snooze)
        action_row.addWidget(skip)
        layout.addLayout(action_row)

        footer = QHBoxLayout()
        open_list = QPushButton("Open task list  →")
        open_list.setProperty("variant", "link")
        open_list.setCursor(Qt.CursorShape.PointingHandCursor)
        open_list.clicked.connect(self._open_list)
        self.countdown = QLabel()
        self.countdown.setObjectName("hint")
        footer.addWidget(open_list)
        footer.addStretch(1)
        footer.addWidget(self.countdown)
        layout.addLayout(footer)

        self.progress = QProgressBar()
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(4)
        self.progress.setRange(0, self._seconds)
        self.progress.setValue(self._seconds)
        layout.addWidget(self.progress)

        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._tick)
        self._update_countdown()

    def _update_countdown(self) -> None:
        self.progress.setValue(self._remaining)
        self.countdown.setText(f"closes in {self._remaining}s")

    def _tick(self) -> None:
        self._remaining -= 1
        self._update_countdown()
        if self._remaining <= 0:
            self._dismiss()

    def show_with_slide(self) -> None:
        super().show_with_slide()
        self._timer.start()

    def closeEvent(self, event) -> None:  # type: ignore[override]
        self._timer.stop()
        super().closeEvent(event)

    def _stop_timer(self) -> None:
        self._timer.stop()

    def _mark_done(self) -> None:
        if self._resolved:
            return
        self._resolved = True
        self._stop_timer()
        self.done_requested.emit(int(self.task.id or 0))
        self.close()

    def _snooze(self, minutes: int) -> None:
        if self._resolved:
            return
        self._resolved = True
        self._stop_timer()
        self.snooze_requested.emit(int(self.task.id or 0), minutes)
        self.close()

    def _skip(self) -> None:
        if self._resolved:
            return
        self._resolved = True
        self._stop_timer()
        self.skip_requested.emit(int(self.task.id or 0))
        self.close()

    def _open_list(self) -> None:
        if self._resolved:
            return
        self._resolved = True
        self._stop_timer()
        self.open_list_requested.emit()
        self.close()

    def _dismiss(self) -> None:
        if self._resolved:
            return
        self._resolved = True
        self._stop_timer()
        self.auto_dismissed.emit(int(self.task.id or 0))
        self.close()


class SummaryPopup(AnimatedPopup):
    open_list_requested = pyqtSignal()

    def __init__(
        self,
        intro: str,
        headline: str,
        note: str,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(430, 319, parent)
        self._remaining = 45
        self._resolved = False
        layout = self._content_layout()

        top = QHBoxLayout()
        top.setSpacing(11)
        top.addWidget(AvatarWidget(59, mood="happy"))
        intro_stack = QVBoxLayout()
        intro_stack.setSpacing(2)
        eyebrow = QLabel("MORNING SUMMARY")
        eyebrow.setObjectName("eyebrow")
        intro_label = QLabel(intro)
        intro_label.setObjectName("muted")
        intro_stack.addWidget(eyebrow)
        intro_stack.addWidget(intro_label)
        top.addLayout(intro_stack, 1)
        close_button = self._close_button()
        close_button.clicked.connect(self._close)
        top.addWidget(close_button, 0, Qt.AlignmentFlag.AlignTop)
        layout.addLayout(top)

        headline_label = QLabel(headline)
        headline_label.setObjectName("summaryHeadline")
        headline_label.setWordWrap(True)
        headline_label.setTextFormat(Qt.TextFormat.PlainText)
        layout.addWidget(headline_label)

        note_label = QLabel(note)
        note_label.setObjectName("muted")
        note_label.setWordWrap(True)
        layout.addWidget(note_label)
        layout.addStretch(1)

        buttons = QHBoxLayout()
        buttons.setSpacing(8)
        open_list = QPushButton("Show my list")
        open_list.setProperty("variant", "ghost")
        open_list.clicked.connect(self._open_list)
        got_it = QPushButton("Got it")
        got_it.setProperty("variant", "primary")
        got_it.clicked.connect(self._close)
        buttons.addWidget(open_list)
        buttons.addWidget(got_it)
        layout.addLayout(buttons)

        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._tick)
        self._countdown = QLabel("closes in 45s")
        self._countdown.setObjectName("hint")
        self._countdown.setAlignment(Qt.AlignmentFlag.AlignRight)
        layout.addWidget(self._countdown)

    def show_with_slide(self) -> None:
        super().show_with_slide()
        self._timer.start()

    def closeEvent(self, event) -> None:  # type: ignore[override]
        self._timer.stop()
        super().closeEvent(event)

    def _tick(self) -> None:
        self._remaining -= 1
        self._countdown.setText(f"closes in {self._remaining}s")
        if self._remaining <= 0:
            self._close()

    def _open_list(self) -> None:
        if self._resolved:
            return
        self._resolved = True
        self._timer.stop()
        self.open_list_requested.emit()
        self.close()

    def _close(self) -> None:
        if self._resolved:
            return
        self._resolved = True
        self._timer.stop()
        self.close()
