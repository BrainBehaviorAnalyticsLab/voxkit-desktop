import subprocess
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QButtonGroup,
    QComboBox,
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
from voxkit.engines.w2tg_engine import AlignmentSettings as W2TGAlignmentSettings
from voxkit.engines.w2tg_engine import W2TGEngine
from voxkit.gui.components.modals.aligning_settings import AlignmentSettingsDialog
from voxkit.storage.paths import list_models
from voxkit.storage.validation import validate_path, validate_paths
from voxkit.workers.worker_thread import WorkerThread

from .styles import BrowseButtonStyle


class PredictingPage(QWidget):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.corpus_path = None
        self.textgrid_output_path = None
        self.selected_mode = Defaults["mode"]
        self.init_ui()

    def on_mode_changed(self):
        """Handle model selection change"""
        # Check which radio button is actually checked
        if self.mfa_radio.isChecked():
            self.selected_mode = "MFA"
            self.mfa_dropdown.setVisible(True)
            self.w2tg_dropdown.setVisible(False)
        elif self.wav2text_radio.isChecked():
            self.selected_mode = "W2TG"
            self.mfa_dropdown.setVisible(False)
            self.w2tg_dropdown.setVisible(True)
            

        print(f"Model changed to: {self.selected_mode}")
    
    def reload_models(self):
        """Reload models in the dropdowns"""
        model_names_mfa = list_models("MFA", add_date=True).keys()
        self.mfa_dropdown.clear()
        self.mfa_dropdown.addItems(list(model_names_mfa) if model_names_mfa else [])

        model_names_w2tg = list_models("W2TG", add_date=True).keys()
        self.w2tg_dropdown.clear()
        self.w2tg_dropdown.addItems(list(model_names_w2tg) if model_names_w2tg else [])

    def init_ui(self):
        """Create the predict alignments page"""
        self.setMinimumWidth(600)
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(30, 30, 30, 30)

        # Header with title and settings button
        header_layout = QHBoxLayout()

        # Title
        title = QLabel("Predict Alignments")
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

        # Model selection group
        model_group = QGroupBox()
        model_layout = QVBoxLayout()
        model_layout.setSpacing(8)

        # Info label
        info_label = QLabel("ⓘ Select alignment method")
        info_label.setStyleSheet("font-size: 12px; color: #7f8c8d;")
        model_layout.addWidget(info_label)
        # ----------------------------------------------------------------------
        # MFA block (aligned)
        # ----------------------------------------------------------------------
        mfa_layout = QHBoxLayout()
        mfa_layout.setSpacing(12)

        # Radio button
        self.mfa_radio = QRadioButton("Montreal Forced Aligner (MFA)")
        self.mfa_radio.setChecked(True)
        self.mfa_radio.toggled.connect(lambda: self.on_mode_changed())

        # Add radio + fixed spacer to align dropdowns
        mfa_radio_container = QHBoxLayout()
        mfa_radio_container.addWidget(self.mfa_radio)
        mfa_radio_container.addStretch()  # pushes radio to the left within its container
        mfa_radio_container.setContentsMargins(0, 0, 0, 0)

        radio_widget_mfa = QWidget()
        radio_widget_mfa.setLayout(mfa_radio_container)

        radio_widget_mfa.setFixedWidth(280)  # <-- SAME fixed width for both
        radio_widget_mfa.setStyleSheet("background-color: white;")
        mfa_layout.addWidget(radio_widget_mfa)

        # Dropdown
        self.mfa_dropdown = QComboBox()
        self.mfa_dropdown.setToolTip("Select the MFA model to use for alignment")
        self.mfa_dropdown.setPlaceholderText("Select MFA Model")
        self.mfa_dropdown.setStyleSheet("color: #95a5a6;")
        model_names_mfa = list_models("MFA", add_date=True).keys()
        self.mfa_dropdown.addItems(list(model_names_mfa) if model_names_mfa else [])
        self.mfa_dropdown.setFixedWidth(300)
        self.mfa_dropdown.setVisible(True)
        mfa_layout.addWidget(self.mfa_dropdown)
        mfa_layout.addStretch()

        model_layout.addLayout(mfa_layout)

        # Info
        mfa_info = QLabel("Default phonetic alignment method")
        mfa_info.setStyleSheet("color: #95a5a6; font-size: 11px; margin-left: 25px;")
        model_layout.addWidget(mfa_info)
        model_layout.addSpacing(5)

        # ----------------------------------------------------------------------
        # W2TG block (IDENTICAL alignment)
        # ----------------------------------------------------------------------
        w2tg_layout = QHBoxLayout()
        w2tg_layout.setSpacing(12)

        # Radio button
        self.wav2text_radio = QRadioButton("Wav2TextGrid (W2TG)")
        self.wav2text_radio.toggled.connect(lambda: self.on_mode_changed())

        self.mode_button_group = QButtonGroup(self)

        self.mode_button_group.addButton(self.mfa_radio)
        self.mode_button_group.addButton(self.wav2text_radio)

        # Same fixed-width container
        w2tg_radio_container = QHBoxLayout()
        w2tg_radio_container.addWidget(self.wav2text_radio)
        w2tg_radio_container.addStretch()
        w2tg_radio_container.setContentsMargins(0, 0, 0, 0)

        radio_widget_w2tg = QWidget()
        radio_widget_w2tg.setLayout(w2tg_radio_container)
        radio_widget_w2tg.setFixedWidth(280)  # <-- MUST match MFA
        radio_widget_w2tg.setStyleSheet("background-color: white;")
        w2tg_layout.addWidget(radio_widget_w2tg)

        # Dropdown
        self.w2tg_dropdown = QComboBox()
        self.w2tg_dropdown.setToolTip("Select the W2TG model to use for alignment")
        self.w2tg_dropdown.setPlaceholderText("Select W2TG Model")
        self.w2tg_dropdown.setStyleSheet("color: #95a5a6;")
        model_names_w2tg = list_models("W2TG", add_date=True).keys()
        self.w2tg_dropdown.addItems(list(model_names_w2tg) if model_names_w2tg else [])
        self.w2tg_dropdown.setFixedWidth(300)
        self.w2tg_dropdown.setVisible(False)
        w2tg_layout.addWidget(self.w2tg_dropdown)
        w2tg_layout.addStretch()

        model_layout.addLayout(w2tg_layout)

        # Info
        wav2text_info = QLabel("Neural network-based alignment")
        wav2text_info.setStyleSheet("color: #95a5a6; font-size: 11px; margin-left: 25px;")
        model_layout.addWidget(wav2text_info)

        model_group.setLayout(model_layout)
        layout.addWidget(model_group)

        layout.addSpacing(10)

        # Data Corpus Path
        corpus_label = QLabel("Audio Path")
        corpus_label.setStyleSheet("font-weight: bold; color: #34495e;")
        layout.addWidget(corpus_label)

        corpus_layout = QHBoxLayout()
        corpus_layout.setSpacing(8)
        self.corpus_path = QLineEdit("/path/to/data/corpus")
        self.corpus_browse = QPushButton("Browse")
        self.corpus_browse.setFixedWidth(100)
        self.corpus_browse.setStyleSheet(BrowseButtonStyle)
        self.corpus_browse.setStyleSheet(BrowseButtonStyle)
        self.corpus_browse.clicked.connect(lambda: self.browse_directory(self.corpus_path))
        corpus_layout.addWidget(self.corpus_path, stretch=1)
        corpus_layout.addWidget(self.corpus_browse)
        layout.addLayout(corpus_layout)

        # Textgrid Output Path
        output_label = QLabel("TextGrid Output Path")
        output_label.setStyleSheet("font-weight: bold; color: #34495e;")
        layout.addWidget(output_label)

        output_layout = QHBoxLayout()
        output_layout.setSpacing(8)
        self.textgrid_output_path = QLineEdit("/path/to/output/directory")
        self.textgrid_browse = QPushButton("Browse")
        self.textgrid_browse.setFixedWidth(100)
        self.textgrid_browse.setStyleSheet(BrowseButtonStyle)
        self.textgrid_browse.setStyleSheet(BrowseButtonStyle)
        self.textgrid_browse.clicked.connect(
            lambda: self.browse_directory(self.textgrid_output_path)
        )
        output_layout.addWidget(self.textgrid_output_path, stretch=1)
        output_layout.addWidget(self.textgrid_browse)
        layout.addLayout(output_layout)

        layout.addSpacing(10)

        # Predict Alignments Button
        self.predict_btn = QPushButton("Predict Alignments")
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
        # Create and show settings dialog
        settings_dialog = AlignmentSettingsDialog(self)

        result = settings_dialog.exec()

        # Clean up
        self.parent.setGraphicsEffect(None)

        if result == QDialog.DialogCode.Accepted:
            # Apply settings
            print("Settings applied:")
            print(f"Expected Pairs: {settings_dialog.expected_pairs.value()}")
            print(f"Assert Num Pairs: {settings_dialog.assert_num_pairs.isChecked()}")
            print(f"Use GPU: {settings_dialog.use_gpu.isChecked()}")

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

    def on_predict_alignments(self):
        """Handle Predict Alignments button click"""
        # Validate inputs
        paths = {
            "Data Corpus Path": self.corpus_path.text(),
            "Textgrid Output Path": self.textgrid_output_path.text(),
        }

        if not validate_paths(self, paths):
            return

        # Get current settings
        corpus_path = self.corpus_path.text()
        output_path = self.textgrid_output_path.text()
        mode = self.selected_mode

        print("Predict Alignments clicked!")
        print(f"Model: {mode}")
        print(f"Corpus Path: {corpus_path}")
        print(f"Output Path: {output_path}")

        # Update UI
        self.predict_status.setText("Processing...")
        self.predict_status.setStyleSheet("color: #f39c12; font-size: 12px; margin-top: 5px;")
        self.predict_btn.setEnabled(False)

        # Start worker thread
        self.worker = WorkerThread(
            lambda: self.predict_alignments_logic(corpus_path, output_path, mode)
        )
        self.worker.finished.connect(self.on_predict_finished)
        self.worker.start()

    def predict_alignments_logic(self, wav_files_path, textgrid_output_path, model):
        """Actual alignment prediction logic"""
        if model == "MFA":
            # Get the selected model from dropdown
            selected_mfa_model = self.mfa_dropdown.currentText()

            # Activate conda environment and run MFA
            subprocess.run(
                "conda run -n aligner mfa align "
                + f'"{wav_files_path}" {selected_mfa_model} {selected_mfa_model} "{textgrid_output_path}"',
                shell=True,
                check=True,
            )
        elif model == "W2TG":
            # Get the selected model from dropdown
            selected_w2tg_model = self.w2tg_dropdown.currentText() or None
            print(f"Using W2TG model: {selected_w2tg_model}")

            settings = W2TGAlignmentSettings(
                aligner_model=selected_w2tg_model,
                use_speaker_adaptation=True,
                use_gpu=False,
                file_type="wav",
            )
            engine = W2TGEngine()
            engine.run_alignment(wav_files_path, textgrid_output_path, settings)
        else:
            raise ValueError(f"Unknown model selected: {model}")

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
