from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Optional


class FieldType(Enum):
    """Enum for different field types of a form"""

    SPINBOX = "spinbox"
    DOUBLE_SPINBOX = "double_spinbox"
    CHECKBOX = "checkbox"
    LINEEDIT = "lineedit"
    COMBOBOX = "combobox"


@dataclass
class FieldConfig:
    """Configuration for a single form field"""

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
