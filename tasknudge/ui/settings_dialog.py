"""Settings for reminder rhythm, quiet hours, sound and startup."""

from __future__ import annotations

from dataclasses import replace
from typing import Callable, Optional

from PyQt6.QtCore import QTime, Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)

from tasknudge.avatar import AvatarWidget
from tasknudge.config import Config
from tasknudge.paths import data_dir


class SettingsDialog(QDialog):
    def __init__(
        self,
        config: Config,
        autostart_enabled: bool,
        autostart_supported: bool,
        test_sound: Optional[Callable[[], None]] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._config = config
        self._autostart_initial = autostart_enabled
        self.updated_config: Optional[Config] = None
        self.start_with_windows = autostart_enabled
        self._test_sound = test_sound

        self.setWindowTitle("TaskNudge settings")
        self.setModal(True)
        self.setMinimumWidth(590)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 22, 24, 22)
        outer.setSpacing(13)

        header = QHBoxLayout()
        header.setSpacing(12)
        header.addWidget(AvatarWidget(52, mood="happy"))
        titles = QVBoxLayout()
        titles.setSpacing(1)
        heading = QLabel("Settings")
        heading.setObjectName("dialogTitle")
        subtitle = QLabel("Make the nudges fit your day, not the other way around.")
        subtitle.setObjectName("muted")
        titles.addWidget(heading)
        titles.addWidget(subtitle)
        header.addLayout(titles, 1)
        outer.addLayout(header)

        reminder_group = QGroupBox("Reminder rhythm")
        reminder_form = QFormLayout(reminder_group)
        reminder_form.setContentsMargins(14, 18, 14, 12)
        reminder_form.setHorizontalSpacing(18)
        reminder_form.setVerticalSpacing(10)

        interval_widget = QWidget()
        interval_layout = QHBoxLayout(interval_widget)
        interval_layout.setContentsMargins(0, 0, 0, 0)
        interval_layout.setSpacing(7)
        self.interval_min = QSpinBox()
        self.interval_min.setRange(1, 720)
        self.interval_min.setSuffix(" min")
        self.interval_min.setValue(config.interval_min_minutes)
        self.interval_max = QSpinBox()
        self.interval_max.setRange(1, 720)
        self.interval_max.setSuffix(" min")
        self.interval_max.setValue(config.interval_max_minutes)
        interval_layout.addWidget(self.interval_min)
        interval_layout.addWidget(QLabel("to"))
        interval_layout.addWidget(self.interval_max)
        interval_layout.addStretch(1)
        reminder_form.addRow("Random nudge every", interval_widget)

        self.auto_dismiss = QSpinBox()
        self.auto_dismiss.setRange(5, 600)
        self.auto_dismiss.setSuffix(" sec")
        self.auto_dismiss.setValue(config.auto_dismiss_seconds)
        reminder_form.addRow("Popup closes itself after", self.auto_dismiss)
        outer.addWidget(reminder_group)

        quiet_group = QGroupBox("Quiet time")
        quiet_layout = QVBoxLayout(quiet_group)
        quiet_layout.setContentsMargins(14, 18, 14, 12)
        quiet_layout.setSpacing(9)
        self.quiet_enabled = QCheckBox("No popups during quiet hours")
        self.quiet_enabled.setChecked(config.quiet_hours_enabled)
        quiet_layout.addWidget(self.quiet_enabled)

        quiet_row = QHBoxLayout()
        quiet_row.setSpacing(7)
        quiet_row.addWidget(QLabel("From"))
        self.quiet_start = QTimeEdit()
        self.quiet_start.setDisplayFormat("h:mm AP")
        self.quiet_start.setTime(QTime.fromString(config.quiet_start, "HH:mm"))
        self.quiet_end = QTimeEdit()
        self.quiet_end.setDisplayFormat("h:mm AP")
        self.quiet_end.setTime(QTime.fromString(config.quiet_end, "HH:mm"))
        quiet_row.addWidget(self.quiet_start)
        quiet_row.addWidget(QLabel("to"))
        quiet_row.addWidget(self.quiet_end)
        quiet_row.addStretch(1)
        quiet_layout.addLayout(quiet_row)

        summary_row = QHBoxLayout()
        summary_row.setSpacing(7)
        self.summary_enabled = QCheckBox("Morning summary at")
        self.summary_enabled.setChecked(config.morning_summary_enabled)
        self.summary_time = QTimeEdit()
        self.summary_time.setDisplayFormat("h:mm AP")
        self.summary_time.setTime(QTime.fromString(config.morning_summary_time, "HH:mm"))
        summary_row.addWidget(self.summary_enabled)
        summary_row.addWidget(self.summary_time)
        summary_row.addStretch(1)
        quiet_layout.addLayout(summary_row)
        outer.addWidget(quiet_group)

        experience_group = QGroupBox("Little details")
        experience_layout = QVBoxLayout(experience_group)
        experience_layout.setContentsMargins(14, 18, 14, 12)
        experience_layout.setSpacing(9)
        sound_row = QHBoxLayout()
        self.sound_enabled = QCheckBox("Play a soft chime")
        self.sound_enabled.setChecked(config.sound_enabled)
        self.test_sound_button = QPushButton("Preview")
        self.test_sound_button.setProperty("variant", "ghost")
        self.test_sound_button.clicked.connect(self._preview_sound)
        self.test_sound_button.setEnabled(self._test_sound is not None)
        sound_row.addWidget(self.sound_enabled)
        sound_row.addStretch(1)
        sound_row.addWidget(self.test_sound_button)
        experience_layout.addLayout(sound_row)

        self.autostart_check = QCheckBox("Start TaskNudge when I sign in")
        self.autostart_check.setChecked(autostart_enabled and autostart_supported)
        self.autostart_check.setEnabled(autostart_supported)
        self.autostart_check.setToolTip(
            "Adds TaskNudge to your Windows user startup items. No admin rights needed."
            if autostart_supported
            else "Automatic startup is currently implemented for Windows."
        )
        experience_layout.addWidget(self.autostart_check)
        if not autostart_supported:
            note = QLabel("Auto-start setup is currently Windows-only.")
            note.setObjectName("hint")
            experience_layout.addWidget(note)
        outer.addWidget(experience_group)

        data_hint = QLabel(f"Tasks and settings are saved in {data_dir()}")
        data_hint.setObjectName("hint")
        data_hint.setWordWrap(True)
        data_hint.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        data_hint.setToolTip(str(data_dir()))
        outer.addWidget(data_hint)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        save = buttons.button(QDialogButtonBox.StandardButton.Save)
        save.setText("Save settings")
        save.setProperty("variant", "primary")
        buttons.accepted.connect(self._validate_and_accept)
        buttons.rejected.connect(self.reject)
        outer.addWidget(buttons)

        self.quiet_enabled.toggled.connect(self._update_enabled)
        self.summary_enabled.toggled.connect(self._update_enabled)
        self._update_enabled()

    def _update_enabled(self) -> None:
        quiet = self.quiet_enabled.isChecked()
        self.quiet_start.setEnabled(quiet)
        self.quiet_end.setEnabled(quiet)
        self.summary_time.setEnabled(self.summary_enabled.isChecked())

    def _preview_sound(self) -> None:
        if self._test_sound is not None:
            self._test_sound()

    def _validate_and_accept(self) -> None:
        if self.interval_min.value() > self.interval_max.value():
            QMessageBox.warning(
                self,
                "Check the interval",
                "The shortest interval must be less than or equal to the longest interval.",
            )
            return
        if self.quiet_enabled.isChecked() and (
            self.quiet_start.time() == self.quiet_end.time()
        ):
            QMessageBox.warning(
                self,
                "Check quiet hours",
                "Quiet hours need a start and end that are different. "
                "Turn them off if you don't want a quiet window.",
            )
            return

        self.updated_config = replace(
            self._config,
            interval_min_minutes=self.interval_min.value(),
            interval_max_minutes=self.interval_max.value(),
            auto_dismiss_seconds=self.auto_dismiss.value(),
            quiet_hours_enabled=self.quiet_enabled.isChecked(),
            quiet_start=self.quiet_start.time().toString("HH:mm"),
            quiet_end=self.quiet_end.time().toString("HH:mm"),
            morning_summary_enabled=self.summary_enabled.isChecked(),
            morning_summary_time=self.summary_time.time().toString("HH:mm"),
            sound_enabled=self.sound_enabled.isChecked(),
        ).normalize()
        self.start_with_windows = (
            self.autostart_check.isChecked() if self.autostart_check.isEnabled() else False
        )
        self.accept()

    @property
    def autostart_changed(self) -> bool:
        return self.start_with_windows != self._autostart_initial
