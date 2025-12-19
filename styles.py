GlobalStyleSheet = """
    QMainWindow {
        background-color: transparent;
    }
    QWidget {
        background-color: #f5f5f5;
        color: #333;
        font-size: 13px;
        border: none;
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
    QPushButton#primaryButton {
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
    QWidget#centralWidget {
        background-color: #f5f7fa;
    }

    """

ToolBarStyle = """
    QToolBar#globalToolbar {
        background: #2f3542;
        spacing: 6px;
        padding: 4px;
    }
    QToolBar#globalToolbar QToolButton {
        color: #eceff4;
        background: transparent;
        border: 1px solid transparent;
        padding: 6px 10px;
        border-radius: 6px;
        margin: 2px;
    }
    QToolBar#globalToolbar QToolButton:hover {
        background: #3b4252;
        border-color: #4c566a;
    }
    QToolBar#globalToolbar QToolButton:pressed {
        background: #2b6fa2;
    }
    QToolBar#globalToolbar QToolButton:disabled {
        color: #7f8c8d;
    }
    """
