import json
import os
from pathlib import Path
from typing import Any, Union

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

from voxkit.gui.components import OverlayWidget, ToggleSwitch
from voxkit.storage.utils import get_storage_root

from .api import FieldConfig, FieldType, SettingsConfig
from voxkit.gui.styles import (
    Buttons,
    Containers,
    Labels,
    Inputs
)


class GenericDialog(QDialog):
    """
    Reusable modal dialog for engine tool settings with automatic field generation.

    This dialog automatically generates form fields based on a declarative
    configuration and handles persistence to JSON files in the VoxKit storage
    directory. It provides a consistent UI experience with animations, blur
    effects, and automatic value restoration.

    The dialog creates widgets dynamically based on the field configurations,
    loads any previously saved values from disk, and provides methods to
    retrieve and save the current form state.

    Args:
        parent: Parent widget, typically the main application window.
        config: SettingsConfig object defining the dialog structure and fields.

    Raises:
        ValueError: If store_file path is not within the storage root directory.

    Attributes:
        store_values_path: Path to JSON file for settings persistence.
        field_configs: List of FieldConfig objects from config.
        field_widgets: Dict mapping field names to their widget instances.

    Example:
        >>> config = SettingsConfig(
        ...     title="Training Settings",
        ...     dimensions=(400, 300),
        ...     apply_blur=True,
        ...     store_file="train_settings.json",
        ...     fields=[...]
        ... )
        >>> dialog = GenericDialog(parent=main_window, config=config)
        >>> if dialog.exec() == QDialog.DialogCode.Accepted:
        ...     values = dialog.get_values()
        ...     dialog.save()
    """

    def __init__(
        self,
        parent,
        config: SettingsConfig,
    ):
        super().__init__(parent)
        self.store_values_path = Path(get_storage_root() / Path(config.store_file))
        if not self.store_values_path:
            raise ValueError("File path must be within the storage root directory.")

        self.field_configs = config.fields or []
        self.field_widgets: dict[str, Any] = {}
        self._apply_blur = config.apply_blur

        # Setup overlay and blur if parent exists
        if parent and config.apply_blur:
            self._setup_overlay(parent)

        self._save_defaults()
        self._setup_ui(config.title, config.dimensions)
        self._create_fields()
        self._load_saved_values()
        self.fade_in()

    def _save_defaults(self):
        """
        Save default field values to JSON file if it doesn't exist.

        This ensures that the dialog has a starting point for form values
        even if no previous settings are saved. It writes default values from
        field configurations to the store_values_path.

        The method only writes if the file does not already exist, avoiding
        overwriting user-saved settings.
        """
        if os.path.exists(self.store_values_path):
            return

        defaults = {field.name: field.default_value for field in self.field_configs}
        if not os.path.exists(os.path.dirname(self.store_values_path)):
            os.makedirs(os.path.dirname(self.store_values_path))
        with open(self.store_values_path, "w") as f:
            json.dump(defaults, f, indent=4)
            print(f"Default settings saved to {self.store_values_path}")

    def _setup_overlay(self, parent) -> None:
        """
        Setup overlay widget and apply blur effect to parent window.

        Creates a semi-transparent overlay on the main window and applies a
        blur effect to create visual focus on the dialog. Gracefully handles
        missing overlay widget or parent window.

        Args:
            parent: Parent widget to apply blur effect to.
        """
        try:
            main_window = parent.parent
            if main_window is None:
                return

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

    def _load_saved_values(self):
        """
        Load previously saved field values from JSON file.

        Reads the JSON file specified by store_values_path and populates
        form fields with saved values. If the file doesn't exist or cannot
        be read, fields retain their default values.

        The method handles different widget types appropriately:
        - Checkboxes/ToggleSwitch: setChecked()
        - SpinBoxes: setValue()
        - LineEdit: setText()
        - ComboBox: setCurrentIndex() matching saved text
        """
        if not os.path.exists(self.store_values_path):
            print("Saved values json doesn't exist yet.")
            return
        try:
            with open(self.store_values_path, "r") as f:
                saved_values = json.load(f)
                for name, value in saved_values.items():
                    print(f"Loading saved value for {name}: {value}")
                    if name in self.field_widgets:
                        widget = self.field_widgets[name]
                        if isinstance(widget, (QCheckBox, ToggleSwitch)):
                            widget.setChecked(value)
                        elif isinstance(widget, (QSpinBox, QDoubleSpinBox)):
                            widget.setValue(value)
                        elif isinstance(widget, QLineEdit):
                            widget.setText(value)
                        elif isinstance(widget, QComboBox):
                            index = widget.findText(value)
                            if index != -1:
                                widget.setCurrentIndex(index)
        except (FileNotFoundError, json.JSONDecodeError):
            print("Error loading saved values.")

    def _setup_ui(self, title: str, dims: tuple[int, int]):
        """
        Setup the basic dialog UI structure and styling.

        Creates the frameless dialog window with rounded container, header,
        form layout, and button box. Centers the dialog on the parent window.

        Args:
            title: Dialog title for the header.
            dims: Dialog dimensions as (width, height) tuple.
        """
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
        container.setStyleSheet(Containers.CONTAINER)

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
        if self.parent is not None and hasattr(self.parent, "parent"):
            try:
                main_window = self.parent.parent
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
        title_label.setStyleSheet(Labels.HEADER_SIMPLE)
        header_layout.addWidget(title_label)
        header_layout.addStretch()

        # Close button
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(30, 30)
        close_btn.setStyleSheet(Buttons.CLOSE)
        close_btn.clicked.connect(self.reject)
        header_layout.addWidget(close_btn)

        return header_layout

    def _create_fields(self):
        """
        Create form fields based on field configurations.

        Iterates through field_configs and creates appropriate widgets for
        each field, adding them to the form layout with their labels.
        """
        for field_config in self.field_configs:
            widget = self._create_field_widget(field_config)
            self.field_widgets[field_config.name] = widget
            self.form_layout.addRow(field_config.label, widget)

    def _create_field_widget(self, config: FieldConfig) -> QWidget:
        """
        Create a widget based on field configuration.

        Factory method that instantiates the appropriate Qt widget based on
        the field type specified in the configuration. Applies styling and
        sets tooltip if provided.

        Args:
            config: Field configuration specifying widget type and parameters.

        Returns:
            Configured Qt widget instance ready for form insertion.

        Raises:
            ValueError: If field_type is not recognized.
        """
        widget: Union[QSpinBox, QDoubleSpinBox, QLineEdit, QComboBox]
        if config.field_type == FieldType.SPINBOX:
            widget = self._create_spinbox(config)
        elif config.field_type == FieldType.DOUBLE_SPINBOX:
            widget = self._create_double_spinbox(config)
        elif config.field_type == FieldType.CHECKBOX:
            widget = ToggleSwitch(checked=bool(config.default_value))
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
        """
        Create an integer spinbox widget.

        Args:
            config: Field configuration with min_value, max_value, default_value.

        Returns:
            Configured QSpinBox instance.
        """
        spinbox = QSpinBox()
        if config.min_value is not None:
            spinbox.setMinimum(config.min_value)
        if config.max_value is not None:
            spinbox.setMaximum(config.max_value)
        if config.default_value is not None:
            spinbox.setValue(config.default_value)

        spinbox.setStyleSheet(Inputs.SPINBOX_WITH_ARROWS)
        return spinbox

    def _create_double_spinbox(self, config: FieldConfig) -> QDoubleSpinBox:
        """
        Create a floating-point spinbox widget.

        Args:
            config: Field configuration with min_value, max_value, decimals,
                default_value.

        Returns:
            Configured QDoubleSpinBox instance.
        """
        spinbox = QDoubleSpinBox()
        if config.min_value is not None:
            spinbox.setMinimum(config.min_value)
        if config.max_value is not None:
            spinbox.setMaximum(config.max_value)
        if config.decimals is not None:
            spinbox.setDecimals(config.decimals)
        if config.default_value is not None:
            spinbox.setValue(config.default_value)

        spinbox.setStyleSheet(Inputs.SPINBOX_WITH_ARROWS)
        return spinbox

    def _create_checkbox(self, config: FieldConfig) -> QCheckBox:
        """
        Create a checkbox widget.

        Args:
            config: Field configuration with default_value (bool).

        Returns:
            Configured QCheckBox instance.
        """
        checkbox = QCheckBox()
        if config.default_value is not None:
            checkbox.setChecked(config.default_value)

        checkbox.setStyleSheet(Inputs.CHECKBOX)
        return checkbox

    def _create_lineedit(self, config: FieldConfig) -> QLineEdit:
        """
        Create a text input line edit widget.

        Args:
            config: Field configuration with default_value, placeholder.

        Returns:
            Configured QLineEdit instance.
        """
        lineedit = QLineEdit()
        if config.default_value is not None:
            lineedit.setText(str(config.default_value))
        if config.placeholder:
            lineedit.setPlaceholderText(config.placeholder)

        lineedit.setStyleSheet(Inputs.LINE_EDIT_SIMPLE)
        return lineedit

    def _create_combobox(self, config: FieldConfig) -> QComboBox:
        """
        Create a dropdown combobox widget.

        Args:
            config: Field configuration with options list, default_value.

        Returns:
            Configured QComboBox instance.
        """
        combobox = QComboBox()
        if config.options:
            combobox.addItems(config.options)
        if config.default_value is not None:
            index = combobox.findText(str(config.default_value))
            if index >= 0:
                combobox.setCurrentIndex(index)

        combobox.setStyleSheet(Inputs.COMBOBOX_SIMPLE)
        return combobox

    def _create_buttons(self) -> QDialogButtonBox:
        """Create OK/Cancel buttons"""
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.setStyleSheet(Containers.DIALOG_BUTTON_BOX)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        return button_box

    def fade_in(self):
        """
        Animate dialog fade-in effect.

        Creates a smooth opacity animation from 0 to 1 over 200ms using an
        easing curve. Called automatically during initialization.
        """
        self.setWindowOpacity(0)
        self.animation = QPropertyAnimation(self, b"windowOpacity")
        self.animation.setDuration(200)
        self.animation.setStartValue(0)
        self.animation.setEndValue(1)
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.animation.start()

    def get_values(self) -> dict[str, Any]:
        """
        Get all field values as a dictionary.

        Retrieves current values from all form widgets and returns them in
        a dictionary keyed by field names. Values are in their native Python
        types (int, float, bool, str).

        Returns:
            Dictionary mapping field names to their current values.

        Example:
            >>> values = dialog.get_values()
            >>> print(values)
            {'batch_size': 32, 'learning_rate': 0.001, 'use_gpu': True}
        """

        values: dict[str, Union[int, float, str]] = {}
        for name, widget in self.field_widgets.items():
            if isinstance(widget, QSpinBox) or isinstance(widget, QDoubleSpinBox):
                values[name] = widget.value()
            elif isinstance(widget, QCheckBox):
                values[name] = widget.isChecked()
            elif isinstance(widget, QLineEdit):
                values[name] = widget.text()
            elif isinstance(widget, QComboBox):
                values[name] = widget.currentText()
            elif isinstance(widget, ToggleSwitch):
                values[name] = widget.isChecked()

        return values

    def set_values(self, values: dict[str, Any]):
        """
        Set field values from a dictionary.

        Updates form widgets with values from the provided dictionary.
        Handles type conversion and widget-specific setter methods.

        Args:
            values: Dictionary mapping field names to their desired values.

        Example:
            >>> dialog.set_values({'batch_size': 64, 'use_gpu': False})
        """
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
                elif isinstance(widget, ToggleSwitch):
                    widget.setChecked(value)

    def save(self):
        """
        Save current field values to JSON file.

        Retrieves all field values and writes them to the JSON file specified
        by store_values_path. The file is created in the VoxKit storage root
        directory and will be loaded automatically when the dialog opens again.

        Example:
            >>> if dialog.exec() == QDialog.DialogCode.Accepted:
            ...     dialog.save()  # Persist settings to disk
        """
        values = self.get_values()
        if not os.path.exists(os.path.dirname(self.store_values_path)):
            os.makedirs(os.path.dirname(self.store_values_path))
        with open(self.store_values_path, "w") as f:
            json.dump(values, f, indent=4)
            print(f"Settings saved to {self.store_values_path}")
