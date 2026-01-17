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


# Legacy aliases for backward compatibility
BrowseButtonStyle = Buttons.BROWSE
CloseButtonStyle = Buttons.CLOSE
SpinBoxStyle = Inputs.SPINBOX_WITH_ARROWS
HeaderLabelStyle = Labels.HEADER_SIMPLE
CheckBoxStyle = Inputs.CHECKBOX
OkCancelButtonStyle = Containers.DIALOG_BUTTON_BOX
ContainerStyle = Containers.CONTAINER
LineEditStyle = Inputs.LINE_EDIT_SIMPLE
ComboBoxStyle = Inputs.COMBOBOX_SIMPLE


__all__ = [
    "Colors",
    "Buttons",
    "Inputs",
    "Labels",
    "Containers",
    # Legacy aliases
    "BrowseButtonStyle",
    "CloseButtonStyle",
    "SpinBoxStyle",
    "HeaderLabelStyle",
    "CheckBoxStyle",
    "OkCancelButtonStyle",
    "ContainerStyle",
    "LineEditStyle",
    "ComboBoxStyle",
]
