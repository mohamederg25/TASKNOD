"""Add or edit a task."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, time
from typing import Optional

from PyQt6.QtCore import QDate, QTime, Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)

from tasknudge.avatar import AvatarWidget
from tasknudge.models import Task


class TaskDialog(QDialog):
    def __init__(self, task: Optional[Task] = None, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._original = task
        self._is_edit = task is not None
        self.task: Optional[Task] = None
        self.setWindowTitle("Edit task" if self._is_edit else "Add a task")
        self.setModal(True)
        self.setMinimumWidth(550)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(16)

        header = QHBoxLayout()
        header.setSpacing(12)
        header.addWidget(AvatarWidget(52, mood="happy"))
        titles = QVBoxLayout()
        titles.setSpacing(2)
        heading = QLabel("Edit this task" if self._is_edit else "What needs doing?")
        heading.setObjectName("dialogTitle")
        subtitle = QLabel("Keep it small, specific and kind to future you.")
        subtitle.setObjectName("muted")
        titles.addWidget(heading)
        titles.addWidget(subtitle)
        header.addLayout(titles, 1)
        layout.addLayout(header)

        panel = QFrame()
        panel.setObjectName("panel")
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(18, 16, 18, 16)
        panel_layout.setSpacing(10)

        form = QFormLayout()
        form.setHorizontalSpacing(18)
        form.setVerticalSpacing(12)
        form.setLabelAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )

        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("e.g. Send the project update")
        self.title_edit.setMaxLength(160)
        form.addRow("Title", self.title_edit)

        self.notes_edit = QPlainTextEdit()
        self.notes_edit.setPlaceholderText("A little context, a link, or the first tiny step…")
        self.notes_edit.setFixedHeight(84)
        form.addRow("Notes", self.notes_edit)

        self.priority_combo = QComboBox()
        self.priority_combo.addItem("Low", 0)
        self.priority_combo.addItem("Medium", 1)
        self.priority_combo.addItem("High", 2)
        form.addRow("Priority", self.priority_combo)

        due_wrap = QWidget()
        due_layout = QVBoxLayout(due_wrap)
        due_layout.setContentsMargins(0, 0, 0, 0)
        due_layout.setSpacing(7)
        due_row = QHBoxLayout()
        due_row.setContentsMargins(0, 0, 0, 0)
        due_row.setSpacing(8)
        self.due_check = QCheckBox("Due date")
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("ddd, MMM d, yyyy")
        self.date_edit.setMinimumWidth(156)
        self.time_check = QCheckBox("At exact time")
        self.time_edit = QTimeEdit()
        self.time_edit.setDisplayFormat("h:mm AP")
        self.time_edit.setMinimumWidth(102)
        due_row.addWidget(self.due_check)
        due_row.addWidget(self.date_edit)
        due_row.addWidget(self.time_check)
        due_row.addWidget(self.time_edit)
        due_row.addStretch(1)
        due_layout.addLayout(due_row)
        hint = QLabel(
            "Timed tasks pop up at their exact time. Date-only tasks join the random rotation."
        )
        hint.setObjectName("hint")
        hint.setWordWrap(True)
        due_layout.addWidget(hint)
        form.addRow("When", due_wrap)

        self.repeat_combo = QComboBox()
        self.repeat_combo.addItem("Doesn't repeat", None)
        self.repeat_combo.addItem("Every day", "daily")
        self.repeat_combo.addItem("Every week", "weekly")
        form.addRow("Repeat", self.repeat_combo)

        panel_layout.addLayout(form)
        layout.addWidget(panel)

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        save_button = self.button_box.button(QDialogButtonBox.StandardButton.Save)
        save_button.setText("Save changes" if self._is_edit else "Add task")
        save_button.setProperty("variant", "primary")
        self.button_box.accepted.connect(self._validate_and_accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

        self._load(task)
        self.due_check.toggled.connect(self._update_due_state)
        self.time_check.toggled.connect(self._time_toggled)
        self.repeat_combo.currentIndexChanged.connect(self._repeat_changed)
        self._update_due_state()
        self.title_edit.setFocus()

    def _load(self, task: Optional[Task]) -> None:
        now = datetime.now()
        default_time = (now.hour + 1) if now.hour < 23 else 23
        if task is None:
            self.priority_combo.setCurrentIndex(1)
            self.date_edit.setDate(QDate.currentDate())
            self.time_edit.setTime(QTime(default_time, 0))
            self.due_check.setChecked(False)
            self.time_check.setChecked(False)
            return

        self.title_edit.setText(task.title)
        self.notes_edit.setPlainText(task.notes)
        index = self.priority_combo.findData(task.priority)
        self.priority_combo.setCurrentIndex(max(0, index))
        repeat_index = self.repeat_combo.findData(task.repeat_rule)
        self.repeat_combo.setCurrentIndex(max(0, repeat_index))

        if task.due_at:
            self.due_check.setChecked(True)
            self.date_edit.setDate(
                QDate(task.due_at.year, task.due_at.month, task.due_at.day)
            )
            self.time_edit.setTime(QTime(task.due_at.hour, task.due_at.minute))
            self.time_check.setChecked(task.due_has_time)
        else:
            self.due_check.setChecked(False)
            self.date_edit.setDate(QDate.currentDate())
            self.time_edit.setTime(QTime(default_time, 0))
            self.time_check.setChecked(False)

    def _update_due_state(self) -> None:
        due_enabled = self.due_check.isChecked()
        self.date_edit.setEnabled(due_enabled)
        self.time_check.setEnabled(due_enabled)
        self.time_edit.setEnabled(due_enabled and self.time_check.isChecked())
        if not due_enabled:
            self.time_check.setChecked(False)

    def _time_toggled(self, checked: bool) -> None:
        if checked and not self.due_check.isChecked():
            self.due_check.setChecked(True)
        self._update_due_state()

    def _repeat_changed(self, _index: int = -1) -> None:
        if self.repeat_combo.currentData() and not self.due_check.isChecked():
            self.due_check.setChecked(True)

    def _validate_and_accept(self) -> None:
        title = self.title_edit.text().strip()
        if not title:
            QMessageBox.warning(
                self,
                "A title, please",
                "Give this task a short title so your reminder has something to say.",
            )
            self.title_edit.setFocus()
            return

        due_at: Optional[datetime] = None
        due_has_time = False
        if self.due_check.isChecked():
            due_date = self.date_edit.date().toPyDate()
            if self.time_check.isChecked():
                due_time = self.time_edit.time().toPyTime()
                due_has_time = True
            else:
                due_time = time(0, 0)
            due_at = datetime.combine(due_date, due_time)

        repeat_rule = self.repeat_combo.currentData()
        if repeat_rule and due_at is None:
            QMessageBox.warning(
                self,
                "Needs a due date",
                "Repeating tasks need a due date so TaskNudge knows when the next one starts.",
            )
            self.due_check.setChecked(True)
            return

        task = replace(self._original) if self._original is not None else Task()
        task.title = title
        task.notes = self.notes_edit.toPlainText().strip()
        task.priority = int(self.priority_combo.currentData())
        task.due_at = due_at
        task.due_has_time = due_has_time
        task.repeat_rule = repeat_rule
        self.task = task
        self.accept()
