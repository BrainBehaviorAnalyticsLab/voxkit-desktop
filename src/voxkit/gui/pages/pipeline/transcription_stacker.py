"""Transcription Stacker Module.

Pipeline page for transcribing dataset audio files into label files.

API
---
- **TranscriptionStacker**: Audio transcription workflow UI
"""

from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QLabel,
    QMessageBox,
    QPushButton,
)

from voxkit.gui.components import MultiColumnComboBox
from voxkit.gui.frameworks.settings_modal import GenericDialog
from voxkit.gui.styles import Buttons, Containers, Labels
from voxkit.gui.workers.worker_thread import WorkerThread
from voxkit.storage import datasets

from .base_stacker import BaseStacker


class TranscriptionStacker(BaseStacker):
    """Audio transcription pipeline page.

    Allows users to transcribe .wav files in a dataset using a registered
    transcription engine, producing .lab files placed next to each audio file.
    """

    def __init__(self, parent):
        from voxkit.engines import engines

        self.engines = engines
        self.engine_dropdown = None
        self.dataset_dropdown = None
        self.transcribe_btn = None
        self._selected_engine_id = None
        super().__init__(parent)

    def get_title(self) -> str:
        return "Transcribe Audio"

    def has_settings(self) -> bool:
        return True

    def on_settings(self):
        """Open settings dialog for the selected transcription engine."""
        engine_id = self._get_selected_engine_id()
        if not engine_id:
            return

        engine = self.engines.get_engine(engine_id)
        if engine and engine.has_tool("transcribe"):
            settings_dialog = GenericDialog(self, config=engine.get_settings_config("transcribe"))
            settings_dialog.exec()

            if settings_dialog.result() == QDialog.DialogCode.Accepted:
                settings_dialog.save()

        if self.parent:
            self.parent.setGraphicsEffect(None)

    def reload_datasets(self):
        """Reload datasets in the dropdown."""
        self.dataset_dropdown.clear()
        dataset_list = datasets.list_datasets_metadata()
        columns = ["Name", "Date", "Transcribed"]

        if dataset_list:
            data = []
            for d in dataset_list:
                status = "Yes" if d.get("transcribed") else "No"
                data.append({"id": d["id"], "data": (d["name"], d["registration_date"], status)})
            self.dataset_dropdown.set_data(data, columns, placeholder="Click to select a dataset")
            self.dataset_dropdown.setEnabled(True)
        else:
            self.dataset_dropdown.set_data(
                [{"id": None, "data": ("No datasets registered", "", "")}],
                columns,
                placeholder="No datasets registered",
            )
            self.dataset_dropdown.setEnabled(False)

    def build_ui(self):
        """Create the transcription page."""
        # Engine selection
        engine_label = QLabel("① Choose a Transcription Engine")
        engine_label.setStyleSheet(Labels.SECTION_LABEL)
        self.content_layout.addWidget(engine_label)

        self.engine_dropdown = QComboBox()
        self.engine_dropdown.setStyleSheet(Containers.COMBOBOX_STANDARD)

        providers = self.engines.get_tool_providers("transcribe")
        if providers:
            for engine_id, engine in providers.items():
                self.engine_dropdown.addItem(engine.human_readable_name, engine_id)
        else:
            self.engine_dropdown.addItem("No transcription engines available")
            self.engine_dropdown.setEnabled(False)

        self.content_layout.addWidget(self.engine_dropdown)
        self.content_layout.addSpacing(10)

        # Dataset selection
        dataset_label = QLabel("② Choose a Speech Dataset")
        dataset_label.setStyleSheet(Labels.SECTION_LABEL)
        self.content_layout.addWidget(dataset_label)

        self.dataset_dropdown = MultiColumnComboBox()
        self.dataset_dropdown.setStyleSheet(Containers.COMBOBOX_STANDARD)

        dataset_list = datasets.list_datasets_metadata()
        columns = ["Name", "Date", "Transcribed"]

        if dataset_list:
            data = []
            for d in dataset_list:
                status = "Yes" if d.get("transcribed") else "No"
                data.append({"id": d["id"], "data": (d["name"], d["registration_date"], status)})
            self.dataset_dropdown.set_data(data, columns, placeholder="Click to select a dataset")
            self.dataset_dropdown.setEnabled(True)
        else:
            self.dataset_dropdown.set_data(
                [{"id": None, "data": ("No datasets registered", "", "")}],
                columns,
                placeholder="No datasets registered",
            )
            self.dataset_dropdown.setEnabled(False)

        self.content_layout.addWidget(self.dataset_dropdown)
        self.content_layout.addSpacing(10)

        # Transcribe button
        self.transcribe_btn = QPushButton("③ Start Transcription")
        self.transcribe_btn.setMinimumHeight(45)
        self.transcribe_btn.setStyleSheet(Buttons.PRIMARY)
        self.transcribe_btn.clicked.connect(self.on_transcribe)
        self.content_layout.addWidget(self.transcribe_btn)

    def _get_selected_engine_id(self) -> str | None:
        """Return the engine ID selected in the dropdown."""
        idx = self.engine_dropdown.currentIndex()
        if idx < 0:
            return None
        engine_id = self.engine_dropdown.itemData(idx)
        return engine_id if isinstance(engine_id, str) or engine_id is None else None

    def on_transcribe(self):
        """Handle Transcribe button click."""
        selected_dataset_id = self.dataset_dropdown.current_id()
        engine_id = self._get_selected_engine_id()

        if not engine_id:
            QMessageBox.warning(self, "No Engine Selected", "Please select a transcription engine.")
            return

        if not selected_dataset_id:
            QMessageBox.warning(
                self, "No Dataset Selected", "Please select a dataset from the dropdown."
            )
            return

        # Check if already transcribed
        dataset_meta = datasets.get_dataset_metadata(selected_dataset_id)
        if dataset_meta and dataset_meta.get("transcribed"):
            QMessageBox.information(
                self,
                "Already Transcribed",
                f"Dataset '{dataset_meta['name']}' is already marked as transcribed. "
                "Transcription will not run again.",
            )
            return

        self.set_status("Transcribing...", "working")
        self.transcribe_btn.setEnabled(False)

        self.worker = WorkerThread(lambda: self._transcribe_logic(selected_dataset_id, engine_id))
        self.worker.finished.connect(self.on_transcribe_finished)
        self.worker.start()

    def _transcribe_logic(self, dataset_id: str, engine_id: str) -> str:
        """Run transcription in a background thread."""
        engine = self.engines.get_engine(engine_id)
        engine.transcribe(dataset_id=dataset_id)

        # Mark dataset as transcribed
        datasets.update_dataset_metadata(
            dataset_id,
            {"transcribed": True, "description": None, "cached": None, "anonymize": None},
        )
        return "Transcription completed successfully"

    def on_transcribe_finished(self, success, message):
        """Handle completion of transcription operation."""
        self.transcribe_btn.setEnabled(True)

        if success:
            self.set_status("✓ " + message, "success")
            QMessageBox.information(self, "Success", message)
            self.reload_datasets()
        else:
            self.set_status("✗ Error occurred", "error")
            QMessageBox.critical(self, "Error", f"An error occurred:\n{message}")

            # Mark dataset as not transcribed on failure
            selected_dataset_id = self.dataset_dropdown.current_id()
            if selected_dataset_id:
                datasets.update_dataset_metadata(
                    selected_dataset_id,
                    {
                        "transcribed": False,
                        "description": None,
                        "cached": None,
                        "anonymize": None,
                    },
                )
