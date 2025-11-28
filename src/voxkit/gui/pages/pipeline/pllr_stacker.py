from pathlib import Path

from pypllrcomputer import compute_pllr
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from voxkit.config import Defaults
from voxkit.gui.frameworks.settings_modal import (
    FieldConfig,
    FieldType,
    GenericDialog,
    SettingsConfig,
)
from voxkit.gui.workers.worker_thread import WorkerThread
from voxkit.storage.datasets import get_dataset_path, list_datasets
from voxkit.storage.validation import validate_path, validate_paths

from .styles import BrowseButtonStyle

FIELDS: list[FieldConfig] = [
    FieldConfig(
        name="acoustic_model",
        label="Acoustic Model:",
        field_type=FieldType.LINEEDIT,
        default_value="pkadambi/w2v2_pronunciation_score_model",
        tooltip="HuggingFace model name or path to local model directory.",
    ),
    FieldConfig(
        name="phone_key",
        label="Phone Key:",
        field_type=FieldType.LINEEDIT,
        default_value="ha phones",
        tooltip="Key in the model's config for phone labels.",
    ),
    FieldConfig(
        name="recompute_probas",
        label="Recompute Probabilities:",
        field_type=FieldType.CHECKBOX,
        default_value=False,
        tooltip="Check to recompute framewise probabilities even if cached data exists.",
    ),
    FieldConfig(
        name="likelihood_dct",
        label="Likelihood Dict Path:",
        field_type=FieldType.LINEEDIT,
        default_value="./computed-likelihoods/likelihood_dict.pkl",
        tooltip="Path to save/load the computed likelihood dictionary.",
    ),
    FieldConfig(
        name="aggregation_function",
        label="Aggregation Function:",
        field_type=FieldType.COMBOBOX,
        default_value="aggregate_by_phoneme_occurrence",
        options=[
            "aggregate_by_phoneme_occurrence",
            "aggregate_by_phoneme_average",
            "aggregate_by_phoneme_median",
        ],
        tooltip="Method to aggregate framewise probabilities into phonewise scores.",
    ),
]


