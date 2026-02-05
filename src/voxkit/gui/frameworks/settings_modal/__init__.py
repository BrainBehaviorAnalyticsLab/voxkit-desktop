"""Settings Modal Framework.

Reusable framework for creating settings dialogs with declarative field configurations.

API
---
- **GenericDialog**: Modal dialog with automatic field generation and JSON persistence
- **SettingsConfig**: Configuration container for dialog title, dimensions, and fields
- **FieldConfig**: Individual field definition (name, label, type, defaults, validation)
- **FieldType**: Enum of supported widget types (SPINBOX, CHECKBOX, LINEEDIT, etc.)

Example
-------
Create a settings dialog for an engine tool::

    from voxkit.gui.frameworks.settings_modal import (
        GenericDialog, SettingsConfig, FieldConfig, FieldType
    )

    config = SettingsConfig(
        title="Training Settings",
        dimensions=(400, 300),
        apply_blur=True,
        store_file="my_engine_train_settings.json",
        fields=[
            FieldConfig(
                name="batch_size",
                label="Batch Size",
                field_type=FieldType.SPINBOX,
                default_value=32,
                min_value=1,
                max_value=512,
                tooltip="Number of samples per training batch"
            ),
            FieldConfig(
                name="learning_rate",
                label="Learning Rate",
                field_type=FieldType.DOUBLE_SPINBOX,
                default_value=0.001,
                decimals=4,
                tooltip="Optimizer learning rate"
            )
        ]
    )

    dialog = GenericDialog(parent=self, config=config)
    if dialog.exec() == QDialog.DialogCode.Accepted:
        dialog.save()  # Persist to JSON
    if dialog.exec() == QDialog.DialogCode.Rejected:
        print("Clean up actions")
"""

from .api import FieldConfig, FieldType, SettingsConfig
from .generic import GenericDialog

__all__ = [
    "GenericDialog",
    "FieldConfig",
    "FieldType",
    "SettingsConfig",
]
