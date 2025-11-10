from typing import Callable, Optional

from voxkit.gui.frameworks.modal.generic import FieldConfig, FieldType, GenericDialog
from voxkit.services.hf import download_and_copy_huggingface_model
from voxkit.storage.paths import create_train_destination


class ImportModelDialog(GenericDialog):
    """Modal dialog for importing models from HuggingFace"""

    def __init__(
        self,
        parent=None,
        on_import: Optional[Callable[[str, str], None]] = None,
        engine_id: str = "W2TG",
    ):
        """
        Args:
            parent: Parent widget
            on_import: Callback function(engine, model_path) called on import
            engines: List of available engines/modes
        """
        self.on_import_callback = on_import or self._placeholder_import
        self.engine_id = 'MFA' if 'MFA' in engine_id else 'W2TG'
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

        super().__init__(
            parent=self.parent,
            title=f"Import {engine_id}",
            dims=(450, 250),
            fields=fields,
            apply_blur=True,
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
        parts = model_path.split('/') if model_path else []
        engine_key = parts[-1] if parts else (model_path or "NONE")
        print(f"Creating destination for engine: {self.engine_id}, key: {engine_key}")
        data_path, dest_model_path, train_path, eval_path = create_train_destination(engine_key, self.engine_id)
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
