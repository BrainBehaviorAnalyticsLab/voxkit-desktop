"""Dataset Registration Worker Module.

Background worker for validating, registering, and analyzing datasets.

Signals
-------
- ``finished(bool, str)``: Emitted on completion with (success, message)
- ``progress(str)``: Emitted with status updates during registration
"""

from PyQt6.QtCore import QThread, pyqtSignal

from voxkit.analyzers import ManageAnalyzers
from voxkit.storage import datasets


class DatasetRegistrationWorker(QThread):
    """Worker thread for dataset registration.

    Validates dataset structure, creates metadata, and generates analysis CSV.

    Attributes:
        finished: Signal emitted on completion with (success, message).
        progress: Signal emitted with status updates.
    """

    finished = pyqtSignal(bool, str)
    progress = pyqtSignal(str)

    def __init__(
        self,
        dataset_path,
        dataset_name,
        description,
        cache,
        anonymize,
        transcribed,
        analysis_method,
    ):
        super().__init__()
        self.dataset_path = dataset_path
        self.dataset_name = dataset_name
        self.description = description
        self.cache = cache
        self.anonymize = anonymize
        self.transcribed = transcribed
        self.analysis_method = analysis_method

    def run(self):
        self.progress.emit("Validating dataset structure...")

        # First validate the dataset
        valid, msg = datasets.validate_dataset(self.dataset_path)

        if not valid:
            self.finished.emit(
                False,
                f"Dataset validation failed: {msg}",
            )
            return

        self.progress.emit("Analyzing dataset...")

        # Run analysis
        analysis_data = ManageAnalyzers.get_analyzers()[self.analysis_method].analyze(
            self.dataset_path
        )

        self.progress.emit("Creating dataset metadata...")

        # Create dataset with analysis data
        success, message = datasets.create_dataset(
            name=self.dataset_name,
            description=self.description,
            original_path=self.dataset_path,
            cached=self.cache,
            anonymize=self.anonymize,
            transcribed=self.transcribed,
            analysis_data=analysis_data,
            analysis_method=self.analysis_method,
        )

        print(f"Dataset creation result: {success}, message: {message}")

        if not success:
            self.finished.emit(False, message)
        else:
            self.finished.emit(True, f"Dataset '{self.dataset_name}' registered successfully!")
