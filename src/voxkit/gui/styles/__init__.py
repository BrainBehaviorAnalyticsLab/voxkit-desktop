"""
Centralized style definitions for VoxKit GUI components.

This module provides a unified styling system organized by component type,
eliminating duplicate styles across the application.
"""


class Colors:
    """Global color palette for consistent theming"""

    # Primary colors
    PRIMARY = "#3498db"
    PRIMARY_HOVER = "#2980b9"
    PRIMARY_PRESSED = "#21618c"
    PRIMARY_DISABLED = "#aed6f1"

    # Text colors
    TEXT_PRIMARY = "#2c3e50"
    TEXT_SECONDARY = "#7f8c8d"
    TEXT_TERTIARY = "#95a5a6"

    # Status colors
    SUCCESS = "#27ae60"
    WARNING = "#f39c12"
    ERROR = "#e74c3c"
    INFO = "#3498db"

    # Neutral colors
    WHITE = "#ffffff"
    LIGHT_GRAY = "#f0f0f0"
    GRAY = "#d0d0d0"
    DARK_GRAY = "#e0e0e0"
    BORDER = "#e0e0e0"

    # Background colors
    BG_PRIMARY = "#ffffff"
    BG_SECONDARY = "#f8f9fa"
    BG_HOVER = "#f0f0f0"


