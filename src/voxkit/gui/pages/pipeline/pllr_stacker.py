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
from voxkit.storage import alignments, datasets
from voxkit.storage.utils import get_storage_root
from voxkit.gui.utils import validate_path, validate_paths
from voxkit.gui.components import MultiColumnComboBox

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
        default_value="phones",
        tooltip="Key in the model's config for phone labels.",
    ),
    FieldConfig(
        name="recompute_probas",
        label="Recompute Probabilities:",
        field_type=FieldType.CHECKBOX,
        default_value=True,
        tooltip="Check to recompute framewise probabilities even if cached data exists.",
    ),
    FieldConfig(
        name="likelihood_dct",
        label="Likelihood Dict Path:",
        field_type=FieldType.LINEEDIT,
        default_value="",  # Will be set at runtime
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


def get_pllr_settings_config() -> SettingsConfig:
    """Get PLLR settings config with runtime-computed default paths."""
    # Find the likelihood_dct field and set its default value at runtime
    fields = FIELDS.copy()
    for field in fields:
        if field.name == "likelihood_dct" and not field.default_value:
            field.default_value = str(get_storage_root() / "computed-likelihoods" / "likelihood_dict.pkl")
    
    return SettingsConfig(
        title="PLLR Extraction Settings",
        dimensions=(400, 400),
        apply_blur=True,
        fields=fields,
        store_file="pllr_settings.json",
    )


class PLLRStacker(QWidget):
    def __init__(self, parent=None):
        super().__init__()
        self.parent = parent
        self.pllr_dataset_dropdown = None
        self.pllr_alignment_dropdown = None
        self.init_ui()

    def on_extract_settings(self):
        
        settings_dialog = GenericDialog(self, get_pllr_settings_config())
         
        result = settings_dialog.exec()

        # Clean up
        self.parent.setGraphicsEffect(None)

        if result == QDialog.DialogCode.Accepted:
            settings_dialog.save()
    
    def on_dataset_selected(self):
        """Handle dataset selection change and load corresponding alignments"""
        selected_index = self.pllr_dataset_dropdown.currentIndex()
        selected_dataset_id = self.pllr_dataset_dropdown.itemData(selected_index)
        
        # Clear alignment dropdown
        self.pllr_alignment_dropdown.clear()
        
        if selected_dataset_id and selected_dataset_id != "No datasets registered":
            # Load alignments for this dataset
            alignments_list = alignments.list_alignments(selected_dataset_id)
            
            if alignments_list:
                rows = []
                for alignment in alignments_list:
                    # Display format: "EngineID - ModelName (Date)"
                    rows.append({"id": alignment["id"], "data": (alignment["engine_id"], alignment["model_metadata"]["name"], alignment["alignment_date"], alignment["status"])})

                self.pllr_alignment_dropdown.set_data(rows, ["Engine ID", "Model Name", "Date Registered", "Status"], placeholder="Click to select an alignment")
                    
                self.pllr_alignment_dropdown.setEnabled(True)
            else:
                self.pllr_alignment_dropdown.set_data([{"id": None, "data": ("No alignments registered", "", "")}], ["Method", "Model", "Date", "Status"], placeholder="No alignments registered")
                self.pllr_alignment_dropdown.setEnabled(False)
        else:
            self.pllr_alignment_dropdown.set_data([], [])
            self.pllr_alignment_dropdown.setEnabled(False)
    
    def reload_datasets(self):
        """Reload datasets in the dropdown"""
        self.pllr_dataset_dropdown.clear()
        datasets_meta = datasets.list_datasets_metadata()
        data = []
        headers = ["Name", "Date", "Description"]
        if datasets_meta:
            for d in datasets_meta:

                name = d["name"]
                date_registered = d["registration_date"]
                id = d["id"]
                description = d["description"]
                data.append({"id": id, "data": (name,date_registered,description)})
            self.pllr_dataset_dropdown.set_data(data, headers, placeholder="Select a dataset")
            self.pllr_dataset_dropdown.setEnabled(True)
        else:
            self.pllr_dataset_dropdown.set_data([], [], placeholder="No datasets registered")
            self.pllr_dataset_dropdown.setEnabled(False)
        self.pllr_alignment_dropdown.set_data([{"id": None, "data": ("Select a dataset first", "", "")}], ["Method", "Model", "Date", "Status"], placeholder="Select a dataset first") # Line 151
        self.pllr_alignment_dropdown.setEnabled(False)

    def init_ui(self):
        """Create the extract PLLR scores page"""
        self.setMinimumWidth(600)
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(30, 30, 30, 30)

        # Header with title and settings button
        header_layout = QHBoxLayout()

        # Title
        title = QLabel("Ⓒ Extract GOP Scoring")
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

        # Dataset selection dropdown
        dataset_label = QLabel("① Choose a PLLR Dataset")
        dataset_label.setStyleSheet("font-weight: bold; color: #2c3e50;")
        layout.addWidget(dataset_label)
        
        self.pllr_dataset_dropdown = MultiColumnComboBox()
        self.pllr_dataset_dropdown.setStyleSheet("""
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
    

        # Connect to selection handler
        self.pllr_dataset_dropdown.currentIndexChanged.connect(self.on_dataset_selected)
        
        layout.addWidget(self.pllr_dataset_dropdown)
        
        # Alignment selection dropdown (initially disabled)
        alignment_label = QLabel("② Choose an Alignment")
        alignment_label.setStyleSheet("font-weight: bold; color: #2c3e50;")
        layout.addWidget(alignment_label)
        
        self.pllr_alignment_dropdown = MultiColumnComboBox()
        self.pllr_alignment_dropdown.setStyleSheet(                              """
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

        self.pllr_alignment_dropdown.set_data([{"id": None, "data": ("Select a dataset first", "", "")}], ["Method", "Model", "Date", "Status"], placeholder="Select a dataset first")
        self.pllr_alignment_dropdown.setEnabled(False)
        
        layout.addWidget(self.pllr_alignment_dropdown)

        # Populate with registered datasets
        self.reload_datasets()

        # Output Path
        extract_output_label = QLabel("③ Output Path")
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
        self.extract_btn = QPushButton("④ Start GOP Extraction")
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
        print("\n=== PLLR EXTRACTION STARTED ===")
        
        # Get selected dataset
        selected_index = self.pllr_dataset_dropdown.currentIndex()
        selected_dataset_id = self.pllr_dataset_dropdown.itemData(selected_index)
        print(f"[DEBUG] Dataset index: {selected_index}, Dataset ID: {selected_dataset_id}")
        
        if not selected_dataset_id or selected_dataset_id == "No datasets registered":
            print("[ERROR] No dataset selected or invalid dataset ID")
            QMessageBox.warning(
                self, "No Dataset Selected",
                "Please select a dataset from the dropdown."
            )
            return
        
        print(f"[DEBUG] Dataset validated: {selected_dataset_id}")
        
        # Get selected alignment
        alignment_index = self.pllr_alignment_dropdown.currentIndex()
        selected_alignment_id = self.pllr_alignment_dropdown.itemData(alignment_index)
        print(f"[DEBUG] Alignment index: {alignment_index}, Alignment ID: {selected_alignment_id}")
        
        if not selected_alignment_id:
            print("[ERROR] No alignment selected or invalid alignment ID")
            QMessageBox.warning(
                self, "No Alignment Selected",
                "Please select an alignment from the dropdown."
            )
            return
        
        print(f"[DEBUG] Alignment validated: {selected_alignment_id}")
        print(f"[DEBUG] Fetching alignment metadata...")
        
        # Get alignment path
        alignment_data = alignments.get_alignment_metadata(selected_dataset_id, selected_alignment_id)
        print(f"[DEBUG] Alignment data retrieved: {alignment_data}")
        if not alignment_data:
            print(f"[ERROR] Could not find alignment data for ID: {selected_alignment_id}")
            QMessageBox.warning(
                self, "Invalid Alignment",
                f"Could not find alignment data for ID '{selected_alignment_id}'."
            )
            return
        
        textgrid_path = alignment_data["tg_path"] + "/cache"
        print(f"[DEBUG] TextGrid path from alignment: {textgrid_path}")
        print(f"[DEBUG] Checking if TextGrid path exists...")
        
        if not textgrid_path or not Path(textgrid_path).exists():
            print(f"[ERROR] TextGrid path does not exist: {textgrid_path}")
            QMessageBox.warning(
                self, "Invalid Alignment Path",
                f"Alignment output path does not exist: {textgrid_path}"
            )
            return
        
        print(f"[DEBUG] TextGrid path validated: {textgrid_path}")
        print(f"[DEBUG] Fetching dataset root path...")
        
        # Get dataset path
        dataset_meta = datasets.get_dataset_metadata(selected_dataset_id)

        wavlab_path = None
        if not (dataset_meta['cached'] == "True" or dataset_meta['cached'] is True):
            wavlab_path = dataset_meta['original_path']

        else:
            wavlab_path = datasets._get_dataset_root(selected_dataset_id) / "cache"


        print(f"[DEBUG] Dataset root path: {wavlab_path}")
        
        if not wavlab_path:
            print(f"[ERROR] Could not find dataset path for ID: {selected_dataset_id}")
            QMessageBox.warning(
                self, "Invalid Dataset",
                f"Could not find path for dataset."
            )
            return
        
        print(f"[DEBUG] Dataset path validated: {wavlab_path}")
        print(f"[DEBUG] Validating all paths...")
        
        # Validate inputs

        print(f"[DEBUG] Preparing paths for validation...")

        paths = {
            "TextGrid Path": textgrid_path,
            "Wav/lab Path": wavlab_path,
            "Output Path": self.extract_output_path.text(),
        }

        print(f"[DEBUG] Paths to validate: {paths}")

        if not validate_paths(self, paths):
            print("[ERROR] Path validation failed")
            return

        print("[DEBUG] All paths validated successfully")
        
        # Get current settings
        output_path = self.extract_output_path.text()

        print("\n[INFO] Extract PLLR clicked!")
        print(f"[INFO] TextGrid Path: {textgrid_path}")
        print(f"[INFO] Wav/lab Path: {wavlab_path}")
        print(f"[INFO] Output Path: {output_path}")
        print(f"[INFO] Phonewise output: {Path(output_path) / 'phonewise_proba.csv'}")
        print(f"[INFO] Framewise output: {Path(output_path) / 'framewise_proba.csv'}")

        # Update UI
        self.extract_status.setText("Processing...")
        self.extract_status.setStyleSheet("color: #f39c12; font-size: 12px; margin-top: 5px;")
        self.extract_btn.setEnabled(False)

        print("[DEBUG] Starting worker thread...")
        
        # Start worker thread
        self.worker = WorkerThread(
            lambda: self.extract_pllr_logic(textgrid_path, wavlab_path, output_path)
        )
        self.worker.finished.connect(self.on_extract_finished)
        self.worker.start()
        print("[DEBUG] Worker thread started")

    def extract_pllr_logic(self, textgrid_path, wavlab_path, output_path):
        """Actual PLLR extraction logic"""

        print("\n=== EXTRACT PLLR LOGIC ===")
        print(f"[LOGIC] Starting PLLR extraction...")
        print(f"[LOGIC] TextGrid Path: {textgrid_path}")
        print(f"[LOGIC] Wav/lab Path: {wavlab_path}")
        print(f"[LOGIC] Output Path: {output_path}")
        
        phonewise_path = str(Path(output_path) / "phonewise_proba.csv")
        framewise_path = str(Path(output_path) / "framewise_proba.csv")
        
        print(f"[LOGIC] Phonewise output file: {phonewise_path}")
        print(f"[LOGIC] Framewise output file: {framewise_path}")
        
        # Check what files exist
        print(f"[LOGIC] Checking TextGrid directory contents...")
        tg_path_obj = Path(textgrid_path)
        if tg_path_obj.is_dir():
            tg_files = list(tg_path_obj.glob("*.TextGrid"))
            print(f"[LOGIC] Found {len(tg_files)} .TextGrid files in {textgrid_path}")
            if tg_files:
                print(f"[LOGIC] First few TextGrid files: {[f.name for f in tg_files[:5]]}")
        else:
            print(f"[LOGIC] TextGrid path is not a directory: {textgrid_path}")
        
        print(f"[LOGIC] Checking wav/lab directory contents...")
        wav_path_obj = Path(wavlab_path)
        if wav_path_obj.is_dir():
            wav_files = list(wav_path_obj.glob("*.wav"))
            print(f"[LOGIC] Found {len(wav_files)} .wav files in {wavlab_path}")
            if wav_files:
                print(f"[LOGIC] First few wav files: {[f.name for f in wav_files[:5]]}")
        else:
            print(f"[LOGIC] Wav/lab path is not a directory: {wavlab_path}")
        
        # READ THE SETTINGS FROM THE FILE
        print(f"[LOGIC] Reading settings from file...")
        path_to_pllr_settings = get_storage_root() / "pllr_settings.json"
        pllr_settings = {}
        if path_to_pllr_settings.exists():
            print(f"[LOGIC] Settings file found at: {path_to_pllr_settings}")
            from json import load as json_load
            with open(path_to_pllr_settings, "r") as f:
                pllr_settings = json_load(f)
            print(f"[LOGIC] Settings loaded: {pllr_settings}")
        else:
            print(f"[LOGIC] Settings file not found at: {path_to_pllr_settings}")
            for key in PLLR_SETTINGS_CONFIG.fields:
                pllr_settings[key.name] = key.default_value
            print(f"[LOGIC] Default settings loaded: {pllr_settings}")
        print(f"[LOGIC] Calling compute_pllr()...")
        print(f"[LOGIC] Parameters:")
        print(f"         tg_files_path={textgrid_path}")
        print(f"         wav_files_path={wavlab_path}")
        print(f"         phone_key='phones'")
        print(f"         phonewise_proba_df={phonewise_path}")
        print(f"         framewise_proba_df={framewise_path}")
        print(f"         likelihood_dct=None")
        
        
        try:
            compute_pllr(
                tg_files_path=textgrid_path,
                wav_files_path=wavlab_path,
                phone_key="phones",
                phonewise_proba_df=phonewise_path,
                framewise_proba_df=framewise_path,
                recompute_probas=pllr_settings.get("recompute_probas", True),
                likelihood_dct=pllr_settings.get("likelihood_dct", None),
                # aggregation_function=pllr_settings.get("aggregation_function", "aggregate_by_phoneme_occurrence"),  
            )
            print(f"[LOGIC] compute_pllr() completed successfully")
            return "PLLR extracted successfully"
        except Exception as e:
            print(f"[ERROR] Exception in compute_pllr(): {type(e).__name__}")
            print(f"[ERROR] Exception message: {str(e)}")
            import traceback
            print(f"[ERROR] Traceback:\n{traceback.format_exc()}")
            raise

    def on_extract_finished(self, success, message):
        """Handle completion of extract PLLR operation"""
        print(f"\n=== PLLR EXTRACTION FINISHED ===")
        print(f"[FINISHED] Success: {success}")
        print(f"[FINISHED] Message: {message}")
        
        self.extract_btn.setEnabled(True)

        if success:
            print(f"[FINISHED] Extraction completed successfully")
            self.extract_status.setText("✓ " + message)
            self.extract_status.setStyleSheet("color: #27ae60; font-size: 12px; margin-top: 5px;")
            QMessageBox.information(self, "Success", message)
        else:
            print(f"[FINISHED] Extraction failed with error: {message}")
            self.extract_status.setText("✗ Error occurred")
            self.extract_status.setStyleSheet("color: #e74c3c; font-size: 12px; margin-top: 5px;")
            QMessageBox.critical(self, "Error", f"An error occurred:\n{message}")
