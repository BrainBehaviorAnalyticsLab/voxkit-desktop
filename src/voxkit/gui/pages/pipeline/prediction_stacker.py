from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QLabel,
    QMessageBox,
    QPushButton,
)
from voxkit.gui.components import ModelSelectionPanel, MultiColumnComboBox
from voxkit.gui.frameworks.settings_modal import GenericDialog
from voxkit.gui.workers.worker_thread import WorkerThread
from voxkit.storage import datasets
from voxkit.gui.styles import Buttons
from voxkit.gui.styles import Labels, Containers, Buttons
from .base_stacker import BaseStacker


class PredictionStacker(BaseStacker):
    def __init__(self, parent):
        from voxkit.engines import engines
        self.predict_dataset_dropdown = None
        self.model_panel = None
        self.predict_btn = None
        self.engines = engines
        super().__init__(parent)

    def get_title(self) -> str:
        """Return the stacker's title."""
        return "Ⓑ Predict Alignments"
    
    def has_settings(self) -> bool:
        """This stacker has settings."""
        return True
    
    def on_settings(self):
        """Open settings dialog for selected engine."""
        engine = self.engines.get_engine(self.model_panel.get_selected_engine())
        if engine:
            settings_dialog = GenericDialog(self, config=engine.get_settings_config("align"))
            settings_dialog.exec()

            if settings_dialog.result() == QDialog.DialogCode.Accepted:
                settings_dialog.save()

        if self.parent:
            self.parent.setGraphicsEffect(None)

    def reload_models(self):
        """Reload models in all engine dropdowns."""
        if self.model_panel:
            self.model_panel.reload_models()

    def reload_datasets(self):
        """Reload datasets in the dropdown."""
        self.predict_dataset_dropdown.clear()
        dataset_list = datasets.list_datasets_metadata()

        columns = ["Name", "Date", "Description"]

        if dataset_list:
            data = []
            for d in dataset_list:
                data.append(
                    {"id": d["id"], "data": (d["name"], d["registration_date"], d["description"])}
                )
            self.predict_dataset_dropdown.set_data(
                data, columns, placeholder="Click to select a dataset"
            )
            self.predict_dataset_dropdown.setEnabled(True)
        else:
            self.predict_dataset_dropdown.set_data(
                [{"id": None, "data": ("No datasets registered", "", "")}],
                columns,
                placeholder="No datasets registered",
            )
            self.predict_dataset_dropdown.setEnabled(False)

    def build_ui(self):
        """Create the predict alignments page."""
        # Model Selection Panel
        available_engines = self.engines.list_engines()
        engines_dict = {engine_id: self.engines.get_engine(engine_id) for engine_id in available_engines}

        self.model_panel = ModelSelectionPanel(engines_dict)
        self.content_layout.addWidget(self.model_panel)
        self.content_layout.addSpacing(10)

        # Dataset selection dropdown
        dataset_label = QLabel("③ Choose a Speech Dataset")
        dataset_label.setStyleSheet(Labels.SECTION_LABEL)
        self.content_layout.addWidget(dataset_label)

        self.predict_dataset_dropdown = MultiColumnComboBox()
        self.predict_dataset_dropdown.setStyleSheet(Containers.COMBOBOX_STANDARD)
        # Populate with registered datasets
        dataset_list = datasets.list_datasets_metadata()
        columns = ["Name", "Date", "Description"]
        if dataset_list:
            data = []
            for d in dataset_list:
                data.append(
                    {"id": d["id"], "data": (d["name"], d["registration_date"], d["description"])}
                )
            self.predict_dataset_dropdown.set_data(
                data, columns, placeholder="Click to select a dataset"
            )
            self.predict_dataset_dropdown.setEnabled(True)
        else:
            # Add dummy ID so itemData() is predictable
            self.predict_dataset_dropdown.set_data(
                [{"id": None, "data": ("No datasets registered", "", "")}],
                columns,
                placeholder="No datasets registered",
            )
            self.predict_dataset_dropdown.setEnabled(False)

        self.content_layout.addWidget(self.predict_dataset_dropdown)

        self.content_layout.addSpacing(10)

        # Predict Alignments Button
        self.predict_btn = QPushButton("④ Start Predicting")
        self.predict_btn.setMinimumHeight(45)
        self.predict_btn.setStyleSheet(Buttons.PRIMARY)
        self.predict_btn.clicked.connect(self.on_predict_alignments)
        self.content_layout.addWidget(self.predict_btn)

    def on_predict_alignments(self):
        """Handle Predict Alignments button click."""
        selected_dataset_id = self.predict_dataset_dropdown.current_id()

        if not selected_dataset_id:
            QMessageBox.warning(
                self, "No Dataset Selected", "Please select a dataset from the dropdown."
            )
            return

        print("Predict Alignments clicked!")
        print(f"Engine: {self.model_panel.get_selected_engine()}")

        self.set_status("Processing...", "working")
        self.predict_btn.setEnabled(False)

        self.worker = WorkerThread(lambda: self.predict_alignments_logic(selected_dataset_id))
        self.worker.finished.connect(self.on_predict_finished)
        self.worker.start()

    def predict_alignments_logic(self, dataset_id: str) -> str:
        """Actual alignment prediction logic"""
        # Get the selected model from the current engine's dropdown
        selected_model_id = self.model_panel.get_selected_model_id()
        selected_engine = self.model_panel.get_selected_engine()

        print(f"Selected engine: {selected_engine}")
        print(f"Selected model ID: {selected_model_id}")

        # Get engine and call align method
        engine = self.engines.get_engine(selected_engine)
        engine.align(
            dataset_id=dataset_id,
            model_id=selected_model_id,
        )

        return "Alignments predicted successfully"

    def on_predict_finished(self, success, message):
        """Handle completion of predict alignments operation."""
        self.predict_btn.setEnabled(True)

        if success:
            self.set_status("✓ " + message, "success")
            QMessageBox.information(self, "Success", message)
        else:
            self.set_status("✗ Error occurred", "error")
            QMessageBox.critical(self, "Error", f"An error occurred:\n{message}")