class Buttons:
    """Button styles for various button types"""

    PRIMARY = f"""
        QPushButton {{
            background-color: {Colors.PRIMARY};
            color: white;
            border: none;
            border-radius: 6px;
            font-size: 12px;
            font-weight: bold;
            min-height: 30px;
        }}
        QPushButton:hover {{
            background-color: {Colors.PRIMARY_HOVER};
        }}
        QPushButton:pressed {{
            background-color: {Colors.PRIMARY_PRESSED};
        }}
        QPushButton:disabled {{
            background-color: {Colors.PRIMARY_DISABLED};
        }}
    """

    SECONDARY = f"""
        QPushButton {{
            background-color: {Colors.WHITE};
            color: {Colors.TEXT_SECONDARY};
            border: 1px solid {Colors.GRAY};
            border-radius: 4px;
            font-weight: bold;
            min-width: 80px;
            min-height: 20px;
            padding: 6px 12px;
        }}
        QPushButton:hover {{
            background-color: {Colors.GRAY};
        }}
    """

    BROWSE = """
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
    """

    BROWSE_ALTERNATE = """
        QPushButton {
            background-color: white;
            color: #555;
            border: 1px solid #d0d0d0;
            border-radius: 4px;
            padding: 6px 12px;
            font-size: 13px;
        }
        QPushButton:hover {
            background-color: #f0f0f0;
            border-color: #b0b0b0;
        }
        QPushButton:pressed {
            background-color: #e0e0e0;
        }
    """

    CLOSE = f"""
        QPushButton {{
            border: none;
            font-size: 16px;
            color: {Colors.TEXT_SECONDARY};
            border-radius: 15px;
        }}
        QPushButton:hover {{
            background-color: {Colors.LIGHT_GRAY};
            color: {Colors.ERROR};
        }}
    """

    ICON = f"""
        QPushButton {{
            border: 1px solid {Colors.GRAY};
            border-radius: 5px;
            font-size: 18px;
            color: {Colors.TEXT_SECONDARY};
        }}
        QPushButton:hover {{
            background-color: {Colors.LIGHT_GRAY};
            color: {Colors.PRIMARY};
        }}
        QPushButton:pressed {{
            background-color: {Colors.DARK_GRAY};
        }}
    """

    SUCCESS = f"""
        QPushButton {{
            background-color: {Colors.SUCCESS};
            color: white;
            border: none;
            border-radius: 5px;
            padding: 10px 20px;
            font-size: 14px;
            font-weight: bold;
            min-height: 35px;
        }}
        QPushButton:hover {{
            background-color: #229954;
        }}
        QPushButton:pressed {{
            background-color: #1e8449;
        }}
    """

    DANGER = f"""
        QPushButton {{
            background-color: {Colors.ERROR};
            color: white;
            border: none;
            border-radius: 5px;
            padding: 10px 20px;
            font-size: 14px;
            font-weight: bold;
            min-height: 35px;
        }}
        QPushButton:hover {{
            background-color: #c0392b;
        }}
        QPushButton:pressed {{
            background-color: #a93226;
        }}
    """

    INFO_ACTION = f"""
        QPushButton {{
            background-color: white;
            color: {Colors.TEXT_PRIMARY};
            border: 1px solid {Colors.GRAY};
            border-radius: 5px;
            padding: 10px 20px;
            font-size: 14px;
            font-weight: bold;
            min-height: 35px;
        }}
        QPushButton:hover {{
            background-color: {Colors.LIGHT_GRAY};
            border-color: {Colors.INFO};
            color: {Colors.INFO};
        }}
        QPushButton:pressed {{
            background-color: {Colors.DARK_GRAY};
        }}
    """

    INFO_LARGE = f"""
        QPushButton {{
            background-color: {Colors.INFO};
            color: white;
            border: none;
            border-radius: 5px;
            padding: 8px 16px;
            font-size: 13px;
            font-weight: bold;
        }}
        QPushButton:hover {{
            background-color: #2980b9;
        }}
        QPushButton:pressed {{
            background-color: #21618c;
        }}
    """

    SELECTION = f"""
        QPushButton {{
            background-color: white;
            color: {Colors.TEXT_SECONDARY};
            border: 1px solid {Colors.GRAY};
            border-radius: 5px;
            padding: 6px 12px;
            font-size: 13px;
        }}
        QPushButton:hover {{
            background-color: {Colors.LIGHT_GRAY};
            border-color: {Colors.PRIMARY};
            color: {Colors.PRIMARY};
        }}
    """

    TABLE_VIEW = f"""
        QPushButton {{
            background-color: {Colors.BG_SECONDARY};
            border: 1px solid {Colors.GRAY};
            border-radius: 6px;
            font-size: 12px;
            font-weight: bold;
            color: {Colors.TEXT_SECONDARY};
        }}
        QPushButton:hover {{
            background-color: {Colors.LIGHT_GRAY};
            color: {Colors.PRIMARY};
            border-color: {Colors.PRIMARY};
        }}
    """

    DELETE_SMALL = """
        QPushButton {
            background-color: #e74c3c;
            color: white;
            border: none;
            border-radius: 5px;
            padding: 5px 10px;
        }
        QPushButton:hover {
            background-color: #c0392b;
        }
        QPushButton:pressed {
            background-color: #a93226;
        }
    """

    SUCCESS_SMALL = f"""
        QPushButton {{
            background-color: {Colors.SUCCESS};
            border: 1px solid #d0d0d0;
            border-radius: 5px;
            padding: 5px 10px;
            color: white;
        }}
        QPushButton:hover {{
            background-color: #229954;
        }}
        QPushButton:pressed {{
            background-color: #1e8449;
        }}
    """

    TOGGLE = """
        QPushButton {
            background-color: #F5F7FA;
            border: 1px solid #E0E0E0;
            border-radius: 6px;
            text-align: left;
            padding: 10px 16px;
            font-size: 13px;
            font-weight: 600;
            color: #37474F;
        }
        QPushButton:hover {
            background-color: #ECEFF1;
            border-color: #BDBDBD;
        }
        QPushButton:checked {
            border-bottom-left-radius: 0;
            border-bottom-right-radius: 0;
            border-bottom: none;
        }
    """

    HUGGINGFACE = """
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
    """
    


