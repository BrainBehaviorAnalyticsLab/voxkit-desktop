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
from voxkit.gui.pages.pipeline.model_eval import QComboBox
from voxkit.storage.validation import validate_path, validate_paths

from voxkit.config import Defaults
from voxkit.engines import ManageEngines
from voxkit.gui.frameworks.settings_modal import GenericDialog
from voxkit.gui.workers.worker_thread import WorkerThread
from voxkit.storage.datasets import get_dataset_path, list_datasets
from voxkit.storage.models import list_models

from .styles import BrowseButtonStyle

TrainingTools = ManageEngines.get_tool_providers("train")


class TrainingPage(QWidget):
    def __init__(self, parent):
        super().__init__()
        self.train_dataset_dropdown = None
        self.train_textgrid_path = Defaults["textgrid_path"]
        self.train_model_name = "default_model"
        self.selected_engine = Defaults["mode"]
        self.w2tg_train_settings = None
        self.parent = parent
        self.init_ui()

    def on_mode_changed(self):
        """Handle model selection change"""
        # Check which radio button is actually checked
        for engine_id, radio in self.engine_panel_radios.items():
            if radio.isChecked():
                self.selected_engine = engine_id
                break

        print(f"Model changed to: {self.selected_engine}")

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
        selected_dataset = self.train_dataset_dropdown.currentText()
        if not selected_dataset or selected_dataset == "Select Dataset":
            QMessageBox.warning(
                self, "No Dataset Selected", "Please select a dataset from the dropdown."
            )
            return

        # Get dataset path
        audio_path = get_dataset_path(selected_dataset)
        if not audio_path:
            QMessageBox.warning(
                self, "Invalid Dataset", f"Could not find path for dataset '{selected_dataset}'."
            )
            return

        # Validate inputs
        paths = {
            "Training Audio Directory": audio_path,
            "Training TextGrid Directory": self.train_textgrid_path.text(),
        }

        if not validate_paths(self, paths):
            return

        # Get current settings
        textgrid_path = self.train_textgrid_path.text()
        model_name = self.train_model_name.text()
        mode = self.selected_engine

        # Check that model name isn't used
        if not model_name:
            QMessageBox.warning(self, "Invalid Model Name", "Please enter a valid model name.")
            return
        print(f"Checking if model name '{model_name}' is already taken in {mode}...")
        names_taken = list_models(mode).keys()

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
        print(
            f"Audio Path: {audio_path}"
            f"\nTextGrid Path: {textgrid_path}"
            f"\nModel Name: {model_name}"
            f"\nModel: {model}"
        )

        TrainingTools[self.selected_engine].train_aligner(
            audio_root=Path(audio_path),
            textgrid_root=Path(textgrid_path),
            base_model_id=self.engine_panel_dropdowns[self.selected_engine].currentText(),
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
        """Reload models in the dropdowns"""
        print(list_models(self.selected_engine, add_date=True))
        model_names = list_models(self.selected_engine, add_date=True).keys()
        print(self.engine_panel_dropdowns.keys())
        self.engine_panel_dropdowns[self.selected_engine].clear()
        self.engine_panel_dropdowns[self.selected_engine].addItems(
            list(model_names) if model_names else []
        )

    def reload_datasets(self):
        """Reload datasets in the dropdown"""
        self.train_dataset_dropdown.clear()
        datasets = list_datasets()
        if datasets:
            self.train_dataset_dropdown.addItems([d["name"] for d in datasets])
            self.train_dataset_dropdown.setEnabled(True)
        else:
            self.train_dataset_dropdown.addItem("No datasets registered")
            self.train_dataset_dropdown.setEnabled(False)

    def init_ui(self):
        self.setMinimumWidth(600)
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(30, 30, 30, 30)

        # ───── Header ─────
        header = QHBoxLayout()
        title = QLabel("Ⓐ Train Aligner")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #2c3e50;")
        header.addWidget(title)
        header.addStretch()

        settings_btn = QPushButton("Settings")
        settings_btn.setFixedSize(65, 40)
        settings_btn.setStyleSheet(""" ... """)
        settings_btn.clicked.connect(self.on_training_settings)
        header.addWidget(settings_btn)

        layout.addLayout(header)
        layout.addSpacing(20)

        # ───── Engine selection panel ─────
        engine_group = QGroupBox()
        engine_vbox = QVBoxLayout()
        engine_vbox.setSpacing(8)

        info = QLabel("Select alignment method")
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
            radio = QRadioButton(f"{engine.name()} ({engine_id})")
            radio.setToolTip(engine.description)
            self.engine_panel_radios[engine_id] = radio
            self.mode_group.addButton(radio)

            # default: first engine checked
            if idx == 0:
                radio.setChecked(True)
                self.selected_engine = engine_id

            # ---------- dropdown ----------
            combo = QComboBox()
            combo.setToolTip(f"Select a base {engine.name()} model")
            combo.setPlaceholderText("Select BASE Model")
            combo.setStyleSheet("color: #95a5a6;")
            combo.setFixedWidth(300)

            models = list_models(engine_id, add_date=True).keys()
            combo.addItems(list(models))
            self.engine_panel_dropdowns[engine_id] = combo

            # ---------- layout ----------
            hbox = QHBoxLayout()
            hbox.setSpacing(12)

            # radio container (fixed width → perfect column)
            rc = QHBoxLayout()
            rc.addWidget(radio)
            rc.addStretch()
            rc.setContentsMargins(0, 0, 0, 0)

            rw = QWidget()
            rw.setLayout(rc)
            rw.setFixedWidth(280)
            rw.setStyleSheet("background-color: white;")
            hbox.addWidget(rw)

            hbox.addWidget(combo)
            hbox.addStretch()

            engine_vbox.addLayout(hbox)

            # tiny description
            desc = QLabel(engine.description or "No description")
            desc.setStyleSheet("color: #95a5a6; font-size: 11px; margin-left: 25px;")
            engine_vbox.addWidget(desc)
            engine_vbox.addSpacing(5)

        # *** IMPORTANT: attach the vertical layout only once ***
        engine_group.setLayout(engine_vbox)
        layout.addWidget(engine_group)

        # Dataset selection dropdown
        dataset_label = QLabel("Training Dataset")
        dataset_label.setStyleSheet("font-weight: bold; color: #2c3e50;")
        layout.addWidget(dataset_label)

        self.train_dataset_dropdown = QComboBox()
        self.train_dataset_dropdown.setPlaceholderText("Select Dataset")
        self.train_dataset_dropdown.setStyleSheet("""
            QComboBox {
                padding: 0px 8px;
                border: 1px solid #bdc3c7;
                border-radius: 4px;
                background-color: white;
                min-height: 25px;
            }
            QComboBox:hover {
                border: 1px solid #3498db;
            }
            QComboBox::drop-down {
                border: none;
                width: 30px;
            }
            QComboBox::down-arrow {
                image: url(down_arrow.png);
                width: 12px;
                height: 12px;
            }
        """)

        # Populate with registered datasets
        datasets = list_datasets()
        if datasets:
            self.train_dataset_dropdown.addItems([d["name"] for d in datasets])
        else:
            self.train_dataset_dropdown.addItem("No datasets registered")
            self.train_dataset_dropdown.setEnabled(False)

        layout.addWidget(self.train_dataset_dropdown)

        # Training Text Grid Directory
        textgrid_label = QLabel("Training TextGrid Corpus")
        textgrid_label.setStyleSheet("font-weight: bold; color: #2c3e50;")
        layout.addWidget(textgrid_label)

        train_textgrid_layout = QHBoxLayout()
        train_textgrid_layout.setSpacing(8)
        self.train_textgrid_path = QLineEdit(Defaults["textgrid_path"])
        self.train_textgrid_browse = QPushButton("Browse")
        self.train_textgrid_browse.setFixedWidth(100)
        self.train_textgrid_browse.setStyleSheet(BrowseButtonStyle)
        self.train_textgrid_browse.clicked.connect(
            lambda: self.browse_directory(self.train_textgrid_path)
        )
        train_textgrid_layout.addWidget(self.train_textgrid_path, stretch=1)
        train_textgrid_layout.addWidget(self.train_textgrid_browse)
        layout.addLayout(train_textgrid_layout)

        # Model Name
        model_name_label = QLabel("Model Name")
        model_name_label.setStyleSheet("font-weight: bold; color: #2c3e50;")
        layout.addWidget(model_name_label)

        self.train_model_name = QLineEdit("my_custom_model")
        layout.addWidget(self.train_model_name)

        layout.addSpacing(10)

        # Train Button
        self.train_btn = QPushButton("Start Training")
        self.train_btn.setMinimumHeight(45)
        self.train_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:pressed {
                background-color: #21618c;
            }
            QPushButton:disabled {
                background-color: #aed6f1;
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
        return self
