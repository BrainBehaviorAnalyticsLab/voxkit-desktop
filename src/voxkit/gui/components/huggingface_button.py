"""
HuggingFace branded button component with logo
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QWidget


class HuggingFaceButton(QPushButton):
    """A button with HuggingFace branding and logo"""

    def __init__(self, title="HuggingFace", parent=None):
        super().__init__(parent)
        self.setText("")  # Clear default text
        self._setup_ui(title)

    def _setup_ui(self, title):
        """Set up the button UI with logo and text"""
        # Create layout for button content
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 6, 12, 6)
        layout.setSpacing(8)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Add HuggingFace emoji/icon
        icon_label = QLabel("🤗")
        icon_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                background: transparent;
            }
        """)
        layout.addWidget(icon_label)

        # Add text
        text_label = QLabel(title)
        text_label.setStyleSheet("""
            QLabel {
                font-size: 13px;
                font-weight: 600;
                color: inherit;
                background: transparent;
            }
        """)
        layout.addWidget(text_label)

        # Style the button with a modern, subtle design
        self.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #ffffff, stop:1 #f8f9fa);
                color: #2c3e50;
                border: 2px solid #e0e0e0;
                border-radius: 6px;
                padding: 6px 16px;
                font-weight: 600;
                min-height: 32px;
                min-width: 180px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #fff8e1, stop:1 #fff3d0);
                border: 2px solid #ffd54f;
                color: #2c3e50;
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #ffecb3, stop:1 #ffe082);
                border: 2px solid #ffb300;
            }
            QPushButton:disabled {
                background: #f5f5f5;
                color: #9e9e9e;
                border: 2px solid #e0e0e0;
            }
        """)

        self.setCursor(Qt.CursorShape.PointingHandCursor)



# Example usage
if __name__ == "__main__":
    import sys

    from PyQt6.QtWidgets import QApplication, QVBoxLayout, QWidget

    app = QApplication(sys.argv)

    # Create test window
    window = QWidget()
    layout = QVBoxLayout(window)

    # Regular button with text
    hf_button = HuggingFaceButton("Browse HuggingFace")
    hf_button.clicked.connect(lambda: print("HuggingFace button clicked!"))
    layout.addWidget(hf_button)

    # Another variant
    hf_button2 = HuggingFaceButton("Import from HuggingFace")
    hf_button2.clicked.connect(lambda: print("Import button clicked!"))
    layout.addWidget(hf_button2)

    window.setWindowTitle("HuggingFace Button Demo")
    window.resize(300, 200)
    window.show()

    sys.exit(app.exec())
