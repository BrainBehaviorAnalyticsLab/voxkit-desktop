from typing import Callable, Optional

from voxkit.gui.frameworks.modal.generic import FieldConfig, FieldType, GenericDialog


class ImportModelDialog(GenericDialog):
    """Modal dialog for importing models from HuggingFace"""

    def __init__(
        self,
        parent=None,
        on_import: Optional[Callable[[str, str], None]] = None,
        engine_id: str = 'W2TG'
    ):
        """
        Args:
            parent: Parent widget
            on_import: Callback function(engine, model_path) called on import
            engines: List of available engines/modes
        """
        self.on_import_callback = on_import or self._placeholder_import

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
            parent=parent,
            title=f"Import {engine_id}",
            dims=(450, 250),
            fields=fields,
            apply_blur=True
        )

    def accept(self):
        """Override accept to trigger import callback"""
        values = self.get_values()
        engine = values.get("engine", "")
        model_path = values.get("model_path", "").strip()

        # Basic validation
        if not model_path:
            # Could add a QMessageBox warning here
            return

        # Call the import callback
        self.on_import_callback(engine, model_path)
        super().accept()

    def _placeholder_import(self, engine: str, model_path: str):
        """Placeholder import logic"""
        print(f"Importing model: {model_path} with engine: {engine}")
        # TODO: Implement actual import logic here
        # This is where you would:
        # - Download the model from HuggingFace
        # - Initialize the engine
        # - Save to local storage
        # - Update application state


def main():
    # Example usage:
    def handle_import(engine: str, model_path: str):
        # Your actual import logic here
        print(f"Importing {model_path} using {engine}")
        # Download model, initialize, etc.

    dialog = ImportModelDialog(
        on_import=handle_import,
        engines=["Whisper", "Wav2Vec2", "Custom"]
    )

    if dialog.exec():
        print("Import completed!")