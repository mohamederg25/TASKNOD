"""The task manager window."""

from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import QTimer, Qt, pyqtSignal
from PyQt6.QtGui import QAction, QBrush, QColor, QFont, QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMainWindow,
    QMenu,
    QPushButton,
    QStackedWidget,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from tasknudge.avatar import AvatarWidget
from tasknudge.models import PRIORITY_COLORS, PRIORITY_SHORT_LABELS, Task
from tasknudge.util import due_description, is_due_today, is_task_overdue, local_now


class TaskListWindow(QMainWindow):
    add_requested = pyqtSignal()
    edit_requested = pyqtSignal(int)
    delete_requested = pyqtSignal(int)
    completion_requested = pyqtSignal(int, bool)
    settings_requested = pyqtSignal()
    stats_requested = pyqtSignal()
    pause_requested = pyqtSignal(bool)
    hidden_to_tray = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self._tasks: list[Task] = []
        self._stats: dict = {}
        self._building = False
        self._handling_toggle = False
        self._allow_close = False
        self._paused = False

        self.setWindowTitle("TaskNudge")
        self.resize(900, 650)
        self.setMinimumSize(760, 520)

        central = QWidget()
        self.setCentralWidget(central)
        outer = QVBoxLayout(central)
        outer.setContentsMargins(28, 24, 28, 20)
        outer.setSpacing(15)

        header = QHBoxLayout()
        header.setSpacing(13)
        header.addWidget(AvatarWidget(64))
        title_stack = QVBoxLayout()
        title_stack.setSpacing(1)
        title = QLabel("TaskNudge")
        title.setObjectName("appTitle")
        subtitle = QLabel("A tiny nudge, a lighter day.")
        subtitle.setObjectName("muted")
        title_stack.addWidget(title)
        title_stack.addWidget(subtitle)
        header.addLayout(title_stack)
        header.addStretch(1)

        self.stats_button = QPushButton("Stats")
        self.stats_button.setProperty("variant", "ghost")
        self.stats_button.clicked.connect(self.stats_requested.emit)
        self.settings_button = QPushButton("Settings")
        self.settings_button.setProperty("variant", "ghost")
        self.settings_button.clicked.connect(self.settings_requested.emit)
        header.addWidget(self.stats_button)
        header.addWidget(self.settings_button)
        outer.addLayout(header)

        stats_bar = QFrame()
        stats_bar.setObjectName("statsBar")
        stats_layout = QHBoxLayout(stats_bar)
        stats_layout.setContentsMargins(14, 9, 14, 9)
        stats_layout.setSpacing(8)
        self.chip_open = QLabel("0 open")
        self.chip_today = QLabel("0 due today")
        self.chip_done = QLabel("0 done today")
        self.chip_streak = QLabel("0-day streak")
        for chip in (
            self.chip_open,
            self.chip_today,
            self.chip_done,
            self.chip_streak,
        ):
            chip.setObjectName("chip")
            stats_layout.addWidget(chip)
        stats_layout.addStretch(1)
        self.paused_label = QLabel("PAUSED")
        self.paused_label.setObjectName("statusPaused")
        self.paused_label.hide()
        stats_layout.addWidget(self.paused_label)
        outer.addWidget(stats_bar)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)
        self.add_button = QPushButton("+  Add task")
        self.add_button.setProperty("variant", "primary")
        self.add_button.clicked.connect(self.add_requested.emit)
        self.done_button = QPushButton("Mark done")
        self.done_button.clicked.connect(self._toggle_selected)
        self.edit_button = QPushButton("Edit")
        self.edit_button.setProperty("variant", "ghost")
        self.edit_button.clicked.connect(self._edit_selected)
        self.delete_button = QPushButton("Delete")
        self.delete_button.setProperty("variant", "danger")
        self.delete_button.clicked.connect(self._delete_selected)
        toolbar.addWidget(self.add_button)
        toolbar.addWidget(self.done_button)
        toolbar.addWidget(self.edit_button)
        toolbar.addWidget(self.delete_button)
        toolbar.addStretch(1)
        filter_label = QLabel("Show")
        filter_label.setObjectName("muted")
        self.filter_combo = QComboBox()
        self.filter_combo.addItem("Open tasks", "open")
        self.filter_combo.addItem("Completed", "completed")
        self.filter_combo.addItem("All tasks", "all")
        self.filter_combo.currentIndexChanged.connect(self._refresh_tree)
        toolbar.addWidget(filter_label)
        toolbar.addWidget(self.filter_combo)
        outer.addLayout(toolbar)

        self.stack = QStackedWidget()
        self.tree = QTreeWidget()
        self.tree.setColumnCount(4)
        self.tree.setHeaderLabels(["Task", "Priority", "Due", "Repeats"])
        self.tree.setRootIsDecorated(False)
        self.tree.setIndentation(0)
        self.tree.setAllColumnsShowFocus(True)
        self.tree.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tree.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tree.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tree.setAlternatingRowColors(True)
        self.tree.setUniformRowHeights(True)
        self.tree.setTextElideMode(Qt.TextElideMode.ElideRight)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._show_context_menu)
        self.tree.itemDoubleClicked.connect(lambda *_: self._edit_selected())
        self.tree.itemChanged.connect(self._item_changed)
        self.tree.currentItemChanged.connect(lambda *_: self._update_actions())
        header_view = self.tree.header()
        header_view.setStretchLastSection(False)
        header_view.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header_view.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        header_view.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        header_view.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.tree.setColumnWidth(1, 84)
        self.tree.setColumnWidth(2, 174)
        self.tree.setColumnWidth(3, 86)
        self.stack.addWidget(self.tree)

        empty = QWidget()
        empty_layout = QVBoxLayout(empty)
        empty_layout.setSpacing(8)
        empty_layout.addStretch(1)
        self.empty_avatar = AvatarWidget(84, mood="happy")
        empty_layout.addWidget(self.empty_avatar, 0, Qt.AlignmentFlag.AlignHCenter)
        self.empty_title = QLabel("All clear")
        self.empty_title.setObjectName("emptyTitle")
        self.empty_title.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.empty_detail = QLabel("Enjoy the quiet.")
        self.empty_detail.setObjectName("muted")
        self.empty_detail.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        empty_layout.addWidget(self.empty_title)
        empty_layout.addWidget(self.empty_detail)
        empty_layout.addStretch(1)
        self.stack.addWidget(empty)
        outer.addWidget(self.stack, 1)

        footer = QHBoxLayout()
        self.pause_button = QPushButton("Pause reminders")
        self.pause_button.setProperty("variant", "ghost")
        self.pause_button.setCheckable(True)
        self.pause_button.toggled.connect(self._pause_toggled)
        self.footer_status = QLabel("Closing this window keeps me napping in the tray.")
        self.footer_status.setObjectName("hint")
        footer.addWidget(self.pause_button)
        footer.addWidget(self.footer_status)
        footer.addStretch(1)
        outer.addLayout(footer)

        self._update_actions()
        self._refresh_tree()

        self._shortcuts: list[QShortcut] = []
        for sequence, handler in (
            (QKeySequence("Ctrl+N"), self.add_requested.emit),
            (QKeySequence("Delete"), self._delete_selected),
            (QKeySequence("Escape"), self.hide),
        ):
            shortcut = QShortcut(sequence, self)
            shortcut.activated.connect(handler)
            self._shortcuts.append(shortcut)

    def set_tasks(self, tasks: list[Task]) -> None:
        self._tasks = tasks
        self._refresh_tree()

    def set_stats(self, stats: dict) -> None:
        self._stats = stats
        self.chip_open.setText(f"{stats.get('open_count', 0)} open")
        self.chip_today.setText(f"{stats.get('due_today_count', 0)} due today")
        self.chip_done.setText(f"{stats.get('completed_today', 0)} done today")
        streak = int(stats.get("streak", 0))
        self.chip_streak.setText(f"{streak}-day streak")
        self.chip_streak.setToolTip(
            "Consecutive days with at least one completed task."
        )
        if stats.get("overdue_count"):
            self.chip_today.setToolTip(f"{stats['overdue_count']} task(s) overdue")

    def set_paused(self, paused: bool) -> None:
        self._paused = paused
        self.pause_button.blockSignals(True)
        self.pause_button.setChecked(paused)
        self.pause_button.setText("Resume reminders" if paused else "Pause reminders")
        self.pause_button.blockSignals(False)
        self.paused_label.setVisible(paused)
        self.footer_status.setText(
            "Reminders are paused. Take your time."
            if paused
            else "Closing this window keeps me napping in the tray."
        )

    def _pause_toggled(self, paused: bool) -> None:
        self.pause_requested.emit(paused)

    def _visible_tasks(self) -> list[Task]:
        mode = self.filter_combo.currentData()
        if mode == "open":
            return [task for task in self._tasks if not task.completed]
        if mode == "completed":
            return [task for task in self._tasks if task.completed]
        return list(self._tasks)

    def _refresh_tree(self, *_args: object) -> None:
        visible = self._visible_tasks()
        self._building = True
        self.tree.blockSignals(True)
        self.tree.clear()
        now = local_now()
        for task in visible:
            if task.id is None:
                continue
            item = QTreeWidgetItem()
            item.setData(0, Qt.ItemDataRole.UserRole, task.id)
            item.setData(0, Qt.ItemDataRole.UserRole + 1, task.completed)
            item.setFlags(
                Qt.ItemFlag.ItemIsEnabled
                | Qt.ItemFlag.ItemIsSelectable
                | Qt.ItemFlag.ItemIsUserCheckable
            )
            item.setCheckState(
                0,
                Qt.CheckState.Checked if task.completed else Qt.CheckState.Unchecked,
            )
            item.setText(0, task.title + ("   ✎" if task.notes else ""))
            item.setToolTip(0, task.title + (f"\n\n{task.notes}" if task.notes else ""))

            item.setText(1, PRIORITY_SHORT_LABELS.get(task.priority, "MED"))
            item.setForeground(1, QBrush(QColor(PRIORITY_COLORS.get(task.priority, "#f2bd73"))))
            item.setTextAlignment(1, Qt.AlignmentFlag.AlignCenter)
            if task.priority >= 2:
                font = item.font(1)
                font.setWeight(QFont.Weight.DemiBold)
                item.setFont(1, font)

            due_text = due_description(task, now)
            item.setText(2, due_text)
            if is_task_overdue(task, now):
                item.setForeground(2, QBrush(QColor("#ff9c8e")))
            elif is_due_today(task, now):
                item.setForeground(2, QBrush(QColor("#f2bd73")))
            else:
                item.setForeground(2, QBrush(QColor("#93acb9")))
            item.setToolTip(2, due_text)

            item.setText(3, task.repeat_label)
            item.setForeground(3, QBrush(QColor("#93acb9")))
            item.setTextAlignment(3, Qt.AlignmentFlag.AlignCenter)

            if task.completed:
                for column in range(4):
                    font = item.font(column)
                    font.setStrikeOut(True)
                    item.setFont(column, font)
                    item.setForeground(column, QBrush(QColor("#647d89")))

            self.tree.addTopLevelItem(item)
        self.tree.blockSignals(False)
        self._building = False

        has_rows = self.tree.topLevelItemCount() > 0
        self.stack.setCurrentIndex(0 if has_rows else 1)
        if not has_rows:
            mode = self.filter_combo.currentData()
            if mode == "completed":
                self.empty_title.setText("Nothing finished yet")
                self.empty_detail.setText("Your completed wins will appear here.")
            elif mode == "open":
                self.empty_title.setText("All clear")
                self.empty_detail.setText("Nothing is waiting. Go enjoy the quiet.")
            else:
                self.empty_title.setText("A fresh start")
                self.empty_detail.setText("Add your first tiny task when you're ready.")
        self._update_actions()

    def _selected_task(self) -> Optional[Task]:
        item = self.tree.currentItem()
        if item is None:
            return None
        task_id = item.data(0, Qt.ItemDataRole.UserRole)
        return next((task for task in self._tasks if task.id == task_id), None)

    def _update_actions(self) -> None:
        task = self._selected_task()
        enabled = task is not None
        self.done_button.setEnabled(enabled)
        self.edit_button.setEnabled(enabled)
        self.delete_button.setEnabled(enabled)
        if task:
            self.done_button.setText("Reopen" if task.completed else "Mark done")

    def _toggle_selected(self) -> None:
        task = self._selected_task()
        if task is None or task.id is None:
            return
        self.completion_requested.emit(task.id, not task.completed)

    def _edit_selected(self) -> None:
        task = self._selected_task()
        if task is None or task.id is None:
            return
        self.edit_requested.emit(task.id)

    def _delete_selected(self) -> None:
        task = self._selected_task()
        if task is None or task.id is None:
            return
        self.delete_requested.emit(task.id)

    def _item_changed(self, item: QTreeWidgetItem, column: int) -> None:
        if self._building or column != 0 or self._handling_toggle:
            return
        task_id = item.data(0, Qt.ItemDataRole.UserRole)
        previous = bool(item.data(0, Qt.ItemDataRole.UserRole + 1))
        checked = item.checkState(0) == Qt.CheckState.Checked
        if task_id is None or checked == previous:
            return
        self._handling_toggle = True

        def finish() -> None:
            self._handling_toggle = False
            self.completion_requested.emit(int(task_id), checked)

        QTimer.singleShot(0, finish)

    def _show_context_menu(self, position) -> None:
        item = self.tree.itemAt(position)
        if item is None:
            return
        self.tree.setCurrentItem(item)
        task = self._selected_task()
        if task is None:
            return
        menu = QMenu(self)
        toggle = QAction("Reopen task" if task.completed else "Mark done", menu)
        toggle.triggered.connect(self._toggle_selected)
        edit = QAction("Edit task", menu)
        edit.triggered.connect(self._edit_selected)
        delete = QAction("Delete task", menu)
        delete.triggered.connect(self._delete_selected)
        menu.addAction(toggle)
        menu.addAction(edit)
        menu.addSeparator()
        menu.addAction(delete)
        menu.exec(self.tree.viewport().mapToGlobal(position))

    def show_and_raise(self) -> None:
        if self.isMinimized():
            self.showNormal()
        self.show()
        self.raise_()
        self.activateWindow()

    def prepare_quit(self) -> None:
        self._allow_close = True

    def closeEvent(self, event) -> None:  # type: ignore[override]
        if self._allow_close:
            event.accept()
            return
        event.ignore()
        self.hide()
        self.hidden_to_tray.emit()
