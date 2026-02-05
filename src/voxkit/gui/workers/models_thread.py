"""Model Registration Worker Module.

Background worker for registering and copying model files to storage.

Signals
-------
- ``finished(bool, str)``: Emitted on completion with (success, message)
- ``progress(str)``: Emitted with status updates during registration
"""

import os

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
        if not os.path.exists(self.model_path):
            self.finished.emit(
                False,
                f"Model path does not exist: {self.model_path}",
            )
            return

        self.progress.emit("Creating model metadata...")

        # Create model metadata
        success, message = models.create_model(
            engine_id=self.engine_id,
            model_name=self.model_name,
        )

        print(f"Model creation result: {success}, message: {message}")

        if not success:
            self.finished.emit(False, message)
            return
        else:
            model_dest = message["model_path"]
            # Replace last part with entrypoint.zip if self.model_path is a zip file
            if self.model_path.endswith(".zip"):
                try:
                    model_dest = os.path.join(os.path.dirname(model_dest), "entrypoint.zip")
                    # Update metadata to point to the correct model path
                    message["model_path"] = model_dest
                    # Update metadata file
                    models.update_model_metadata(
                        engine_id=self.engine_id,
                        model_id=message["id"],
                        updates={"model_path": model_dest},
                    )
                    # Copy the zip file to the destination
                    os.makedirs(os.path.dirname(model_dest), exist_ok=True)
                    with open(self.model_path, "rb") as src_file:
                        with open(model_dest, "wb") as dest_file:
                            dest_file.write(src_file.read())
                except Exception as e:
                    self.finished.emit(
                        False,
                        f"Failed to copy model zip file: {e}",
                    )
                    return
            elif self.model_path.endswith(".model"):
                try:
                    # Assume model_dest exists and that it is a folder
                    # Recursively copy the model_path to the destination
                    import shutil

                    shutil.copytree(self.model_path, model_dest, dirs_exist_ok=True)
                except Exception as e:
                    self.finished.emit(
                        False,
                        f"Failed to copy model file: {e}",
                    )
                    return

            else:
                # Models where the model lives in a folder (W2TG)
                try:
                    # Recursively copy the model_path to the destination
                    import shutil

                    shutil.copytree(self.model_path, model_dest, dirs_exist_ok=True)
                except Exception as e:
                    self.finished.emit(
                        False,
                        f"Failed to copy model folder: {e}",
                    )
                    return

            self.progress.emit("Model metadata created successfully.")
            self.finished.emit(True, f"Model '{self.model_name}' registered successfully!")
