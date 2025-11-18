"""
Generic settings modal framework for VoxKit engine tool configuration.

This module provides a reusable framework for creating settings dialogs that
manage configuration for VoxKit engine tools. The framework handles:

- Dynamic form field generation from declarative configurations
- Automatic persistence of settings to JSON files
- Type-safe field definitions with validation support
- Integration with VoxKit storage system

The primary components are:

- :class:`GenericDialog`: Modal dialog widget with automatic field generation
- :class:`SettingsConfig`: Configuration container for dialog specification
- :class:`FieldConfig`: Individual field configuration with type and validation
- :class:`FieldType`: Enum of supported field widget types

Example usage
-------------
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
