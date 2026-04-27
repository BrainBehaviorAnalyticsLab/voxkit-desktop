"""Custom QSplitter with a visible grip handle for intuitive resizing."""

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPainter
from PyQt6.QtWidgets import QSplitter, QSplitterHandle


class GripSplitterHandle(QSplitterHandle):
    """Custom splitter handle with a visible grip indicator."""

    def __init__(self, orientation, parent):
        super().__init__(orientation, parent)
        if orientation == Qt.Orientation.Vertical:
            self.setCursor(Qt.CursorShape.SplitVCursor)
        else:
            self.setCursor(Qt.CursorShape.SplitHCursor)

    def paintEvent(self, event):
        """Draw the handle with grip dots."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw background
        bg_color = QColor("#ecf0f1")
        if self.underMouse():
            bg_color = QColor("#d5dbdb")
        painter.fillRect(self.rect(), bg_color)

        # Draw border lines
        border_color = QColor("#bdc3c7")
        if self.underMouse():
            border_color = QColor("#3498db")
        painter.setPen(border_color)

        if self.orientation() == Qt.Orientation.Vertical:
            painter.drawLine(0, 0, self.width(), 0)
            painter.drawLine(0, self.height() - 1, self.width(), self.height() - 1)
        else:
            painter.drawLine(0, 0, 0, self.height())
            painter.drawLine(self.width() - 1, 0, self.width() - 1, self.height())

        # Draw grip dots in the center
        grip_color = QColor("#95a5a6")
        if self.underMouse():
            grip_color = QColor("#3498db")
        painter.setBrush(grip_color)
        painter.setPen(Qt.PenStyle.NoPen)

        center_x = self.width() // 2
        center_y = self.height() // 2
        dot_radius = 2
        dot_spacing = 8

        # Draw 5 dots along the handle
        for i in range(-2, 3):
            if self.orientation() == Qt.Orientation.Vertical:
                x = center_x + (i * dot_spacing)
                y = center_y
            else:
                x = center_x
                y = center_y + (i * dot_spacing)
            painter.drawEllipse(x - dot_radius, y - dot_radius, dot_radius * 2, dot_radius * 2)

        painter.end()


class GripSplitter(QSplitter):
    """QSplitter with custom grip handles for better discoverability."""

    def createHandle(self):
        return GripSplitterHandle(self.orientation(), self)