PLLR_SETTINGS_CONFIG: SettingsConfig = SettingsConfig(
    title="PLLR Extraction Settings",
    dimensions=(400, 400),
    apply_blur=True,
    fields=FIELDS,
    store_file="pllr_settings.json",
)   
class PLLRStacker(QWidget):
    def __init__(self, parent=None):
        super().__init__()
        self.parent = parent
        self.pllr_dataset_dropdown = None
        self.init_ui()

    def on_extract_settings(self):
        
        settings_dialog = GenericDialog(self, PLLR_SETTINGS_CONFIG)
         
        result = settings_dialog.exec()

        # Clean up
        self.parent.setGraphicsEffect(None)

        if result == QDialog.DialogCode.Accepted:
            settings_dialog.save()
    
    def reload_datasets(self):
        """Reload datasets in the dropdown"""
        self.pllr_dataset_dropdown.clear()
        datasets = list_datasets()
        if datasets:
            self.pllr_dataset_dropdown.addItems([d["name"] for d in datasets])
            self.pllr_dataset_dropdown.setEnabled(True)
        else:
            self.pllr_dataset_dropdown.addItem("No datasets registered")
            self.pllr_dataset_dropdown.setEnabled(False)

    def init_ui(self):
        """Create the extract PLLR scores page"""
        self.setMinimumWidth(600)
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(30, 30, 30, 30)

        # Header with title and settings button
        header_layout = QHBoxLayout()

        # Title
        title = QLabel("Extract PLLR Scores")
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
        settings_btn.clicked.connect(self.on_extract_settings)
        header_layout.addWidget(settings_btn)

        layout.addLayout(header_layout)

        layout.addSpacing(10)

        # TextGrid Path
        textgrid_label = QLabel("TextGrid Path")
        textgrid_label.setStyleSheet("font-weight: bold; color: #34495e;")
        layout.addWidget(textgrid_label)

        textgrid_layout = QHBoxLayout()
        textgrid_layout.setSpacing(8)
        self.textgrid_path = QLineEdit("/path/to/alignments")
        self.textgrid_path_browse = QPushButton("Browse")
        self.textgrid_path_browse.setFixedWidth(100)
        self.textgrid_path_browse.setStyleSheet(BrowseButtonStyle)
        self.textgrid_path_browse.clicked.connect(lambda: self.browse_directory(self.textgrid_path))
        textgrid_layout.addWidget(self.textgrid_path, stretch=1)
        textgrid_layout.addWidget(self.textgrid_path_browse)
        layout.addLayout(textgrid_layout)

        # Dataset selection dropdown
        dataset_label = QLabel("PLLR Dataset")
        dataset_label.setStyleSheet("font-weight: bold; color: #2c3e50;")
        layout.addWidget(dataset_label)
        
        self.pllr_dataset_dropdown = QComboBox()
        self.pllr_dataset_dropdown.setPlaceholderText("Select Dataset")
        self.pllr_dataset_dropdown.setStyleSheet("""
            QComboBox {
                padding: 8px;
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
            self.pllr_dataset_dropdown.addItems([d["name"] for d in datasets])
        else:
            self.pllr_dataset_dropdown.addItem("No datasets registered")
            self.pllr_dataset_dropdown.setEnabled(False)
        
        layout.addWidget(self.pllr_dataset_dropdown)

        # Output Path
        extract_output_label = QLabel("Output Path")
        extract_output_label.setStyleSheet("font-weight: bold; color: #34495e;")
        layout.addWidget(extract_output_label)

        extract_output_layout = QHBoxLayout()
        extract_output_layout.setSpacing(5)
        self.extract_output_path = QLineEdit(Defaults["output_path"])
        self.extract_browse = QPushButton("Browse")
        self.extract_browse.setFixedWidth(100)
        self.extract_browse.setStyleSheet(BrowseButtonStyle)
        self.extract_browse.clicked.connect(lambda: self.browse_directory(self.extract_output_path))
        extract_output_layout.addWidget(self.extract_output_path, stretch=1)
        extract_output_layout.addWidget(self.extract_browse)
        layout.addLayout(extract_output_layout)

        layout.addSpacing(15)

        # Extract PLLR Button
        self.extract_btn = QPushButton("Extract PLLR")
        self.extract_btn.setMinimumHeight(45)
        self.extract_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #229954;
            }
            QPushButton:pressed {
                background-color: #1e8449;
            }
            QPushButton:disabled {
                background-color: #a9dfbf;
            }
        """)
        self.extract_btn.clicked.connect(self.on_extract_pllr)
        layout.addWidget(self.extract_btn)

        # Status label
        self.extract_status = QLabel("Ready")
        self.extract_status.setStyleSheet("color: #7f8c8d; font-size: 12px; margin-top: 5px;")
        self.extract_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.extract_status)

        layout.addStretch()
        return self

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

    def on_extract_pllr(self):
        """Handle Extract PLLR button click"""
        # Get selected dataset
        selected_dataset = self.pllr_dataset_dropdown.currentText()
        if not selected_dataset or selected_dataset == "Select Dataset":
            QMessageBox.warning(
                self, "No Dataset Selected",
                "Please select a dataset from the dropdown."
            )
            return
        
        # Get dataset path
        wavlab_path = get_dataset_path(selected_dataset)
        if not wavlab_path:
            QMessageBox.warning(
                self, "Invalid Dataset",
                f"Could not find path for dataset '{selected_dataset}'."
            )
            return
        
        # Validate inputs
        paths = {
            "TextGrid Path": self.textgrid_path.text(),
            "Wav/lab Path": wavlab_path,
            "Output Path": self.extract_output_path.text(),
        }

        if not validate_paths(self, paths):
            return

        # Get current settings
        textgrid_path = self.textgrid_path.text()
        output_path = self.extract_output_path.text()

        print("Extract PLLR clicked!")
        print(f"TextGrid Path: {textgrid_path}")
        print(f"Wav/lab Path: {wavlab_path}")
        print(f"Output Path: {output_path}")

        # Update UI
        self.extract_status.setText("Processing...")
        self.extract_status.setStyleSheet("color: #f39c12; font-size: 12px; margin-top: 5px;")
        self.extract_btn.setEnabled(False)

        # Start worker thread
        self.worker = WorkerThread(
            lambda: self.extract_pllr_logic(textgrid_path, wavlab_path, output_path)
        )
        self.worker.finished.connect(self.on_extract_finished)
        self.worker.start()

    def extract_pllr_logic(self, textgrid_path, wavlab_path, output_path):
        """Actual PLLR extraction logic"""
        compute_pllr(
            tg_files_path=textgrid_path,
            wav_files_path=wavlab_path,
            phone_key="phones",
            phonewise_proba_df=str(Path(output_path) / "phonewise_proba.csv"),
            framewise_proba_df=str(Path(output_path) / "framewise_proba.csv"),
        )
        return "PLLR extracted successfully"

    def on_extract_finished(self, success, message):
        """Handle completion of extract PLLR operation"""
        self.extract_btn.setEnabled(True)

        if success:
            self.extract_status.setText("✓ " + message)
            self.extract_status.setStyleSheet("color: #27ae60; font-size: 12px; margin-top: 5px;")
            QMessageBox.information(self, "Success", message)
        else:
            self.extract_status.setText("✗ Error occurred")
            self.extract_status.setStyleSheet("color: #e74c3c; font-size: 12px; margin-top: 5px;")
            QMessageBox.critical(self, "Error", f"An error occurred:\n{message}")
