"""Dataset Registration Worker Module.

Background worker for validating, registering, and analyzing datasets.

Signals
-------
- ``finished(bool, str)``: Emitted on completion with (success, message)
- ``progress(str)``: Emitted with status updates during registration
"""

import os

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
        success = datasets.validate_dataset(self.dataset_path)

        if not success:
            self.finished.emit(
                False,
                " Dataset validation failed. "
                "Please ensure the dataset follows the Kaldi organization pattern.",
            )
            return

        success, message = datasets.create_dataset(
            name=self.dataset_name,
            description=self.description,
            original_path=self.dataset_path,
            cached=self.cache,
            anonymize=self.anonymize,
            transcribed=self.transcribed,
        )

        print(f"Dataset creation result: {success}, message: {message}")

        if not success:
            self.finished.emit(False, message)
            return
        else:
            self.progress.emit("Dataset metadata created successfully.")

        # Determine output path for CSV file
        dataset_dir = os.path.join(datasets._get_datasets_root(), message["id"])

        csv_path = os.path.join(dataset_dir, f"{self.analysis_method.lower()}_summary.csv")

        csv_data = ManageAnalyzers.get_analyzers()[self.analysis_method].analyze(self.dataset_path)

        csv_success, csv_message = self._save_csv(csv_data, csv_path)

        if not csv_success:
            self.finished.emit(True, f"Warning: {csv_message}")
        else:
            self.finished.emit(True, csv_message)

    def _save_csv(self, data: list[dict], path: str) -> tuple[bool, str]:
        """
        Save the analysis data to a CSV file.

        Args:
            data: List of dictionaries where each dictionary represents a row.
            path: Output path for the CSV file.
        Returns:
            Tuple of (success, message) where success is True if the file was saved successfully.
        """
        import csv

        if not os.path.exists(os.path.dirname(path)):
            return False, "Expected directory does not exist: " + os.path.dirname(path)

        try:
            with open(path, "w", newline="", encoding="utf-8") as csvfile:
                if not data:
                    return False, "No data to write to CSV."

                fieldnames = data[0].keys()
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                for row in data:
                    writer.writerow(row)
            return True, f"CSV saved successfully to {path}."
        except Exception as e:
            return False, f"Failed to save CSV: {e}"