class Inputs:
    """Input field styles"""

    LINE_EDIT = f"""
        QLineEdit {{
            padding: 6px;
            border: 2px solid {Colors.GRAY};
            border-radius: 4px;
            color: {Colors.TEXT_PRIMARY};
            background-color: white;
        }}
        QLineEdit:focus {{
            border-color: {Colors.PRIMARY};
        }}
        QLineEdit:disabled {{
            background-color: {Colors.LIGHT_GRAY};
            color: {Colors.TEXT_TERTIARY};
        }}
    """

    LINE_EDIT_SIMPLE = """
        QLineEdit {
            padding: 4px;
            border: 2px solid #d0d0d0;
            border-radius: 4px;
            color: #000000;
        }
    """

    SPINBOX = f"""
        QSpinBox {{
            padding: 4px;
            border: 2px solid {Colors.GRAY};
            border-radius: 4px;
            color: {Colors.TEXT_PRIMARY};
            selection-background-color: transparent;
            selection-color: {Colors.TEXT_PRIMARY};
        }}
        QSpinBox:focus {{
            border-color: {Colors.PRIMARY};
        }}
    """

    SPINBOX_WITH_ARROWS = """
        QSpinBox {
            padding: 4px;
            border: 2px solid #d0d0d0;
            border-radius: 4px;
            color: #000000;
            selection-background-color: transparent;
            selection-color: #000000;
        }
        QSpinBox::up-button, QSpinBox::down-button {
            width: 16px;
            height: 16px;
        }
        QSpinBox::up-arrow, QSpinBox::down-arrow {
            width: 10px;
            height: 10px;
        }
    """

    DOUBLE_SPINBOX = f"""
        QDoubleSpinBox {{
            padding: 4px;
            border: 2px solid {Colors.GRAY};
            border-radius: 4px;
            color: {Colors.TEXT_PRIMARY};
            selection-background-color: transparent;
            selection-color: {Colors.TEXT_PRIMARY};
        }}
        QDoubleSpinBox:focus {{
            border-color: {Colors.PRIMARY};
        }}
    """

    CHECKBOX = """
        QCheckBox {
            spacing: 8px;
            color: black;
        }
        QCheckBox::indicator {
            width: 18px;
            height: 18px;
        }
    """

    COMBOBOX = f"""
        QComboBox {{
            padding: 0px 8px;
            border: 2px solid {Colors.GRAY};
            border-radius: 4px;
            color: {Colors.TEXT_PRIMARY};
        }}
        QComboBox:focus {{
            border-color: {Colors.PRIMARY};
        }}
        QComboBox::drop-down {{
            border: none;
        }}
    """

    COMBOBOX_SIMPLE = """
        QComboBox {
            padding: 0px 8px;
            border: 2px solid #d0d0d0;
            border-radius: 4px;
            color: #000000;
        }
    """


class Labels:
    """Label styles"""

    TITLE = f"""
        QLabel {{
            font-size: 24px;
            font-weight: bold;
            color: {Colors.TEXT_PRIMARY};
        }}
    """

    HEADER = f"""
        QLabel {{
            font-size: 18px;
            font-weight: bold;
            color: {Colors.TEXT_PRIMARY};
        }}
    """

    HEADER_SIMPLE = """
        font-size: 18px; font-weight: bold; color: #2c3e50;
    """

    SECTION_HEADER = f"""
        QLabel {{
            font-weight: bold;
            color: {Colors.TEXT_PRIMARY};
        }}
    """

    INFO = f"""
        QLabel {{
            font-size: 12px;
            color: {Colors.TEXT_SECONDARY};
        }}
    """

    STATUS_READY = f"""
        QLabel {{
            color: {Colors.TEXT_SECONDARY};
            font-size: 12px;
            margin-top: 5px;
        }}
    """

    STATUS_WORKING = f"""
        QLabel {{
            color: {Colors.WARNING};
            font-size: 12px;
            margin-top: 5px;
        }}
    """

    STATUS_SUCCESS = f"""
        QLabel {{
            color: {Colors.SUCCESS};
            font-size: 12px;
            margin-top: 5px;
        }}
    """

    STATUS_ERROR = f"""
        QLabel {{
            color: {Colors.ERROR};
            font-size: 12px;
            margin-top: 5px;
        }}
    """

    CATEGORY = f"""
        QLabel {{
            font-size: 16px;
            font-weight: bold;
            color: {Colors.TEXT_PRIMARY};
            background-color: white;
            padding: 8px 16px;
            border: 1px solid {Colors.BORDER};
            border-radius: 5px;
        }}
    """

    DIALOG_TITLE = f"""
        QLabel {{
            font-size: 14px;
            font-weight: bold;
            color: {Colors.TEXT_PRIMARY};
            padding: 10px;
            background-color: {Colors.BG_SECONDARY};
            border-radius: 5px;
        }}
    """

    FIELD_KEY = f"""
        QLabel {{
            font-weight: bold;
            color: {Colors.TEXT_SECONDARY};
            min-width: 120px;
        }}
    """

    FIELD_VALUE = f"""
        QLabel {{
            color: {Colors.TEXT_PRIMARY};
            background-color: {Colors.BG_SECONDARY};
            padding: 8px;
            border-radius: 3px;
            border: 1px solid {Colors.BORDER};
        }}
    """

    SECTION_LABEL = """
        font-weight: bold; color: #2c3e50;
    """

    PAGE_TITLE = """
        font-size: 24px; font-weight: bold; color: #2c3e50;
    """

    STATS = """
        QLabel {
            color: #7f8c8d;
            font-size: 12px;
            font-style: italic;
            padding: 5px;
        }
    """

    CREDIT = """
        color: #999; font-size: 10px; padding: 5px;
    """

    INFO_SMALL = """
        font-size: 12px; color: #7f8c8d;
    """

    FILTER_LABEL = """
        color: #2c3e50; font-weight: 500;
    """

    CONTENT_SECTION = """
        QLabel {
            background-color: #FAFBFC;
            border: 1px solid #E0E0E0;
            border-top: none;
            padding: 16px;
            font-size: 13px;
            color: #546E7A;
            border-bottom-left-radius: 6px;
            border-bottom-right-radius: 6px;
        }
    """


