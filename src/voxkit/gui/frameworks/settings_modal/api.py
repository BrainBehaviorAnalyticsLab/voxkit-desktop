from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Optional


class FieldType(Enum):
    """
    Each field type corresponds to a specific Qt widget that will be
    instantiated when the settings dialog is created.

    Attributes:
        SPINBOX: Integer input field (QSpinBox)
        DOUBLE_SPINBOX: Floating-point input field (QDoubleSpinBox)
        CHECKBOX: Boolean toggle field (ToggleSwitch)
        LINEEDIT: Text input field (QLineEdit)
        COMBOBOX: Dropdown selection field (QComboBox)
    """

    SPINBOX = "spinbox"
    DOUBLE_SPINBOX = "double_spinbox"
    CHECKBOX = "checkbox"
    LINEEDIT = "lineedit"
    COMBOBOX = "combobox"

@dataclass
class FieldConfig:
    """
    Configuration for a single form field in a settings dialog.

    This dataclass defines all parameters needed to create and configure a
    form field widget. The field will be automatically instantiated based on
    the ``field_type`` and configured with the provided parameters.

    Attributes:
        name: Internal identifier used as dictionary key when saving/loading.
        label: Human-readable label displayed next to the field.
        field_type: Type of widget to create (from FieldType enum).
        default_value: Initial value for the field. Type depends on field_type.
        tooltip: Optional help text shown on hover.
        min_value: Minimum value for spinbox types (int or float).
        max_value: Maximum value for spinbox types (int or float).
        decimals: Number of decimal places for DOUBLE_SPINBOX (default: 2).
        options: List of choices for COMBOBOX type.
        placeholder: Hint text for LINEEDIT when empty.
        validator: Optional callable for custom validation (not yet implemented).

    Example:
        >>> field = FieldConfig(
        ...     name="epochs",
        ...     label="Training Epochs",
        ...     field_type=FieldType.SPINBOX,
        ...     default_value=100,
        ...     min_value=1,
        ...     max_value=1000,
        ...     tooltip="Number of training iterations"
        ... )
    """

    name: str  # Internal name/key
    label: str  # Display label
    field_type: FieldType
    default_value: Any = None
    tooltip: Optional[str] = None

    # SpinBox specific
    min_value: Optional[int] = None
    max_value: Optional[int] = None

    # DoubleSpinBox specific
    decimals: Optional[int] = 2

    # ComboBox specific
    options: Optional[list] = None

    # LineEdit specific
    placeholder: Optional[str] = None

    # Validation
    validator: Optional[Callable] = None

@dataclass
class SettingsConfig:
    """Configuration container for creating a settings dialog.

    This dataclass aggregates all parameters needed to instantiate a
    :class:`GenericDialog` with a complete settings form. It defines the
    dialog's appearance, behavior, and the form fields it contains.

    Attributes:
        title: Dialog window title displayed in the header.
        dimensions: Dialog size as (width, height) tuple in pixels.
        apply_blur: If True, applies blur effect to parent window when open.
        fields: List of FieldConfig objects defining the form fields.
        store_file: Filename for JSON persistence (saved in storage root).

    Example:
        >>> config = SettingsConfig(
        ...     title="Alignment Settings",
        ...     dimensions=(450, 350),
        ...     apply_blur=True,
        ...     store_file="mfa_align_settings.json",
        ...     fields=[
        ...         FieldConfig(name="beam", label="Beam Width",
        ...                     field_type=FieldType.SPINBOX, default_value=10)
        ...     ]
        ... )
    """

    title: str
    dimensions: tuple[int, int]  # (width, height)
    apply_blur: bool
    fields: list[FieldConfig]
    store_file: str