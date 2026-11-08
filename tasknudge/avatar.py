"""The tiny TaskNudge character, drawn programmatically with Qt."""

from __future__ import annotations

import random
from typing import Optional

from PyQt6.QtCore import QRectF, Qt, QTimer
from PyQt6.QtGui import (
    QColor,
    QIcon,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QRadialGradient,
)
from PyQt6.QtWidgets import QWidget

_BACKGROUND_TOP = QColor("#1d3d50")
_BACKGROUND_BOTTOM = QColor("#08141d")
_GLOW = QColor("#86e8ef")
_FACE = QColor("#f4ffff")


def _face_path(rect: QRectF) -> QPainterPath:
    path = QPainterPath()
    radius = rect.width() * 0.26
    path.addRoundedRect(rect, radius, radius)
    return path


def draw_face(
    painter: QPainter,
    rect: QRectF,
    mood: str = "friendly",
    blink: bool = False,
) -> None:
    """Paint the character into ``rect``; safe to reuse for widget and icons."""

    painter.save()
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

    margin = rect.width() * 0.045
    shape = rect.adjusted(margin, margin, -margin, -margin)
    path = _face_path(shape)

    # Soft outer glow, like the reference avatar sheet.
    painter.setBrush(Qt.BrushStyle.NoBrush)
    for step in range(5, 0, -1):
        glow_pen = QPen(QColor(134, 232, 239, 10 + (5 - step) * 7))
        glow_pen.setWidthF(max(1.0, rect.width() * 0.018 * step))
        painter.setPen(glow_pen)
        painter.drawPath(path)

    gradient = QRadialGradient(
        shape.center().x() - shape.width() * 0.22,
        shape.center().y() - shape.height() * 0.32,
        shape.width() * 0.9,
    )
    gradient.setColorAt(0.0, _BACKGROUND_TOP)
    gradient.setColorAt(1.0, _BACKGROUND_BOTTOM)
    painter.setPen(QPen(QColor("#5fcbd8"), max(1.0, rect.width() * 0.018)))
    painter.setBrush(gradient)
    painter.drawPath(path)

    # A glassy highlight across the top.
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(255, 255, 255, 18))
    highlight = QPainterPath()
    highlight.addRoundedRect(
        QRectF(
            shape.left() + shape.width() * 0.14,
            shape.top() + shape.height() * 0.09,
            shape.width() * 0.72,
            shape.height() * 0.25,
        ),
        shape.width() * 0.18,
        shape.height() * 0.14,
    )
    painter.drawPath(highlight)

    eye_y = shape.center().y() - shape.height() * 0.05
    eye_offset = shape.width() * 0.17
    eye_radius = shape.width() * 0.085

    for center_x in (shape.center().x() - eye_offset, shape.center().x() + eye_offset):
        if blink or mood == "sleepy":
            pen = QPen(_FACE)
            pen.setWidthF(max(1.4, shape.width() * 0.028))
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)
            painter.drawArc(
                QRectF(
                    center_x - eye_radius,
                    eye_y - eye_radius * 0.1,
                    eye_radius * 2,
                    eye_radius * 1.2,
                ),
                200 * 16,
                140 * 16,
            )
            continue

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(134, 232, 239, 24))
        painter.drawEllipse(
            QRectF(
                center_x - eye_radius * 1.55,
                eye_y - eye_radius * 1.55,
                eye_radius * 3.1,
                eye_radius * 3.1,
            )
        )
        painter.setBrush(_FACE)
        painter.drawEllipse(
            QRectF(
                center_x - eye_radius,
                eye_y - eye_radius,
                eye_radius * 2,
                eye_radius * 2,
            )
        )

    cheek_color = QColor(255, 139, 130, 82)
    painter.setBrush(cheek_color)
    cheek_size = shape.width() * 0.047
    for center_x in (
        shape.center().x() - shape.width() * 0.30,
        shape.center().x() + shape.width() * 0.30,
    ):
        painter.drawEllipse(
            QRectF(
                center_x - cheek_size,
                eye_y + shape.height() * 0.10,
                cheek_size * 2,
                cheek_size,
            )
        )

    mouth = QPainterPath()
    if mood == "happy":
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(_FACE)
        mouth.moveTo(shape.center().x() - shape.width() * 0.13, eye_y + shape.height() * 0.12)
        mouth.quadTo(
            shape.center().x(),
            eye_y + shape.height() * 0.30,
            shape.center().x() + shape.width() * 0.13,
            eye_y + shape.height() * 0.12,
        )
        mouth.quadTo(
            shape.center().x(),
            eye_y + shape.height() * 0.20,
            shape.center().x() - shape.width() * 0.13,
            eye_y + shape.height() * 0.12,
        )
        painter.drawPath(mouth)
    elif mood == "sleepy":
        pen = QPen(_FACE)
        pen.setWidthF(max(1.3, shape.width() * 0.024))
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawLine(
            int(shape.center().x() - shape.width() * 0.055),
            int(eye_y + shape.height() * 0.19),
            int(shape.center().x() + shape.width() * 0.055),
            int(eye_y + shape.height() * 0.19),
        )
    else:
        pen = QPen(_FACE)
        pen.setWidthF(max(1.8, shape.width() * 0.032))
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        mouth.moveTo(shape.center().x() - shape.width() * 0.12, eye_y + shape.height() * 0.13)
        mouth.quadTo(
            shape.center().x(),
            eye_y + shape.height() * 0.26,
            shape.center().x() + shape.width() * 0.12,
            eye_y + shape.height() * 0.13,
        )
        painter.drawPath(mouth)

    painter.restore()