class Containers:
    """Container and dialog styles"""

    CONTAINER = """
        #container {
            background-color: white;
            border-radius: 10px;
            border: 1px solid #e0e0e0;
        }
    """

    DIALOG_BUTTON_BOX = """
        QDialogButtonBox QPushButton {
            min-width: 80px;
            min-height: 30px;
            border-radius: 4px;
            font-weight: bold;
        }
    """

    GROUP_BOX = """
        QGroupBox {
            font-weight: bold;
            border: 2px solid #3498db;
            border-radius: 8px;
            margin-top: 12px;
            padding: 15px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 15px;
            padding: 0 5px;
            color: #2c3e50;
        }
    """

    SCROLL_AREA = f"""
        QScrollArea {{
            border: 1px solid {Colors.BORDER};
            border-radius: 5px;
            background-color: white;
        }}
    """

    TABLE_WIDGET = """
        QTableWidget {
            gridline-color: #ecf0f1;
            background-color: white;
            border: 1px solid #bdc3c7;
            border-radius: 4px;
        }
        QTableWidget::item {
            padding: 0px;
        }
        QTableWidget::item:hover {
            background-color: #e8f4f8;
        }
        QTableWidget::item:selected {
            background-color: #3498db;
            color: white;
        }
        QHeaderView::section {
            background-color: #34495e;
            color: white;
            padding: 8px;
            font-weight: bold;
            border: none;
        }
    """

    HELPER_TEXT = """
        QLabel {
            color: #3498db;
            font-size: 12px;
            font-weight: 500;
            padding: 5px;
            background-color: #ebf5fb;
            border-left: 3px solid #3498db;
            border-radius: 3px;
        }
    """

    EMPTY_STATE = """
        QLabel {
            font-size: 14px;
            color: #95a5a6;
            font-style: italic;
            padding: 40px;
            text-align: center;
        }
    """

    COMBOBOX_STANDARD = """
        QComboBox {
            padding: 0px 8px;
            border: 1px solid #bdc3c7;
            border-radius: 4px;
            background-color: white;
            min-height: 25px;
        }
        QComboBox:disabled {
            background-color: #f5f5f5;
            color: #999;
        }
    """

    COMBOBOX_FILTER = """
        QComboBox {
            background-color: #F5F5F5;
            border: 1px solid #BDBDBD;
            border-radius: 4px;
            padding: 6px 10px;
            font-size: 13px;
            min-height: 25px;
        }
        QComboBox:hover {
            border-color: #2196F3;
            background-color: white;
        }
        QComboBox:focus {
            border-color: #1565C0;
            background-color: white;
        }
        QComboBox::drop-down {
            border: none;
            width: 25px;
        }
        QComboBox::down-arrow {
            image: none;
            border-left: 4px solid transparent;
            border-right: 4px solid transparent;
            border-top: 5px solid #757575;
            margin-right: 6px;
        }
        QComboBox:hover::down-arrow {
            border-top-color: #2196F3;
        }
        QComboBox QAbstractItemView {
            background-color: white;
            border: 1px solid #BDBDBD;
            selection-background-color: #E3F2FD;
            selection-color: #1976D2;
            outline: none;
            padding: 4px;
        }
    """

    TRANSPARENT_CONTAINER = """
        background-color: transparent;
    """

    MARKDOWN_DISPLAY = """
        QTextBrowser#markdownDisplay {
            background-color: white;
            border: 1px solid #E0E0E0;
            border-radius: 6px;
            padding: 20px;
            font-size: 14px;
            line-height: 1.6;
        }
    """

__all__ = [
    "Colors",
    "Buttons",
    "Inputs",
    "Labels",
    "Containers",
]
