"""Loading Dialog Module.

Splash screen / loading dialog for long-running operations.

API
---
- **LoadingDialog**: Modal dialog with animated spinner and status message
"""

from PyQt6.QtCore import QEasingCurve, QPropertyAnimation, Qt, QTimer
from PyQt6.QtWidgets import QDialog, QGraphicsOpacityEffect, QLabel, QVBoxLayout


class LoadingDialog(QDialog):
    """A modal loading dialog with a message and spinner.

    This dialog is used to display a loading message while a long-running
    operation is in progress. It blocks user interaction with the main
    application until the operation completes.

    Args:
        message: The message to display in the dialog
        parent: Optional parent widget
    """

    def __init__(self, message: str = "Loading...", parent=None):
        super().__init__(parent)
        self.setModal(True)
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # Animation state
        self._spinner_index = 0
        self._spinner_frames = ["◐", "◓", "◑", "◒"]

        self.init_ui(message)

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

        # Setup spinner animation timer
        self.spinner_timer = QTimer(self)
        self.spinner_timer.timeout.connect(self._update_spinner)
        self.spinner_timer.start(150)  # Update every 150ms

    def init_ui(self, message: str):
        """Initialize the dialog UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)

        # Message label
        message_label = QLabel(message)
        message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        message_label.setStyleSheet(
            """
            QLabel {
                color: #2c3e50;
                font-size: 16px;
                font-weight: bold;
                background-color: #ffffff;
                padding: 20px;
                border-radius: 10px;
                border: 2px solid #3498db;
            }
            """
        )
        layout.addWidget(message_label)

        # Progress indicator label (animated spinner)
        self.progress_label = QLabel(self._spinner_frames[0])
        self.progress_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.progress_label.setStyleSheet(
            """
            QLabel {
                color: #3498db;
                font-size: 32px;
                background-color: #ffffff;
                padding: 10px;
                border-radius: 10px;
                font-weight: bold;
            }
            """
        )
        layout.addWidget(self.progress_label)

        # Set dialog background with shadow effect
        self.setStyleSheet(
            """
            QDialog {
                background-color: rgba(255, 255, 255, 250);
                border-radius: 15px;
                border: 3px solid #3498db;
            }
            """
        )

        self.setFixedSize(400, 250)

    def center_on_screen(self):
        """Center the dialog on the primary screen."""
        from PyQt6.QtGui import QGuiApplication

        screen = QGuiApplication.primaryScreen().geometry()
        dialog_rect = self.frameGeometry()
        center_point = screen.center()
        dialog_rect.moveCenter(center_point)
        self.move(dialog_rect.topLeft())

    def _update_spinner(self):
        """Update the spinner animation."""
        self._spinner_index = (self._spinner_index + 1) % len(self._spinner_frames)
        self.progress_label.setText(self._spinner_frames[self._spinner_index])

    def showEvent(self, event):
        """Override show event to trigger fade-in animation."""
        super().showEvent(event)
        self.fade_in_animation.start()

    def update_message(self, message: str):
        """Update the message displayed in the dialog.

        Args:
            message: The new message to display
        """
        if self.layout() and self.layout().itemAt(0):
            label = self.layout().itemAt(0).widget()
            if isinstance(label, QLabel):
                label.setText(message)

    def close_gracefully(self):
        """Close the dialog with a fade-out animation."""
        self.spinner_timer.stop()
        fade_out = QPropertyAnimation(self.opacity_effect, b"opacity")
        fade_out.setDuration(200)
        fade_out.setStartValue(1.0)
        fade_out.setEndValue(0.0)
        fade_out.setEasingCurve(QEasingCurve.Type.InOutQuad)
        fade_out.finished.connect(self.accept)
        fade_out.start()
        # Keep reference to prevent garbage collection
        self._fade_out = fade_out
