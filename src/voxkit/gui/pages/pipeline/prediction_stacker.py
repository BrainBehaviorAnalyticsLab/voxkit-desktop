from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from voxkit.engines import engines
from voxkit.gui.components import ModelSelectionPanel, MultiColumnComboBox
from voxkit.gui.frameworks.settings_modal import GenericDialog
from voxkit.gui.workers.worker_thread import WorkerThread
from voxkit.storage import datasets


class PredictionStacker(QWidget):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.predict_dataset_dropdown = None
        self.model_panel = None
        self.init_ui()

    def reload_models(self):
        """Reload models in all engine dropdowns"""
        if self.model_panel:
            self.model_panel.reload_models()

    def reload_datasets(self):
        """Reload datasets in the dropdown"""
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

    def init_ui(self):
        """Create the predict alignments page"""
        self.setMinimumWidth(600)
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(30, 30, 30, 30)

        # Header with title and settings button
        header_layout = QHBoxLayout()
        title = QLabel("Ⓑ Predict Alignments")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #2c3e50;")
        header_layout.addWidget(title)
        header_layout.addStretch()

        # Settings button
        settings_btn = QPushButton("⚙️")
        settings_btn.setFixedSize(65, 40)
        settings_btn.setStyleSheet("""
            QPushButton {
                background-color: white;
                border: 1px solid #d0d0d0;
                border-radius: 5px;
                font-size: 18px;
                color: #7f8c8d;
            }
            QPushButton:hover {
                background-color: #f0f0f0;
                color: #4a90e2;
            }
            QPushButton:pressed {
                background-color: #e0e0e0;
            }
        """)
        settings_btn.clicked.connect(self.on_predict_settings)
        header_layout.addWidget(settings_btn)
        layout.addLayout(header_layout)
        layout.addSpacing(20)

        # Model Selection Panel
        available_engines = engines.list_engines()
        engines_dict = {engine_id: engines.get_engine(engine_id) for engine_id in available_engines}

        self.model_panel = ModelSelectionPanel(engines_dict)
        layout.addWidget(self.model_panel)
        layout.addSpacing(10)

        # Dataset selection dropdown
        dataset_label = QLabel("③ Choose a Speech Dataset")
        dataset_label.setStyleSheet("font-weight: bold; color: #2c3e50;")
        layout.addWidget(dataset_label)

        self.predict_dataset_dropdown = MultiColumnComboBox()
        self.predict_dataset_dropdown.setStyleSheet("""
            QComboBox {
                padding: 0px 8px;
                border: 1px solid #bdc3c7;
                border-radius: 4px;
                background-color: white;
                min-height: 25px;
            }
            QComboBox:disabled {
                background-color: #f5f5f5;
                color: #999;
            }
        """)
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

        layout.addWidget(self.predict_dataset_dropdown)

        layout.addSpacing(10)

        # Predict Alignments Button
        self.predict_btn = QPushButton("④ Start Predicting")
        self.predict_btn.setMinimumHeight(45)
        self.predict_btn.setStyleSheet("""
            QPushButton {
                background-color: #4a90e2;
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #357abd;
            }
            QPushButton:pressed {
                background-color: #2d6ba3;
            }
            QPushButton:disabled {
                background-color: #b0c4de;
            }
        """)
        self.predict_btn.clicked.connect(self.on_predict_alignments)
        layout.addWidget(self.predict_btn)

        # Status label
        self.predict_status = QLabel("Ready")
        self.predict_status.setStyleSheet("color: #7f8c8d; font-size: 12px; margin-top: 5px;")
        self.predict_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.predict_status)

        layout.addStretch()

        return self

    def on_predict_settings(self):
        """Open settings dialog for selected engine"""
        engine = engines.get_engine(self.model_panel.get_selected_engine())
        if engine:
            settings_dialog = GenericDialog(self, config=engine.get_settings_config("align"))
            settings_dialog.exec()

            if settings_dialog.result() == QDialog.DialogCode.Accepted:
                settings_dialog.save()

        self.parent.setGraphicsEffect(None)

    def on_predict_alignments(self):
        """Handle Predict Alignments button click"""
        selected_dataset_id = self.predict_dataset_dropdown.current_id()

        if not selected_dataset_id:
            QMessageBox.warning(
                self, "No Dataset Selected", "Please select a dataset from the dropdown."
            )
            return

        print("Predict Alignments clicked!")
        print(f"Engine: {self.model_panel.get_selected_engine()}")

        self.predict_status.setText("Processing...")
        self.predict_status.setStyleSheet("color: #f39c12; font-size: 12px; margin-top: 5px;")
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
        engine = engines.get_engine(selected_engine)
        engine.align(
            dataset_id=dataset_id,
            model_id=selected_model_id,
        )

        return "Alignments predicted successfully"

    def on_predict_finished(self, success, message):
        """Handle completion of predict alignments operation"""
        self.predict_btn.setEnabled(True)

        if success:
            self.predict_status.setText("✓ " + message)
            self.predict_status.setStyleSheet("color: #27ae60; font-size: 12px; margin-top: 5px;")
            QMessageBox.information(self, "Success", message)
        else:
            self.predict_status.setText("✗ Error occurred")
            self.predict_status.setStyleSheet("color: #e74c3c; font-size: 12px; margin-top: 5px;")
            QMessageBox.critical(self, "Error", f"An error occurred:\n{message}")
