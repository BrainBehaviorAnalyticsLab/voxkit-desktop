from typing import Any

from PyQt6.QtCore import QEasingCurve, QPropertyAnimation, Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QGraphicsBlurEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from .api import FieldConfig, FieldType
from .styles import (
    CheckBoxStyle,
    CloseButtonStyle,
    ComboBoxStyle,
    ContainerStyle,
    HeaderLabelStyle,
    LineEditStyle,
    OkCancelButtonStyle,
    SpinBoxStyle,
)


class GenericDialog(QDialog):
    """Base class for reusable modal dialogs with configurable fields"""

    def __init__(
        self,
        parent=None,
        title: str = "Settings",
        dims: tuple[int, int] = (400, 350),
        fields: list[FieldConfig] = None,
        apply_blur: bool = True,
    ):
        super().__init__(parent)

        self.field_configs = fields or []
        self.field_widgets = {}
        self._apply_blur = apply_blur

        # Setup overlay and blur if parent exists
        if parent and apply_blur:
            self._setup_overlay(parent)

        self._setup_ui(title, dims)
        self._create_fields()
        self.fade_in()

    def _setup_overlay(self, parent):
        """Setup overlay and blur effect"""
        try:
            from voxkit.gui.components.widgets import OverlayWidget

            main_window = parent.parent
            overlay = OverlayWidget(main_window)
            overlay.resize(main_window.size())
            overlay.show()

            # Apply blur effect
            blur_effect = QGraphicsBlurEffect()
            blur_effect.setBlurRadius(5)
            parent.parent.setGraphicsEffect(blur_effect)

            overlay.deleteLater()
        except (AttributeError, ImportError):
            # Gracefully handle if overlay utils aren't available
            pass

    def _setup_ui(self, title: str, dims: tuple[int, int]):
        """Setup the basic dialog UI structure"""
        self.setWindowTitle(title)
        self.setFixedSize(dims[0], dims[1])
        self.setModal(True)

        # Frameless window
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Container widget
        container = QWidget()
        container.setObjectName("container")
        container.setStyleSheet(ContainerStyle)

        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(20, 20, 20, 20)

        # Header
        container_layout.addLayout(self._create_header(title))
        container_layout.addSpacing(15)

        # Form layout (will be populated by _create_fields)
        self.form_layout = QFormLayout()
        self.form_layout.setSpacing(15)
        self.form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        container_layout.addLayout(self.form_layout)
        container_layout.addSpacing(20)

        # Buttons
        container_layout.addWidget(self._create_buttons())

        main_layout.addWidget(container)

        # Center dialog on parent
        if self.parent():
            try:
                main_window = self.parent().parent
                self.move(
                    main_window.x() + (main_window.width() - self.width()) // 2,
                    main_window.y() + (main_window.height() - self.height()) // 2,
                )
            except AttributeError:
                pass

    def _create_header(self, title: str) -> QHBoxLayout:
        """Create header with title and close button"""
        header_layout = QHBoxLayout()

        title_label = QLabel(title)
        title_label.setStyleSheet(HeaderLabelStyle)
        header_layout.addWidget(title_label)
        header_layout.addStretch()

        # Close button
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(30, 30)
        close_btn.setStyleSheet(CloseButtonStyle)
        close_btn.clicked.connect(self.reject)
        header_layout.addWidget(close_btn)

        return header_layout

    def _create_fields(self):
        """Create form fields based on field configurations"""
        for field_config in self.field_configs:
            widget = self._create_field_widget(field_config)
            self.field_widgets[field_config.name] = widget
            self.form_layout.addRow(field_config.label, widget)

    def _create_field_widget(self, config: FieldConfig) -> QWidget:
        """Create a widget based on field configuration"""
        if config.field_type == FieldType.SPINBOX:
            widget = self._create_spinbox(config)
        elif config.field_type == FieldType.DOUBLE_SPINBOX:
            widget = self._create_double_spinbox(config)
        elif config.field_type == FieldType.CHECKBOX:
            widget = self._create_checkbox(config)
        elif config.field_type == FieldType.LINEEDIT:
            widget = self._create_lineedit(config)
        elif config.field_type == FieldType.COMBOBOX:
            widget = self._create_combobox(config)
        else:
            raise ValueError(f"Unsupported field type: {config.field_type}")

        if config.tooltip:
            widget.setToolTip(config.tooltip)

        return widget

    def _create_spinbox(self, config: FieldConfig) -> QSpinBox:
        """Create a spinbox widget"""
        spinbox = QSpinBox()
        if config.min_value is not None:
            spinbox.setMinimum(config.min_value)
        if config.max_value is not None:
            spinbox.setMaximum(config.max_value)
        if config.default_value is not None:
            spinbox.setValue(config.default_value)

        spinbox.setStyleSheet(SpinBoxStyle)
        return spinbox

    def _create_double_spinbox(self, config: FieldConfig) -> QDoubleSpinBox:
        """Create a double spinbox widget"""
        spinbox = QDoubleSpinBox()
        if config.min_value is not None:
            spinbox.setMinimum(config.min_value)
        if config.max_value is not None:
            spinbox.setMaximum(config.max_value)
        if config.decimals is not None:
            spinbox.setDecimals(config.decimals)
        if config.default_value is not None:
            spinbox.setValue(config.default_value)

        spinbox.setStyleSheet(SpinBoxStyle)
        return spinbox

    def _create_checkbox(self, config: FieldConfig) -> QCheckBox:
        """Create a checkbox widget"""
        checkbox = QCheckBox()
        if config.default_value is not None:
            checkbox.setChecked(config.default_value)

        checkbox.setStyleSheet(CheckBoxStyle)
        return checkbox

    def _create_lineedit(self, config: FieldConfig) -> QLineEdit:
        """Create a line edit widget"""
        lineedit = QLineEdit()
        if config.default_value is not None:
            lineedit.setText(str(config.default_value))
        if config.placeholder:
            lineedit.setPlaceholderText(config.placeholder)

        lineedit.setStyleSheet(LineEditStyle)
        return lineedit

    def _create_combobox(self, config: FieldConfig) -> QComboBox:
        """Create a combobox widget"""
        combobox = QComboBox()
        if config.options:
            combobox.addItems(config.options)
        if config.default_value is not None:
            index = combobox.findText(str(config.default_value))
            if index >= 0:
                combobox.setCurrentIndex(index)

        combobox.setStyleSheet(ComboBoxStyle)
        return combobox

    def _create_buttons(self) -> QDialogButtonBox:
        """Create OK/Cancel buttons"""
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.setStyleSheet(OkCancelButtonStyle)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        return button_box

    def fade_in(self):
        """Animate dialog fade-in"""
        self.setWindowOpacity(0)
        self.animation = QPropertyAnimation(self, b"windowOpacity")
        self.animation.setDuration(200)
        self.animation.setStartValue(0)
        self.animation.setEndValue(1)
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.animation.start()

    def get_values(self) -> dict[str, Any]:
        """Get all field values as a dictionary"""
        values = {}
        for name, widget in self.field_widgets.items():
            if isinstance(widget, QSpinBox) or isinstance(widget, QDoubleSpinBox):
                values[name] = widget.value()
            elif isinstance(widget, QCheckBox):
                values[name] = widget.isChecked()
            elif isinstance(widget, QLineEdit):
                values[name] = widget.text()
            elif isinstance(widget, QComboBox):
                values[name] = widget.currentText()
        return values

    def set_values(self, values: dict[str, Any]):
        """Set field values from a dictionary"""
        for name, value in values.items():
            if name in self.field_widgets:
                widget = self.field_widgets[name]
                if isinstance(widget, QSpinBox) or isinstance(widget, QDoubleSpinBox):
                    widget.setValue(value)
                elif isinstance(widget, QCheckBox):
                    widget.setChecked(value)
                elif isinstance(widget, QLineEdit):
                    widget.setText(str(value))
                elif isinstance(widget, QComboBox):
                    index = widget.findText(str(value))
                    if index >= 0:
                        widget.setCurrentIndex(index)
