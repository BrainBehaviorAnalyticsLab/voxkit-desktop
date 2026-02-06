"""Import Model Dialog Module.

Modal dialog for importing alignment models from HuggingFace Hub.

API
---
- **ImportModelDialog**: GenericDialog subclass for HuggingFace model import
"""

from typing import Callable, Optional

from PyQt6.QtWidgets import QMessageBox

from voxkit.gui.frameworks.settings_modal import (
    FieldConfig,
    FieldType,
    GenericDialog,
    SettingsConfig,
)
from voxkit.storage import models
from voxkit.storage.models import download_and_copy_huggingface_model


class ImportModelDialog(GenericDialog):
    """Modal dialog for importing models from HuggingFace.

    Extends GenericDialog with fields for HuggingFace path and local path input.
    """

    def __init__(
        self,
        parent=None,
        on_import: Optional[Callable[[str, str], None]] = None,
        engine_id: str = "W2TGENGINE",
    ):
        """
        Args:
            parent: Parent widget
            on_import: Callback function(engine, model_path) called on import
            engines: List of available engines/modes
        """
        self.on_import_callback = on_import or self._placeholder_import
        self.engine_id = engine_id
        self.parent = parent

        # Define fields
        fields = [
            FieldConfig(
                name="model_path",
                label="HuggingFace Path:",
                field_type=FieldType.LINEEDIT,
                placeholder="e.g., pkadambi/Wav2TextGrid",
                tooltip="Enter the HuggingFace model path (username/model-name)",
            ),
            FieldConfig(
                name="local_model_path",
                label="Local Model Path:",
                field_type=FieldType.LINEEDIT,
                placeholder="e.g., /path/to/local/model",
                tooltip="Enter the local path to the model",
            ),
        ]

        config = SettingsConfig(
            title=f"Import {self.engine_id} Model",
            dimensions=(450, 250),
            apply_blur=True,
            fields=fields,
            store_file=f"{self.engine_id}/imported_models_dialog.json",
        )

        super().__init__(
            parent=self.parent,
            config=config,
        )

    def accept(self):
        """Override accept to trigger import callback"""
        values = self.get_values()
        model_path = values.get("model_path", "").strip()

        # Basic validation
        if not model_path:
            # Could add a QMessageBox warning here
            return

        # Call the import callback
        self.on_import_callback(model_path)
        super().accept()

    def _placeholder_import(self, model_path: str):
        parts = model_path.split("/") if model_path else []
        model_name = parts[-1] if parts else (model_path or "NONE")
        print(f"Creating destination for engine: {self.engine_id}, key: {model_name}")
        success, message = models.create_model(
            engine_id=self.engine_id,
            model_name=model_name,
        )
        if not success:
            QMessageBox.critical(self, "Import Failed", f"Failed to create model entry: {message}")
        else:
            dest_model_path = message["model_path"]
        result = download_and_copy_huggingface_model(model_path, destination=dest_model_path)

        if result is None:
            print("Failed to download model")
        else:
            print(f"Model imported successfully to: {result}")


def main():
    # Example usage:
    def handle_import(engine: str, model_path: str):
        # Your actual import logic here
        print(f"Importing {model_path} using {engine}")
        # Download model, initialize, etc.

    dialog = ImportModelDialog(on_import=handle_import, engines=["Whisper", "Wav2Vec2", "Custom"])

    if dialog.exec():
        print("Import completed!")
