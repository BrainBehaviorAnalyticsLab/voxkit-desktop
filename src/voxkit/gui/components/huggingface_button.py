"""HuggingFace Button Module.

Branded button with HuggingFace logo for model hub integration.

API
---
- **HuggingFaceButton**: QPushButton with HuggingFace emoji and styling
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QWidget

from voxkit.gui.styles import Buttons, Labels


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
        icon_label.setStyleSheet(Labels.HEADER_SIMPLE)
        layout.addWidget(icon_label)

        # Add text
        text_label = QLabel(title)
        layout.addWidget(text_label)

        # Style the button with a modern, subtle design
        self.setStyleSheet(Buttons.HUGGINGFACE)

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
