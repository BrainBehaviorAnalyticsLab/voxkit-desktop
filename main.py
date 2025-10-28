import sys
from PyQt6.QtWidgets import (
    QApplication
)
from gui import AlignmentGUI


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    window = AlignmentGUI()
    window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()