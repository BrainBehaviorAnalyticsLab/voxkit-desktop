import math

from PyQt6.QtCore import QPointF, Qt
from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtWidgets import (
    QWidget,
)


class DNAStrandWidget(QWidget):
    """Decorative audio waveform widget for toolbar - homage to Wav2Vec"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(100)
        # Set size policy to expand horizontally
        from PyQt6.QtWidgets import QSizePolicy

        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        # Make the widget ignore mouse events so it's purely decorative
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        width = self.width()
        height = self.height()
        center_y = height / 2

        # Audio waveform parameters
        num_bars = max(40, int(width / 8))  # Number of vertical bars
        bar_spacing = width / num_bars
        max_amplitude = height * 0.4

        # Colors for audio waveform - reminiscent of audio visualizers
        wave_color = QColor(100, 149, 237, 120)  # Semi-transparent blue
        center_line_color = QColor(150, 150, 150, 60)  # Subtle center line

        # Draw center reference line
        painter.setPen(QPen(center_line_color, 1))
        painter.drawLine(QPointF(0, center_y), QPointF(width, center_y))

        # Draw waveform bars
        pen = QPen(wave_color, max(1.5, bar_spacing * 0.6))
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)

        for i in range(num_bars):
            x = i * bar_spacing + bar_spacing / 2

            # Create varied amplitudes using multiple sine waves for natural audio look
            # Mix different frequencies to simulate speech/audio envelope
            phase1 = (i / num_bars) * 4 * math.pi
            phase2 = (i / num_bars) * 7 * math.pi + 0.5
            phase3 = (i / num_bars) * 11 * math.pi + 1.2

            # Combine multiple frequencies with different amplitudes
            amplitude = 0.5 * math.sin(phase1) + 0.3 * math.sin(phase2) + 0.2 * math.sin(phase3)

            # Add some randomness for natural variation (deterministic based on position)
            amplitude *= 0.8 + 0.4 * math.sin(i * 0.7)

            # Scale to fit height
            bar_height = abs(amplitude) * max_amplitude

            # Draw vertical bar from center
            if amplitude >= 0:
                painter.drawLine(QPointF(x, center_y), QPointF(x, center_y - bar_height))
            else:
                painter.drawLine(QPointF(x, center_y), QPointF(x, center_y + bar_height))