def make_avatar_pixmap(size: int = 64, mood: str = "friendly") -> QPixmap:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    draw_face(painter, QRectF(0, 0, size, size), mood=mood)
    painter.end()
    return pixmap


def make_app_icon() -> QIcon:
    icon = QIcon()
    for size in (16, 20, 24, 32, 40, 48, 64, 128, 256):
        icon.addPixmap(make_avatar_pixmap(size))
    return icon


class AvatarWidget(QWidget):
    """A small blinking avatar. The blink timer runs only while visible."""

    def __init__(
        self,
        size: int = 62,
        mood: str = "friendly",
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._mood = mood
        self._blink = False
        self.setFixedSize(size, size)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self._blink_timer = QTimer(self)
        self._blink_timer.setSingleShot(True)
        self._blink_timer.timeout.connect(self._blink_once)
        self._unblink_timer = QTimer(self)
        self._unblink_timer.setSingleShot(True)
        self._unblink_timer.setInterval(130)
        self._unblink_timer.timeout.connect(self._finish_blink)

    def set_mood(self, mood: str) -> None:
        self._mood = mood
        self.update()

    def showEvent(self, event) -> None:  # type: ignore[override]
        super().showEvent(event)
        self._schedule_blink()

    def hideEvent(self, event) -> None:  # type: ignore[override]
        self._blink_timer.stop()
        self._unblink_timer.stop()
        self._blink = False
        super().hideEvent(event)

    def _schedule_blink(self) -> None:
        if self._mood == "sleepy":
            return
        self._blink_timer.start(random.randint(3800, 7200))

    def _blink_once(self) -> None:
        if not self.isVisible():
            return
        self._blink = True
        self.update()
        self._unblink_timer.start()

    def _finish_blink(self) -> None:
        self._blink = False
        self.update()
        if self.isVisible():
            self._schedule_blink()

    def paintEvent(self, event) -> None:  # type: ignore[override]
        painter = QPainter(self)
        draw_face(
            painter,
            QRectF(self.rect()).adjusted(1, 1, -1, -1),
            mood=self._mood,
            blink=self._blink,
        )
        painter.end()
