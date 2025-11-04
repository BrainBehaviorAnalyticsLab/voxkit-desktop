import sys

from gui import AlignmentGUI
from PyQt6.QtWidgets import QApplication


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = AlignmentGUI()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
