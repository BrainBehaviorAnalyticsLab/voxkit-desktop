from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QButtonGroup,
    QDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)

from voxkit.config import Defaults
from voxkit.engines import engines
from voxkit.gui.components import MultiColumnComboBox
from voxkit.gui.frameworks.settings_modal import GenericDialog
from voxkit.gui.workers.worker_thread import WorkerThread
from voxkit.storage import datasets, models


class PredictionStacker(QWidget):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.predict_dataset_dropdown = None
        self.selected_engine = Defaults["mode"]
        self.engine_dropdowns = {}  # Store dropdowns by engine ID
        self.engine_radios = {}  # Store radio buttons by engine ID
        self.init_ui()

    def on_mode_changed(self):
        """Handle engine selection change"""
        # Find which radio button is checked
        for engine_id, radio in self.engine_radios.items():
            if radio.isChecked():
                self.selected_engine = engine_id
                break

        # Show/hide appropriate dropdowns
        for engine_id, dropdown in self.engine_dropdowns.items():
            dropdown.setVisible(engine_id == self.selected_engine)

        print(f"Engine changed to: {self.selected_engine}")

    def reload_models(self):
        """Reload models in all engine dropdowns"""
        for engine_id, dropdown in self.engine_dropdowns.items():
            dropdown.clear()
            model_list = models.list_models(engine_id)

            if model_list:
                # Handle different model list formats
                data = []
                for m in model_list:
                    if isinstance(m, dict):
                        data.append(
                            {"id": m["id"], "data": (m["name"], m["download_date"], m["id"])}
                        )
                    else:
                        raise ValueError("Model list item is not a dict")
                dropdown.set_data(
                    data, ["Name", "Download Date", "ID"], placeholder="➁ Click to select a model"
                )
                dropdown.setEnabled(True)
            else:
                dropdown.set_data(
                    [{"id": None, "data": ("No models registered", "", "")}],
                    ["Name", "Download Date", "ID"],
                    placeholder="No models registered",
                )
                dropdown.setEnabled(False)

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

        # Dynamic engine selection group
        model_group = QGroupBox()
        model_layout = QVBoxLayout()
        model_layout.setSpacing(8)

        info_label = QLabel("① Choose an alignment method")
        info_label.setStyleSheet("font-size: 12px; color: #7f8c8d;")
        model_layout.addWidget(info_label)

        # Create button group for radio buttons
        self.mode_button_group = QButtonGroup(self)

        # Dynamically create engine options
        available_engines = engines.list_engines()

        for idx, engine_id in enumerate(available_engines):
            engine_obj = engines.get_engine(engine_id)
            engine_name = engine_obj.name()
            engine_description = engine_obj.description

            # Create engine layout
            engine_layout = QHBoxLayout()
            engine_layout.setSpacing(0)

            # Set right side spacing
            engine_layout.setContentsMargins(0, 0, 0, 0)

            # Radio button
            radio = QRadioButton(engine_name)
            radio.setChecked(idx == 0)  # Check first one by default
            radio.toggled.connect(self.on_mode_changed)

            self.engine_radios[engine_id] = radio
            self.mode_button_group.addButton(radio)

            # Radio container with fixed width
            radio_container = QHBoxLayout()
            radio_container.addWidget(radio)
            radio_container.addStretch()
            radio_container.setContentsMargins(0, 0, 0, 0)

            radio_widget = QWidget()
            radio_widget.setLayout(radio_container)
            radio_widget.setFixedWidth(160)
            radio_widget.setStyleSheet("background-color: white;")
            engine_layout.addWidget(radio_widget)

            # Add spacing to align dropdown with description box
            engine_layout.addSpacing(25)

            # Model dropdown
            dropdown = MultiColumnComboBox()
            dropdown.setStyleSheet("color: #95a5a6;")

            # Populate models
            model_list = models.list_models(engine_id)
            if model_list:
                data = []
                for m in model_list:
                    print(m)
                    if isinstance(m, dict):
                        data.append(
                            {"id": m["id"], "data": (m["name"], m["download_date"], m["id"])}
                        )
                    else:
                        raise ValueError("Model list item is not a dict")
                dropdown.set_data(
                    data, ["Name", "Download Date", "ID"], placeholder="➁ Click to select a model"
                )
                dropdown.setEnabled(True)
            else:
                dropdown.set_data(
                    [{"id": None, "data": ("No models registered", "", "")}],
                    ["Name", "Download Date", "ID"],
                    placeholder="No models registered",
                )
                dropdown.setEnabled(False)

            dropdown.setFixedWidth(300)

            self.engine_dropdowns[engine_id] = dropdown
            engine_layout.addWidget(dropdown)
            engine_layout.addStretch()

            model_layout.addLayout(engine_layout)

            # Description in a styled box
            if engine_description:
                desc_container = QWidget()
                desc_container.setStyleSheet("""
                    QWidget {
                        background-color: #f8f9fa;
                        border: 1px solid #e0e0e0;
                        border-radius: 4px;
                        padding: 8px;
                        margin-left: 25px;
                    }
                """)
                desc_layout = QHBoxLayout(desc_container)
                desc_layout.setContentsMargins(8, 6, 8, 6)

                info = QLabel(engine_description)
                info.setStyleSheet(
                    "color: #7f8c8d; font-size: 11px; background: transparent; border: none;"
                )
                info.setWordWrap(True)
                desc_layout.addWidget(info)

                model_layout.addWidget(desc_container)

            model_layout.addSpacing(5)

        # Set initial selected engine
        if available_engines:
            self.selected_engine = available_engines[0]

        model_group.setLayout(model_layout)
        layout.addWidget(model_group)
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
        
        # Set initial visibility of dropdowns based on selected engine
        self.on_mode_changed()
        
        return self

    def on_predict_settings(self):
        """Open settings dialog for selected engine"""
        engine = engines.get_engine(self.selected_engine)
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
        print(f"Engine: {self.selected_engine}")

        self.predict_status.setText("Processing...")
        self.predict_status.setStyleSheet("color: #f39c12; font-size: 12px; margin-top: 5px;")
        self.predict_btn.setEnabled(False)

        self.worker = WorkerThread(lambda: self.predict_alignments_logic(selected_dataset_id))
        self.worker.finished.connect(self.on_predict_finished)
        self.worker.start()

    def predict_alignments_logic(self, dataset_id: str) -> str:
        """Actual alignment prediction logic"""
        # Get the selected model from the current engine's dropdown
        selected_model_id = self.engine_dropdowns[self.selected_engine].current_id()

        print(f"Selected model ID: {selected_model_id}")

        # Get engine and call align method
        engine = engines.get_engine(self.selected_engine)
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
