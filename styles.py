GlobalStyleSheet = """
    QMainWindow {
        background-color: #f5f5f5;
    }
    QWidget {
        background-color: #f5f5f5;
        font-family: 'Segoe UI', Arial, sans-serif;
        font-size: 13px;
    }
    QGroupBox {
        background-color: white;
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        margin-top: 10px;
        padding: 15px;
    }
    QLabel {
        color: #333;
        background-color: transparent;
    }
    QLineEdit {
        background-color: white;
        border: 1px solid #d0d0d0;
        border-radius: 5px;
        padding: 8px 12px;
        min-height: 20px;
        color: #333;
    }
    QLineEdit:focus {
        border: 2px solid #4a90e2;
    }
    QPushButton {
        background-color: white;
        border: 1px solid #d0d0d0;
        border-radius: 5px;
        padding: 8px 16px;
        min-width: 80px;
        min-height: 20px;
        color: #333;
    }
    QPushButton:hover {
        background-color: #f0f0f0;
        border-color: #b0b0b0;
    }
    QPushButton:pressed {
        background-color: #e0e0e0;
    }
    QRadioButton {
        background-color: white;
        color: #333;
        spacing: 8px;
    }
    QRadioButton::indicator {
        width: 18px;
        height: 18px;
        border-radius: 9px;
    }
    QRadioButton::indicator:unchecked {
        border: 2px solid #d0d0d0;
        background-color: white;
    }
    QRadioButton::indicator:checked {
        border: 2px solid #4a90e2;
        background-color: #4a90e2;
    }
    QRadioButton::indicator:hover {
        border-color: #4a90e2;
    }
    QListWidget {
        background-color: white;
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 5px;
        outline: none;
    }
    QListWidget::item {
        padding: 12px 15px;
        border-radius: 5px;
        color: #333;
    }
    QListWidget::item:selected {
        background-color: #4a90e2;
        color: white;
    }
    QListWidget::item:hover {
        background-color: #b0cef2;
    }
"""