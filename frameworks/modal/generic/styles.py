CloseButtonStyle = """
    QPushButton {
        border: none;
        font-size: 16px;
        color: #7f8c8d;
        border-radius: 15px;
    }
    QPushButton:hover {
        background-color: #f0f0f0;
        color: #e74c3c;
    }
    """

SpinBoxStyle = """
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

HeaderLabelStyle = """
    font-size: 18px; font-weight: bold; color: #2c3e50;
    """

CheckBoxStyle = """
    QCheckBox {
        spacing: 8px;
        color: black;
    }
    QCheckBox::indicator {
        width: 18px;
        height: 18px;
    }
    """

OkCancelButtonStyle = """
    QDialogButtonBox QPushButton {
        min-width: 80px;
        min-height: 30px;
        border-radius: 4px;
        font-weight: bold;
    }
"""

ContainerStyle = """
    #container {
        background-color: white;
        border-radius: 10px;
        border: 1px solid #e0e0e0;
    }
    """

LineEditStyle = """
    QLineEdit {
        padding: 4px;
        border: 2px solid #d0d0d0;
        border-radius: 4px;
        color: #000000;
    }
    """

ComboBoxStyle = """
    QComboBox {
        padding: 4px;
        border: 2px solid #d0d0d0;
        border-radius: 4px;
        color: #000000;
    }
    """