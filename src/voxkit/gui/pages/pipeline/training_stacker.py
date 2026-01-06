from pathlib import Path

from PyQt6.QtCore import Qt

# Add these imports at the top of your file
from PyQt6.QtWidgets import (
    QButtonGroup,
    QDialog,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
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
from voxkit.gui.utils import validate_path, validate_paths
from voxkit.gui.workers.worker_thread import WorkerThread
from voxkit.storage import alignments, datasets, models

TrainingTools = engines.get_tool_providers("train")


class TrainingStacker(QWidget):
    def __init__(self, parent):
        super().__init__()
        self.train_dataset_dropdown = None
        self.train_alignment_dropdown = None
        self.train_textgrid_path = Defaults["textgrid_path"]
        self.train_model_name = "default_model"
        self.selected_engine = Defaults["mode"]
        self.w2tg_train_settings = None
        self.parent = parent
        self.init_ui()

    def on_mode_changed(self):
        """Handle engine selection change"""
        # Find which radio button is checked
        for engine_id, radio in self.engine_panel_radios.items():
            if radio.isChecked():
                self.selected_engine = engine_id
                break

        # Show/hide appropriate dropdowns
        for engine_id, dropdown in self.engine_panel_dropdowns.items():
            dropdown.setVisible(engine_id == self.selected_engine)

        print(f"Engine changed to: {self.selected_engine}")

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
        mode = self.selected_engine

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
        self.train_status.setText("Training...")
        self.train_status.setStyleSheet("color: #f39c12; font-size: 12px; margin-top: 5px;")
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

        selected_model_index = self.engine_panel_dropdowns[self.selected_engine].currentIndex()
        base_model_id = self.engine_panel_dropdowns[self.selected_engine].itemData(
            selected_model_index
        )

        TrainingTools[self.selected_engine].train_aligner(
            audio_root=Path(audio_path),
            textgrid_root=Path(textgrid_path),
            base_model_id=base_model_id,
            new_model_id=model_name,
        )

        return "Model training completed successfully"

    def on_train_finished(self, success, message):
        """Handle completion of training operation"""
        self.train_btn.setEnabled(True)

        if success:
            self.train_status.setText("✓ " + message)
            self.train_status.setStyleSheet("color: #27ae60; font-size: 12px; margin-top: 5px;")
            QMessageBox.information(self, "Success", message)
        else:
            self.train_status.setText("✗ Error occurred")
            self.train_status.setStyleSheet("color: #e74c3c; font-size: 12px; margin-top: 5px;")
            QMessageBox.critical(self, "Error", f"An error occurred:\n{message}")

    def on_training_settings(self):
        """Handle settings button click on training page"""

        self.settings_dialog = GenericDialog(
            parent=self, config=TrainingTools[self.selected_engine].get_settings_config("train")
        )
        result = self.settings_dialog.exec()

        if result == QDialog.DialogCode.Accepted:
            try:
                self.settings_dialog.save()
            except Exception as e:
                print("Error syncing training settings:", e)
        # Clean up
        self.parent.setGraphicsEffect(None)

    def reload_models(self):
        """Reload models in the dropdown"""
        for engine, combo in self.engine_panel_dropdowns.items():
            try:
                models_meta = models.list_models(engine)
                if models_meta:
                    data = []
                    for m in models_meta:
                        data.append(
                            {"id": m["id"], "data": (m["name"], m["download_date"], m["id"])}
                        )
                    combo.set_data(data, ["Name", "Download Date", "ID"])
                else:
                    combo.set_data(
                        [{"id": None, "data": ("No models registered", "", "")}],
                        ["Name", "Download Date", "ID"],
                    )
            except Exception as e:
                print("Error reloading models:", e)

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

    def init_ui(self):
        self.setMinimumWidth(600)
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(30, 30, 30, 30)

        # ───── Header ─────
        header = QHBoxLayout()
        title = QLabel("Ⓐ Train Aligners")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #2c3e50;")
        header.addWidget(title)
        header.addStretch()

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
        settings_btn.clicked.connect(self.on_training_settings)
        header.addWidget(settings_btn)

        layout.addLayout(header)
        layout.addSpacing(20)

        # ───── Engine selection panel ─────
        engine_group = QGroupBox()
        engine_vbox = QVBoxLayout()
        engine_vbox.setSpacing(8)

        info = QLabel("① Choose an alignment method")
        info.setStyleSheet("font-size: 12px; color: #7f8c8d;")
        engine_vbox.addWidget(info)

        # *** NEW: button group for exclusive selection ***
        self.mode_group = QButtonGroup(self)
        self.mode_group.setExclusive(True)

        # Maps
        self.engine_panel_radios = {}
        self.engine_panel_dropdowns = {}

        # ------------------------------------------------------------------
        #  LOOP – one block per engine
        # ------------------------------------------------------------------
        for idx, (engine_id, engine) in enumerate(TrainingTools.items()):
            # ---------- radio ----------
            print(engine.id)
            print("ABOVE________")
            radio = QRadioButton(f"{engine.name()}")
            radio.setToolTip(engine.description)
            radio.toggled.connect(self.on_mode_changed)
            self.engine_panel_radios[engine_id] = radio
            self.mode_group.addButton(radio)

            # default: first engine checked
            if idx == 0:
                radio.setChecked(True)
                self.selected_engine = engine_id

            # ---------- dropdown ----------
            combo = MultiColumnComboBox()
            combo.setStyleSheet("color: #95a5a6;")
            combo.setFixedWidth(300)

            models_meta = models.list_models(engine_id)

            if models_meta:
                data = []
                for m in models_meta:
                    data.append({"id": m["id"], "data": (m["name"], m["download_date"], m["id"])})
                combo.set_data(
                    data, ["Name", "Download Date", "ID"], placeholder="➁ Click to select a model"
                )
            else:
                combo.set_data(
                    [{"id": None, "data": ("No models registered", "", "")}],
                    ["Name", "Download Date", "ID"],
                    placeholder="No models registered",
                )

            self.engine_panel_dropdowns[engine_id] = combo

            # ---------- layout ----------
            hbox = QHBoxLayout()
            hbox.setSpacing(0)
            hbox.setContentsMargins(0, 0, 0, 0)

            # radio container (fixed width → perfect column)
            rc = QHBoxLayout()
            rc.addWidget(radio)
            rc.addStretch()
            rc.setContentsMargins(0, 0, 0, 0)

            rw = QWidget()
            rw.setLayout(rc)
            rw.setFixedWidth(160)
            rw.setStyleSheet("background-color: white;")
            hbox.addWidget(rw)

            # Add spacing to align dropdown with description box
            hbox.addSpacing(25)

            hbox.addWidget(combo)
            hbox.addStretch()

            engine_vbox.addLayout(hbox)

            # Description in a styled box
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

            desc = QLabel(engine.description or "No description")
            desc.setStyleSheet(
                "color: #7f8c8d; font-size: 11px; background: transparent; border: none;"
            )
            desc.setWordWrap(True)
            desc_layout.addWidget(desc)

            engine_vbox.addWidget(desc_container)
            engine_vbox.addSpacing(5)

        # *** IMPORTANT: attach the vertical layout only once ***
        engine_group.setLayout(engine_vbox)
        layout.addWidget(engine_group)

        # Dataset selection dropdown
        dataset_label = QLabel("③ Choose a Training Dataset")
        dataset_label.setStyleSheet("font-weight: bold; color: #2c3e50;")
        layout.addWidget(dataset_label)

        self.train_dataset_dropdown = MultiColumnComboBox()
        self.train_dataset_dropdown.setStyleSheet("""
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

        layout.addWidget(self.train_dataset_dropdown)

        # Alignment selection dropdown (initially disabled)
        alignment_label = QLabel("④ Choose an Alignment")
        alignment_label.setStyleSheet("font-weight: bold; color: #2c3e50;")
        layout.addWidget(alignment_label)

        self.train_alignment_dropdown = MultiColumnComboBox()
        self.train_alignment_dropdown.setStyleSheet("""
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

        self.train_alignment_dropdown.set_data(
            [{"id": None, "data": ("Select a dataset first", "", "")}],
            ["Method", "Model", "Date", "Status"],
            placeholder="Select a dataset first",
        )
        self.train_alignment_dropdown.setEnabled(False)
        layout.addWidget(self.train_alignment_dropdown)

        # # Training Text Grid Directory
        # textgrid_label = QLabel("Training TextGrid Corpus")
        # textgrid_label.setStyleSheet("font-weight: bold; color: #2c3e50;")
        # layout.addWidget(textgrid_label)

        # train_textgrid_layout = QHBoxLayout()
        # train_textgrid_layout.setSpacing(8)
        # self.train_textgrid_path = QLineEdit(Defaults["textgrid_path"])
        # self.train_textgrid_browse = QPushButton("Browse")
        # self.train_textgrid_browse.setFixedWidth(100)
        # self.train_textgrid_browse.setStyleSheet(BrowseButtonStyle)
        # self.train_textgrid_browse.clicked.connect(
        #     lambda: self.browse_directory(self.train_textgrid_path)
        # )
        # train_textgrid_layout.addWidget(self.train_textgrid_path, stretch=1)
        # train_textgrid_layout.addWidget(self.train_textgrid_browse)
        # layout.addLayout(train_textgrid_layout)

        # Model Name
        model_name_label = QLabel("⑤ Name Your Model")
        model_name_label.setStyleSheet("font-weight: bold; color: #2c3e50;")
        layout.addWidget(model_name_label)

        self.train_model_name = QLineEdit("my_custom_model")
        layout.addWidget(self.train_model_name)

        layout.addSpacing(10)

        # Train Button
        self.train_btn = QPushButton("⑥ Start Training")
        self.train_btn.setMinimumHeight(45)
        self.train_btn.setStyleSheet("""
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
        self.train_btn.clicked.connect(self.on_train_model)
        layout.addWidget(self.train_btn)

        # Status label
        self.train_status = QLabel("Ready")
        self.train_status.setStyleSheet("color: #7f8c8d; font-size: 12px; margin-top: 5px;")
        self.train_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.train_status)

        layout.addStretch()
        
        # Set initial visibility of dropdowns based on selected engine
        self.on_mode_changed()
        
        return self
