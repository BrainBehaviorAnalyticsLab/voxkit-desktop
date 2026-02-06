"""Model Registration Worker Module.

Background worker for registering and copying model files to storage.

Signals
-------
- ``finished(bool, str)``: Emitted on completion with (success, message)
- ``progress(str)``: Emitted with status updates during registration
"""

from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal

from voxkit.storage import models


class ModelRegistrationWorker(QThread):
    """Worker thread for model registration.

    Creates model metadata and copies model files (zip, .model, or directory).

    Attributes:
        finished: Signal emitted on completion with (success, message).
        progress: Signal emitted with status updates.
    """

    finished = pyqtSignal(bool, str)
    progress = pyqtSignal(str)

    def __init__(
        self,
        model_path,
        model_name,
        engine_id,
    ):
        super().__init__()
        self.model_path = model_path
        self.model_name = model_name
        self.engine_id = engine_id

    def run(self):
        self.progress.emit("Validating model structure...")

        # First validate the model path exists
        if not Path(self.model_path).exists():
            self.finished.emit(
                False,
                f"Model path does not exist: {self.model_path}",
            )
            return

        self.progress.emit("Creating model metadata and copying files...")

        # Create model metadata and copy files
        success, message = models.create_model(
            engine_id=self.engine_id,
            model_name=self.model_name,
            source_path=self.model_path,
        )

        print(f"Model creation result: {success}, message: {message}")

        if not success:
            self.finished.emit(False, message)
        else:
            self.progress.emit("Model registered successfully.")
            self.finished.emit(True, f"Model '{self.model_name}' registered successfully!")
