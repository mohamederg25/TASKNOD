"""A small, friendly progress view."""

from __future__ import annotations

from datetime import date
from typing import Optional

from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from tasknudge.avatar import AvatarWidget


class WeekChart(QWidget):
    def __init__(
        self,
        data: list[tuple[date, int]],
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._data = data
        self.setMinimumHeight(132)

    def paintEvent(self, event) -> None:  # type: ignore[override]
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        area = QRectF(self.rect()).adjusted(8, 18, -8, -23)
        if area.width() <= 0 or area.height() <= 0:
            painter.end()
            return

        baseline = area.bottom()
        maximum = max(1, max((count for _, count in self._data), default=0))
        slot_width = area.width() / max(1, len(self._data))
        bar_width = min(30.0, slot_width * 0.50)
        today = date.today()

        painter.setPen(QPen(QColor("#263b46"), 1))
        painter.drawLine(area.left(), baseline, area.right(), baseline)

        label_font = QFont("Segoe UI", 8)
        count_font = QFont("Segoe UI", 8)
        count_font.setWeight(QFont.Weight.DemiBold)

        for index, (day, count) in enumerate(self._data):
            center_x = area.left() + slot_width * (index + 0.5)
            height = (area.height() - 16) * (count / maximum) if count else 3.0
            height = max(3.0, height)
            bar_rect = QRectF(
                center_x - bar_width / 2,
                baseline - height,
                bar_width,
                height,
            )
            path = QPainterPath()
            path.addRoundedRect(bar_rect, 5, 5)
            if day == today:
                color = QColor("#71e2c3")
            elif count:
                color = QColor("#3f8f80")
            else:
                color = QColor("#29414b")
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(color)
            painter.drawPath(path)

            if count:
                painter.setFont(count_font)
                painter.setPen(QPen(QColor("#c8dce2")))
                painter.drawText(
                    QRectF(center_x - slot_width / 2, baseline - height - 18, slot_width, 15),
                    Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom,
                    str(count),
                )

            painter.setFont(label_font)
            painter.setPen(QPen(QColor("#6fdfc3" if day == today else "#7894a1")))
            painter.drawText(
                QRectF(center_x - slot_width / 2, baseline + 5, slot_width, 16),
                Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
                day.strftime("%a"),
            )
        painter.end()


class StatsDialog(QDialog):
    def __init__(
        self,
        stats: dict,
        encouragement: str,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("TaskNudge progress")
        self.setModal(True)
        self.setMinimumWidth(570)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 22, 24, 20)
        outer.setSpacing(14)

        header = QHBoxLayout()
        header.setSpacing(12)
        header.addWidget(AvatarWidget(54, mood="happy"))
        titles = QVBoxLayout()
        titles.setSpacing(1)
        heading = QLabel("Your progress")
        heading.setObjectName("dialogTitle")
        subtitle = QLabel("Small wins, quietly collected.")
        subtitle.setObjectName("muted")
        titles.addWidget(heading)
        titles.addWidget(subtitle)
        header.addLayout(titles, 1)
        outer.addLayout(header)

        message = QLabel(encouragement)
        message.setObjectName("muted")
        message.setWordWrap(True)
        outer.addWidget(message)

        cards = QGridLayout()
        cards.setSpacing(10)
        overdue = int(stats.get("overdue_count", 0))
        open_caption = "open"
        if overdue:
            open_caption += f" · {overdue} overdue"
        cards.addWidget(
            self._stat_card(str(stats.get("completed_today", 0)), "completed today"),
            0,
            0,
        )
        cards.addWidget(
            self._stat_card(str(stats.get("completed_week", 0)), "completed this week"),
            0,
            1,
        )
        cards.addWidget(
            self._stat_card(str(stats.get("streak", 0)), "days in a row"),
            1,
            0,
        )
        cards.addWidget(
            self._stat_card(str(stats.get("open_count", 0)), open_caption),
            1,
            1,
        )
        outer.addLayout(cards)

        chart_panel = QFrame()
        chart_panel.setObjectName("panel")
        chart_layout = QVBoxLayout(chart_panel)
        chart_layout.setContentsMargins(16, 12, 16, 10)
        chart_layout.setSpacing(2)
        chart_title = QLabel("Last 7 days")
        chart_title.setObjectName("eyebrow")
        chart_layout.addWidget(chart_title)
        chart_layout.addWidget(WeekChart(stats.get("week_chart", [])))
        outer.addWidget(chart_panel)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        close_button = buttons.button(QDialogButtonBox.StandardButton.Close)
        close_button.setText("Back to my day")
        close_button.setProperty("variant", "primary")
        buttons.rejected.connect(self.reject)
        outer.addWidget(buttons)

    @staticmethod
    def _stat_card(value: str, caption: str) -> QFrame:
        card = QFrame()
        card.setObjectName("panel")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(15, 11, 15, 11)
        layout.setSpacing(0)
        value_label = QLabel(value)
        value_label.setObjectName("statValue")
        caption_label = QLabel(caption)
        caption_label.setObjectName("statCaption")
        layout.addWidget(value_label)
        layout.addWidget(caption_label)
        return card
