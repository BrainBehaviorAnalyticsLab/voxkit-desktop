"""Toggle Switch Module.

Animated iOS-style toggle switch widget.

API
---
- **ToggleSwitch**: Custom toggle switch with smooth animation
"""

from PyQt6.QtCore import (  # type: ignore[attr-defined]
    QEasingCurve,
    QPropertyAnimation,
    QRect,
    Qt,
    pyqtProperty,
)
from PyQt6.QtGui import QBrush, QColor, QPainter, QPen
from PyQt6.QtWidgets import QWidget


class ToggleSwitch(QWidget):
    """Animated toggle switch widget.

    A custom iOS-style toggle switch with smooth thumb animation.

    Attributes:
        _checked: Current checked state.
        _thumb_pos: Animated thumb position for rendering.
    """

    def __init__(self, checked=False, parent=None):
        super().__init__(parent)
        self._checked = checked
        self._thumb_pos = 0
        self._animation = QPropertyAnimation(self, b"thumb_pos")
        self._animation.setDuration(150)
        self._animation.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self.setFixedSize(40, 22)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        # Initialize thumb position correctly
        self._thumb_pos = self.width() - self.height() if self._checked else 0

    # --- Expose to Qt's meta-system ---
    @pyqtProperty(float)  # type: ignore[no-redef]
    def thumb_pos(self):
        return self._thumb_pos

    @thumb_pos.setter  # type: ignore[no-redef]
    def thumb_pos(self, pos):
        self._thumb_pos = pos
        self.update()

    def mousePressEvent(self, event):
        self._checked = not self._checked
        start = self._thumb_pos
        end = self.width() - self.height() if self._checked else 0
        self._animation.stop()
        self._animation.setStartValue(start)
        self._animation.setEndValue(end)
        self._animation.start()
        self.update()

    def isChecked(self):
        return self._checked

    def setChecked(self, checked):
        self._checked = checked
        self._thumb_pos = self.width() - self.height() if checked else 0
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Track
        track_color = QColor("#4cd964") if self._checked else QColor("#d0d0d0")
        p.setBrush(QBrush(track_color))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(self.rect(), self.height() / 2, self.height() / 2)

        # Thumb
        thumb_rect = QRect(int(self._thumb_pos), 0, self.height(), self.height())
        p.setBrush(QBrush(Qt.GlobalColor.white))
        p.setPen(QPen(Qt.GlobalColor.lightGray))
        p.drawEllipse(thumb_rect)
