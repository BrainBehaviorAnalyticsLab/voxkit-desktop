"""Splash screen / loading dialog for long-running operations."""

import math

from PyQt6.QtCore import QEasingCurve, QPointF, QPropertyAnimation, Qt, QTimer
from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtWidgets import (
    QDialog,
    QFrame,
    QGraphicsOpacityEffect,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from voxkit.gui.styles import Colors, Labels


class _WaveformStrip(QWidget):
    """Animated audio waveform, matching the toolbar's decorative strip.

    Renders vertical bars radiating from a center line whose amplitudes are a
    mix of sine frequencies (a homage to Wav2Vec). A steadily advancing phase
    scrolls the pattern so it reads as a live audio meter.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._phase = 0.0
        self.setFixedHeight(56)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

    def advance(self, step: float = 0.18):
        """Advance the animation by one frame and repaint."""
        self._phase += step
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        width = self.width()
        height = self.height()
        center_y = height / 2

        num_bars = max(40, int(width / 8))
        bar_spacing = width / num_bars
        max_amplitude = height * 0.4

        # App primary blue (matches the border and palette), slightly translucent.
        wave_color = QColor(Colors.PRIMARY)
        wave_color.setAlpha(200)

        pen = QPen(wave_color, max(1.5, bar_spacing * 0.6))
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)

        for i in range(num_bars):
            x = i * bar_spacing + bar_spacing / 2

            # Mix a few frequencies for a natural speech-like envelope, offset
            # by the running phase so the waveform scrolls.
            phase1 = (i / num_bars) * 4 * math.pi + self._phase
            phase2 = (i / num_bars) * 7 * math.pi + 0.5 + self._phase
            phase3 = (i / num_bars) * 11 * math.pi + 1.2 + self._phase

            amplitude = 0.5 * math.sin(phase1) + 0.3 * math.sin(phase2) + 0.2 * math.sin(phase3)
            amplitude *= 0.8 + 0.4 * math.sin(i * 0.7 + self._phase)

            bar_height = abs(amplitude) * max_amplitude
            painter.drawLine(QPointF(x, center_y - bar_height), QPointF(x, center_y + bar_height))


class LoadingDialog(QDialog):
    """A modal loading dialog / first-launch splash screen.

    Shows the VoxKit name so users can tell what has launched, an animated
    audio waveform, the primary status message, and an optional subtitle to
    explain long-running work. It blocks user interaction with the main
    application until the operation completes.

    Args:
        message: The primary status message to display
        parent: Optional parent widget
        title: Brand/heading text shown at the top (defaults to "VoxKit")
        subtitle: Optional secondary hint shown below the message
    """

    def __init__(
        self,
        message: str = "Loading...",
        parent=None,
        *,
        title: str = "VoxKit",
        subtitle: str | None = None,
    ):
        super().__init__(parent)
        self.setModal(True)
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        # The window itself stays transparent; the visible card is painted by a
        # child QFrame so the gradient/border/rounded corners render reliably
        # (a stylesheet background on a translucent top-level window does not).
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.init_ui(message, title, subtitle)

        # Center the dialog on screen
        self.center_on_screen()

        # Setup fade-in animation
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)
        self.fade_in_animation = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_in_animation.setDuration(300)
        self.fade_in_animation.setStartValue(0.0)
        self.fade_in_animation.setEndValue(1.0)
        self.fade_in_animation.setEasingCurve(QEasingCurve.Type.InOutQuad)

        # Drive the waveform animation
        self.wave_timer = QTimer(self)
        self.wave_timer.timeout.connect(self.waveform.advance)
        self.wave_timer.start(50)  # ~20 fps

    def init_ui(self, message: str, title: str, subtitle: str | None):
        """Initialize the dialog UI."""
        # Outer layout holds a single card; the window behind it is transparent.
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        self._card = QFrame()
        self._card.setObjectName("card")
        outer.addWidget(self._card)

        layout = QVBoxLayout(self._card)
        layout.setContentsMargins(40, 32, 40, 32)
        layout.setSpacing(16)

        # Brand heading
        self._brand_title_label = QLabel(title)
        self._brand_title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._brand_title_label.setStyleSheet(
            f"""
            QLabel {{
                color: {Colors.PRIMARY};
                font-size: 26px;
                font-weight: bold;
                letter-spacing: 1px;
                background-color: transparent;
            }}
            """
        )
        layout.addWidget(self._brand_title_label)

        # Animated waveform (copied from the toolbar's decorative strip)
        self.waveform = _WaveformStrip()
        layout.addWidget(self.waveform)

        # Primary status message
        self.message_label = QLabel(message)
        self.message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.message_label.setWordWrap(True)
        self.message_label.setStyleSheet(
            f"""
            QLabel {{
                color: {Colors.TEXT_PRIMARY};
                font-size: 15px;
                font-weight: bold;
                background-color: transparent;
            }}
            """
        )
        layout.addWidget(self.message_label)

        # Optional secondary hint (e.g. "VoxKit will start when this finishes")
        self.subtitle_label = QLabel(subtitle or "")
        self.subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.subtitle_label.setWordWrap(True)
        self.subtitle_label.setStyleSheet(
            f"""
            QLabel {{
                color: {Colors.TEXT_SECONDARY};
                font-size: 12px;
                background-color: transparent;
            }}
            """
        )
        self.subtitle_label.setVisible(bool(subtitle))
        layout.addWidget(self.subtitle_label)

        # Fine-print institutional credit
        credit_label = QLabel(
            "VoxKit is brought to you by the University of Wisconsin-Madison "
            "and Arizona State University"
        )
        credit_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        credit_label.setWordWrap(True)
        credit_label.setStyleSheet(Labels.CREDIT)
        layout.addWidget(credit_label)

        # Card background: subtle vertical gradient (light tints of the app's
        # primary blue) with a primary-blue rounded border. Painted on the child
        # frame (not the translucent window) so it renders reliably.
        self._card.setStyleSheet(
            f"""
            QFrame#card {{
                background-color: qlineargradient(
                    x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 {Colors.WHITE},
                    stop: 1 #dbeef9
                );
                border-radius: 15px;
                border: 3px solid {Colors.PRIMARY};
            }}
            """
        )

        self.setFixedSize(420, 290)

    def center_on_screen(self):
        """Center the dialog on the primary screen."""
        from PyQt6.QtGui import QGuiApplication

        screen = QGuiApplication.primaryScreen()
        if screen is not None:
            screen_geometry = screen.geometry()
            dialog_rect = self.frameGeometry()
            center_point = screen_geometry.center()
            dialog_rect.moveCenter(center_point)
            self.move(dialog_rect.topLeft())

    def showEvent(self, event):
        """Override show event to trigger fade-in animation."""
        super().showEvent(event)
        self.fade_in_animation.start()

    def update_message(self, message: str):
        """Update the primary status message displayed in the dialog.

        Args:
            message: The new message to display
        """
        self.message_label.setText(message)

    def update_subtitle(self, subtitle: str):
        """Update the secondary hint line, showing or hiding it as needed.

        Args:
            subtitle: The new subtitle text (empty string hides the line)
        """
        self.subtitle_label.setText(subtitle)
        self.subtitle_label.setVisible(bool(subtitle))

    def close_gracefully(self):
        """Close the dialog with a fade-out animation."""
        self.wave_timer.stop()
        fade_out = QPropertyAnimation(self.opacity_effect, b"opacity")
        fade_out.setDuration(200)
        fade_out.setStartValue(1.0)
        fade_out.setEndValue(0.0)
        fade_out.setEasingCurve(QEasingCurve.Type.InOutQuad)
        fade_out.finished.connect(self.accept)
        fade_out.start()
        # Keep reference to prevent garbage collection
        self._fade_out = fade_out
