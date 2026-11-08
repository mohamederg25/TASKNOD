"""The application controller that connects every TaskNudge component."""

from __future__ import annotations

import logging
import random
from typing import Optional

from PyQt6.QtCore import QObject
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QMenu,
    QMessageBox,
    QSystemTrayIcon,
    QWidget,
)

from tasknudge import APP_NAME
from tasknudge import autostart
from tasknudge.avatar import make_app_icon
from tasknudge.config import Config
from tasknudge.messages import MessageBook
from tasknudge.scheduler import Scheduler
from tasknudge.sound import SoundPlayer
from tasknudge.storage import TaskStore
from tasknudge.ui.popup import AnimatedPopup, NudgePopup, SummaryPopup
from tasknudge.ui.settings_dialog import SettingsDialog
from tasknudge.ui.stats_dialog import StatsDialog
from tasknudge.ui.task_dialog import TaskDialog
from tasknudge.ui.task_list import TaskListWindow

log = logging.getLogger(__name__)
SKIP_DELAY_MINUTES = 30


class ApplicationController(QObject):
    def __init__(
        self,
        app: QApplication,
        config: Config,
        store: TaskStore,
    ) -> None:
        super().__init__()
        self.app = app
        self.config = config
        self.store = store
        self.messages = MessageBook()
        self.sound = SoundPlayer(config.sound_enabled, self)
        self.scheduler = Scheduler(config, store, self)
        self._popup: Optional[AnimatedPopup] = None
        self._hide_hint_shown = False
        self._shutting_down = False
        self._tray_available = QSystemTrayIcon.isSystemTrayAvailable()

        self.window = TaskListWindow()
        self._connect_window()
        self._build_tray()

        self.scheduler.reminder_ready.connect(self._show_nudge)
        self.scheduler.summary_ready.connect(self._show_summary)
        self.app.aboutToQuit.connect(self.shutdown)

    # ------------------------------------------------------------------ tray
    def _build_tray(self) -> None:
        self.tray = QSystemTrayIcon(make_app_icon(), self)
        self.tray.setToolTip(f"{APP_NAME} · your friendly task buddy")
        self._tray_menu = QMenu()
        self.add_action = QAction("Add Task…", self._tray_menu)
        self.view_action = QAction("View Tasks", self._tray_menu)
        self.pause_action = QAction("Pause reminders", self._tray_menu)
        self.settings_action = QAction("Settings…", self._tray_menu)
        self.quit_action = QAction("Quit", self._tray_menu)

        self.add_action.triggered.connect(self.show_add_task)
        self.view_action.triggered.connect(self.show_task_list)
        self.pause_action.triggered.connect(self._toggle_pause)
        self.settings_action.triggered.connect(self.show_settings)
        self.quit_action.triggered.connect(self.quit)

        self._tray_menu.addAction(self.add_action)
        self._tray_menu.addAction(self.view_action)
        self._tray_menu.addSeparator()
        self._tray_menu.addAction(self.pause_action)
        self._tray_menu.addAction(self.settings_action)
        self._tray_menu.addSeparator()
        self._tray_menu.addAction(self.quit_action)
        self.tray.setContextMenu(self._tray_menu)
        self.tray.activated.connect(self._tray_activated)

    def _tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            self.show_task_list()

    def _toggle_pause(self) -> None:
        self.set_paused(not self.config.paused)

    def set_paused(self, paused: bool) -> None:
        self.config.paused = paused
        self.config.save()
        self.scheduler.set_paused(paused)
        self._update_pause_ui()
        self.window.set_paused(paused)

    def _update_pause_ui(self) -> None:
        self.pause_action.setText("Resume reminders" if self.config.paused else "Pause reminders")
        state = "paused" if self.config.paused else "ready"
        self.tray.setToolTip(f"{APP_NAME} · {state}")
        self.window.set_paused(self.config.paused)

    # --------------------------------------------------------------- windows
    def _connect_window(self) -> None:
        self.window.add_requested.connect(self.show_add_task)
        self.window.edit_requested.connect(self.edit_task)
        self.window.delete_requested.connect(self.delete_task)
        self.window.completion_requested.connect(self._completion_from_list)
        self.window.settings_requested.connect(self.show_settings)
        self.window.stats_requested.connect(self.show_stats)
        self.window.pause_requested.connect(self.set_paused)
        self.window.hidden_to_tray.connect(self._window_hidden)

    def start(self, show_window: bool = True) -> None:
        self._refresh()
        if self._tray_available:
            self.tray.show()
            self._update_pause_ui()
        else:
            log.warning("System tray is unavailable; showing the task list instead")
            show_window = True
        if show_window:
            self.show_task_list()
        self.scheduler.start()

    def show_task_list(self) -> None:
        self._refresh()
        self.window.show_and_raise()

    def _window_hidden(self) -> None:
        if not self._hide_hint_shown and self._tray_available:
            self._hide_hint_shown = True
            self._notify("TaskNudge is still here in the tray. I'll nudge you later.", 3000)

    def show_add_task(self) -> None:
        dialog = TaskDialog(parent=self._dialog_parent())
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.task is not None:
            try:
                self.store.add_task(dialog.task)
            except Exception as exc:
                log.exception("Could not add task")
                QMessageBox.critical(dialog, "Could not add task", str(exc))
                return
            self._refresh()
            if not self.window.isVisible():
                self.show_task_list()

    def edit_task(self, task_id: int) -> None:
        task = self.store.get_task(task_id)
        if task is None:
            return
        dialog = TaskDialog(task, parent=self._dialog_parent())
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.task is not None:
            try:
                self.store.update_task(dialog.task)
            except Exception as exc:
                log.exception("Could not update task")
                QMessageBox.critical(dialog, "Could not save task", str(exc))
                return
            self._refresh()

    def delete_task(self, task_id: int) -> None:
        task = self.store.get_task(task_id)
        if task is None:
            return
        parent = self._dialog_parent()
        response = QMessageBox.question(
            parent,
            "Delete this task?",
            f'“{task.title}” will be removed, with no guilt and no undo.',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if response != QMessageBox.StandardButton.Yes:
            return
        if self._popup is not None and getattr(self._popup, "task", None) is not None:
            if self._popup.task.id == task_id:
                self._popup.close()
        self.store.delete_task(task_id)
        self._refresh()

    def _completion_from_list(self, task_id: int, completed: bool) -> None:
        if completed:
            self._complete_task(task_id, close_popup=True)
        else:
            self.store.reopen_task(task_id)
            self._refresh()

    def _complete_task(self, task_id: int, close_popup: bool) -> None:
        task = self.store.get_task(task_id)
        if task is None:
            return
        title = task.title
        updated, recurring = self.store.complete_task(task_id)
        if close_popup and self._popup is not None:
            current = getattr(self._popup, "task", None)
            if current is not None and current.id == task_id:
                self._popup.close()
        self._refresh()
        if updated is None:
            return
        if recurring:
            from tasknudge.util import due_description

            self._notify(
                self.messages.repeated_done(title, due_description(updated).lower()), 3600
            )
        else:
            self._notify(self.messages.done(title), 3600)

    def _dialog_parent(self) -> Optional[QWidget]:
        return self.window if self.window.isVisible() else None

    def show_stats(self) -> None:
        stats = self.store.statistics()
        line = self.messages.stats_line(
            int(stats.get("completed_today", 0)), int(stats.get("streak", 0))
        )
        dialog = StatsDialog(stats, line, parent=self._dialog_parent())
        dialog.exec()

    def show_settings(self) -> None:
        supported = autostart.is_supported()
        enabled = autostart.is_enabled() if supported else False
        dialog = SettingsDialog(
            self.config,
            autostart_enabled=enabled,
            autostart_supported=supported,
            test_sound=lambda: self.sound.play(force=True),
            parent=self._dialog_parent(),
        )
        if dialog.exec() != QDialog.DialogCode.Accepted or dialog.updated_config is None:
            return

        self.config = dialog.updated_config
        self.scheduler.config = self.config
        self.config.save()
        self.sound.set_enabled(self.config.sound_enabled)
        self.scheduler.reconfigure()
        self._update_pause_ui()
        self._refresh()

        if dialog.autostart_changed:
            try:
                autostart.set_enabled(dialog.start_with_windows)
            except OSError as exc:
                log.exception("Could not change auto-start")
                QMessageBox.warning(
                    self._dialog_parent(),
                    "Could not update auto-start",
                    "TaskNudge could not change the Windows startup entry:\n\n"
                    f"{exc}\n\nYou can try again from Settings.",
                )

    # --------------------------------------------------------------- popups
    def _show_nudge(self, task_id: int) -> None:
        if self._popup is not None:
            self.scheduler.popup_closed()
            return
        task = self.store.get_task(task_id)
        if task is None or task.completed:
            self.scheduler.popup_closed()
            return
        try:
            popup = NudgePopup(task, self.config, self.messages)
            popup.done_requested.connect(
                lambda tid: self._complete_task(tid, close_popup=False)
            )
            popup.snooze_requested.connect(self._snooze_task)
            popup.skip_requested.connect(self._skip_task)
            popup.auto_dismissed.connect(self._defer_dismissed)
            popup.open_list_requested.connect(self.show_task_list)
            popup.closed.connect(self._popup_closed)
            self._popup = popup
            self.sound.play()
            popup.show_with_slide()
        except Exception:
            log.exception("Could not show reminder popup")
            self._popup = None
            self.scheduler.popup_closed()

    def _show_summary(self) -> None:
        self.config.save()
        if self._popup is not None:
            self.scheduler.popup_closed()
            return
        try:
            stats = self.store.statistics()
            summary = self.store.summary_tasks()
            headline = self.messages.summary_line(
                int(summary["open"]),
                int(summary["due_today"]),
                int(summary["overdue"]),
            )
            note = self.messages.summary_note(
                int(stats["completed_today"]), int(stats["streak"])
            )
            popup = SummaryPopup(self.messages.summary_intro(), headline, note)
            popup.open_list_requested.connect(self.show_task_list)
            popup.closed.connect(self._popup_closed)
            self._popup = popup
            self.sound.play()
            popup.show_with_slide()
        except Exception:
            log.exception("Could not show morning summary")
            self._popup = None
            self.scheduler.popup_closed()

    def _popup_closed(self) -> None:
        self._popup = None
        self.scheduler.popup_closed()
        self._refresh()

    def _snooze_task(self, task_id: int, minutes: int) -> None:
        self.store.snooze_task(task_id, minutes)
        self._refresh()

    def _skip_task(self, task_id: int) -> None:
        self.store.defer_task(task_id, SKIP_DELAY_MINUTES)
        self._refresh()
        self._notify(self.messages.skipped(), 2200)

    def _defer_dismissed(self, task_id: int) -> None:
        minutes = random.randint(
            max(1, self.config.interval_min_minutes),
            max(1, self.config.interval_max_minutes),
        )
        self.store.defer_task(task_id, minutes)
        self._refresh()

    # ---------------------------------------------------------------- helpers
    def _refresh(self) -> None:
        try:
            self.window.set_tasks(self.store.list_tasks(include_completed=True))
            self.window.set_stats(self.store.statistics())
            self.window.set_paused(self.config.paused)
            self.scheduler.wake()
        except Exception:
            log.exception("Could not refresh tasks")

    def _notify(self, message: str, duration_ms: int = 3000) -> None:
        if self._tray_available and self.tray.isVisible():
            self.tray.showMessage(
                APP_NAME, message, QSystemTrayIcon.MessageIcon.Information, duration_ms
            )

    def quit(self) -> None:
        self.shutdown()
        self.app.quit()

    def shutdown(self) -> None:
        if self._shutting_down:
            return
        self._shutting_down = True
        self.scheduler.stop()
        if self._popup is not None:
            self._popup.close()
            self._popup = None
        self.window.prepare_quit()
        self.window.close()
        self.tray.hide()
        self.store.close()
