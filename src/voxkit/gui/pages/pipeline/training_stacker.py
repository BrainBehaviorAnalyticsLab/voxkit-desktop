from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QFileDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
)

from voxkit.config import Defaults
from voxkit.engines import engines
from voxkit.gui.components import ModelSelectionPanel, MultiColumnComboBox
from voxkit.gui.frameworks.settings_modal import GenericDialog
from voxkit.gui.utils import validate_path, validate_paths
from voxkit.gui.workers.worker_thread import WorkerThread
from voxkit.storage import alignments, datasets, models
from voxkit.gui.styles import Buttons, Containers, Labels

from .base_stacker import BaseStacker

TrainingTools = engines.get_tool_providers("train")


class TrainingStacker(BaseStacker):
    def __init__(self, parent):
        self.train_dataset_dropdown = None
        self.train_alignment_dropdown = None
        self.train_textgrid_path = Defaults["textgrid_path"]
        self.train_model_name = "default_model"
        self.model_panel = None
        self.w2tg_train_settings = None
        self.train_btn = None
        super().__init__(parent)

    def get_title(self) -> str:
        """Return the stacker's title."""
        return "Ⓐ Train Aligners"
    
    def has_settings(self) -> bool:
        """This stacker has settings."""
        return True
    
    def on_settings(self):
        """Handle settings button click on training page."""
        self.settings_dialog = GenericDialog(
            parent=self,
            config=TrainingTools[self.model_panel.get_selected_engine()].get_settings_config(
                "train"
            ),
        )
        result = self.settings_dialog.exec()

        if result == QDialog.DialogCode.Accepted:
            try:
                self.settings_dialog.save()
            except Exception as e:
                print("Error syncing training settings:", e)
        # Clean up
        if self.parent:
            self.parent.setGraphicsEffect(None)

    def on_dataset_selected(self):
        """Handle dataset selection change and load corresponding alignments"""
        selected_dataset_id = self.train_dataset_dropdown.current_id()

        # Load alignments for the selected dataset
        alignments_meta = alignments.list_alignments(selected_dataset_id)

        if alignments_meta:
            data = []
            for a in alignments_meta:
                data.append(
                    {
                        "id": a["id"],
                        "data": (
                            a["engine_id"],
                            a["model_metadata"]["name"],
                            a["alignment_date"],
                            a["status"],
                        ),
                    }
                )
            self.train_alignment_dropdown.set_data(
                data,
                ["Method", "Model", "Date", "Status"],
                placeholder="Click to select an alignment",
            )
            self.train_alignment_dropdown.setEnabled(True)

        else:
            self.train_alignment_dropdown.set_data(
                [{"id": None, "data": ("No alignments registered", "", "")}],
                ["Method", "Model", "Date", "Status"],
                placeholder="No alignments registered",
            )
            self.train_alignment_dropdown.setEnabled(False)

    def browse_directory(self, line_edit):
        """Open directory browser and update the line edit"""
        directory = QFileDialog.getExistingDirectory(
            self,
            "Select Directory",
            line_edit.text() if Path(line_edit.text()).exists() else str(Path.home()),
        )
        if directory:
            line_edit.setText(directory)
            if not validate_path(self, directory):
                QMessageBox.warning(self, "Invalid Path", f"The path does not exist:\n{directory}")

    def on_train_model(self):
        """Handle Start Training button click"""
        # Get selected dataset
        index = self.train_dataset_dropdown.currentIndex()
        selected_dataset_id = self.train_dataset_dropdown.itemData(index)
        if not selected_dataset_id or selected_dataset_id == "Click to select a dataset":
            QMessageBox.warning(
                self, "No Dataset Selected", "Please select a dataset from the dropdown."
            )
            return

        # Get dataset path
        audio_path = datasets._get_dataset_root(selected_dataset_id)
        if not audio_path:
            QMessageBox.warning(
                self, "Invalid Dataset", f"Could not find path for dataset '{selected_dataset_id}'."
            )
            return

        # Get the alignments metadata
        align_index = self.train_alignment_dropdown.currentIndex()
        selected_alignment_id = self.train_alignment_dropdown.itemData(align_index)
        if not selected_alignment_id or selected_alignment_id == "Click to select an alignment":
            QMessageBox.warning(
                self, "No Alignment Selected", "Please select an alignment from the dropdown."
            )
            return

        alignment_meta = alignments.get_alignment_metadata(
            selected_dataset_id, selected_alignment_id
        )
        if not alignment_meta:
            QMessageBox.warning(
                self,
                "Invalid Alignment",
                f"Could not find metadata for alignment '{selected_alignment_id}'.",
            )
            return

        # Validate inputs
        paths = {
            "Training Audio Directory": audio_path,
            "Training TextGrid Directory": alignment_meta["tg_path"],
        }

        if not validate_paths(self, paths):
            return

        # Get current settings
        textgrid_path = alignment_meta["tg_path"]
        model_name = self.train_model_name.text()
        mode = self.model_panel.get_selected_engine()

        # Check that model name isn't used
        if not model_name:
            QMessageBox.warning(self, "Invalid Model Name", "Please enter a valid model name.")
            return

        print(f"Checking if model name '{model_name}' is already taken in {mode}...")
        names_taken = models.list_models(mode)
        names_taken = [m["name"] for m in names_taken]

        if model_name in names_taken:
            QMessageBox.warning(
                self,
                "Model Name Taken",
                f"The model name '{model_name}' is already in use. Please choose a different name.",
            )
            return

        print("Start Training clicked!")
        print(f"Model: {mode}")
        print(f"Training Audio Directory: {audio_path}")
        print(f"Training TextGrid Directory: {textgrid_path}")
        print(f"Model Name: {model_name}")

        # Update UI
        self.set_status("Training...", "working")
        self.train_btn.setEnabled(False)

        # Start worker thread
        self.worker = WorkerThread(
            lambda: self.train_model_logic(audio_path, textgrid_path, model_name, mode)
        )
        self.worker.finished.connect(self.on_train_finished)
        self.worker.start()

    def train_model_logic(self, audio_path, textgrid_path, model_name, model):
        """Actual model training logic"""
        print("Training logic would be implemented here.")

        selected_engine = self.model_panel.get_selected_engine()
        base_model_id = self.model_panel.get_selected_model_id()

        TrainingTools[selected_engine].train_aligner(
            audio_root=Path(audio_path),
            textgrid_root=Path(textgrid_path),
            base_model_id=base_model_id,
            new_model_id=model_name,
        )

        return "Model training completed successfully"

    def on_train_finished(self, success, message):
        """Handle completion of training operation.

        When training succeeds, this method refreshes the model lists in all
        relevant components (training page, prediction page, etc.) so the newly
        trained model is immediately available for selection.

        Args:
            success: Boolean indicating if training succeeded
            message: Status message to display to the user
        """
        self.train_btn.setEnabled(True)

        if success:
            self.set_status("✓ " + message, "success")

            # Refresh models in all relevant components
            self.reload_models()

            # Notify parent to refresh models in other stackers
            if hasattr(self.parent, "pipeline_container"):
                self.parent.pipeline_container.reload()

            QMessageBox.information(self, "Success", message)
        else:
            self.set_status("✗ Error occurred", "error")
            QMessageBox.critical(self, "Error", f"An error occurred:\n{message}")

    def reload_models(self):
        """Reload models in the dropdown"""
        if self.model_panel:
            self.model_panel.reload_models()

    def reload_datasets(self):
        """Reload datasets in the dropdown"""
        datasets_meta = datasets.list_datasets_metadata()
        if datasets_meta:
            data = []
            for d in datasets_meta:
                data.append({"id": d["id"], "data": (d["name"], d["description"], d["id"])})
            self.train_dataset_dropdown.set_data(
                data, ["Name", "Description", "ID"], placeholder="Click to select a dataset"
            )
            self.train_dataset_dropdown.setEnabled(True)
        else:
            self.train_dataset_dropdown.set_data(
                [{"id": None, "data": ("No datasets registered", "", "")}],
                ["Name", "Description", "ID"],
                placeholder="No datasets registered",
            )
            self.train_dataset_dropdown.setEnabled(False)

        self.train_alignment_dropdown.set_data(
            [{"id": None, "data": ("Select a dataset first", "", "")}],
            ["Method", "Model", "Date", "Status"],
            placeholder="Select a dataset first",
        )
        self.train_alignment_dropdown.setEnabled(False)

    def build_ui(self):
        """Build the training UI."""
        # Model Selection Panel
        engines_dict = {engine_id: engine for engine_id, engine in TrainingTools.items()}

        self.model_panel = ModelSelectionPanel(engines_dict)
        self.content_layout.addWidget(self.model_panel)

        # Dataset selection dropdown
        dataset_label = QLabel("③ Choose a Training Dataset")
        dataset_label.setStyleSheet(Labels.SECTION_LABEL)
        self.content_layout.addWidget(dataset_label)

        self.train_dataset_dropdown = MultiColumnComboBox()
        self.train_dataset_dropdown.setStyleSheet(Containers.COMBOBOX_STANDARD)

        # Populate with registered datasets
        datasets_meta = datasets.list_datasets_metadata()
        if datasets_meta:
            data = []
            for d in datasets_meta:
                data.append(
                    {"id": d["id"], "data": (d["name"], d["registration_date"], d["description"])}
                )
            self.train_dataset_dropdown.set_data(
                data, ["Name", "Date", "Description"], placeholder="Click to select a dataset"
            )
            self.train_dataset_dropdown.setEnabled(True)
        else:
            self.train_dataset_dropdown.set_data(
                [{"id": None, "data": ("No datasets registered", "", "")}],
                ["Name", "Date", "Description"],
                placeholder="No datasets registered",
            )
            self.train_dataset_dropdown.setEnabled(False)

        # Connect to selection handler
        self.train_dataset_dropdown.currentIndexChanged.connect(self.on_dataset_selected)

        self.content_layout.addWidget(self.train_dataset_dropdown)

        # Alignment selection dropdown (initially disabled)
        alignment_label = QLabel("④ Choose an Alignment")
        alignment_label.setStyleSheet(Labels.SECTION_LABEL)
        self.content_layout.addWidget(alignment_label)

        self.train_alignment_dropdown = MultiColumnComboBox()
        self.train_alignment_dropdown.setStyleSheet(Containers.COMBOBOX_STANDARD)

        self.train_alignment_dropdown.set_data(
            [{"id": None, "data": ("Select a dataset first", "", "")}],
            ["Method", "Model", "Date", "Status"],
            placeholder="Select a dataset first",
        )
        self.train_alignment_dropdown.setEnabled(False)
        self.content_layout.addWidget(self.train_alignment_dropdown)

        # Model Name
        model_name_label = QLabel("⑤ Name Your Model")
        model_name_label.setStyleSheet(Labels.SECTION_LABEL)
        self.content_layout.addWidget(model_name_label)

        self.train_model_name = QLineEdit("my_custom_model")
        self.content_layout.addWidget(self.train_model_name)

        self.content_layout.addSpacing(10)

        # Train Button
        self.train_btn = QPushButton("⑥ Start Training")
        self.train_btn.setMinimumHeight(45)
        self.train_btn.setStyleSheet(Buttons.PRIMARY)
        self.train_btn.clicked.connect(self.on_train_model)
        self.content_layout.addWidget(self.train_btn)
