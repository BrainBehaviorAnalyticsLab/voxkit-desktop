"""Loading Dialog Component.

This module provides a splash screen/loading dialog for displaying progress
during long-running operations like first-launch startup scripts.
"""

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QMovie
from PyQt6.QtWidgets import QDialog, QLabel, QVBoxLayout


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
        self.init_ui(message)

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

        # Progress indicator label
        self.progress_label = QLabel("●")
        self.progress_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.progress_label.setStyleSheet(
            """
            QLabel {
                color: #3498db;
                font-size: 24px;
                background-color: #ffffff;
                padding: 10px;
                border-radius: 10px;
            }
            """
        )
        layout.addWidget(self.progress_label)

        # Set dialog background
        self.setStyleSheet(
            """
            QDialog {
                background-color: rgba(255, 255, 255, 240);
                border-radius: 15px;
            }
            """
        )

        self.setFixedSize(350, 200)

    def update_message(self, message: str):
        """Update the message displayed in the dialog.

        Args:
            message: The new message to display
        """
        if self.layout() and self.layout().itemAt(0):
            label = self.layout().itemAt(0).widget()
            if isinstance(label, QLabel):
                label.setText(message)
