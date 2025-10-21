import sys
from pathlib import Path
import subprocess
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QRadioButton, QLabel, QLineEdit, QPushButton, QFileDialog,
    QGroupBox, QMessageBox, QStackedWidget, QListWidget
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

from pypllrcomputer import compute_pllr
from Wav2TextGrid.wav2textgrid import align_dirs

class WorkerThread(QThread):
    """Thread for running operations without blocking the UI"""
    finished = pyqtSignal(bool, str)  # success, message
    
    def __init__(self, operation_func):
        super().__init__()
        self.operation_func = operation_func
    
    def run(self):
        try:
            result = self.operation_func()
            self.finished.emit(True, result if result else "Operation completed successfully")
        except Exception as e:
            self.finished.emit(False, str(e))


class AlignmentGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.selected_model = "MFA"  # Default model selection
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle("TPE - PLLR Pipeline")
        self.setMinimumSize(1000, 600)
        
        # Set application-wide stylesheet
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f5;
            }
            QWidget {
                background-color: #f5f5f5;
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 13px;
            }
            QGroupBox {
                background-color: white;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                margin-top: 10px;
                padding: 15px;
            }
            QLabel {
                color: #333;
                background-color: transparent;
            }
            QLineEdit {
                background-color: white;
                border: 1px solid #d0d0d0;
                border-radius: 5px;
                padding: 8px 12px;
                min-height: 20px;
                color: #333;
            }
            QLineEdit:focus {
                border: 2px solid #4a90e2;
            }
            QPushButton {
                background-color: white;
                border: 1px solid #d0d0d0;
                border-radius: 5px;
                padding: 8px 16px;
                min-width: 80px;
                min-height: 20px;
                color: #333;
            }
            QPushButton:hover {
                background-color: #f0f0f0;
                border-color: #b0b0b0;
            }
            QPushButton:pressed {
                background-color: #e0e0e0;
            }
            QRadioButton {
                background-color: transparent;
                color: #333;
                spacing: 8px;
            }
            QRadioButton::indicator {
                width: 18px;
                height: 18px;
                border-radius: 9px;
            }
            QRadioButton::indicator:unchecked {
                border: 2px solid #d0d0d0;
                background-color: white;
            }
            QRadioButton::indicator:checked {
                border: 2px solid #4a90e2;
                background-color: #4a90e2;
            }
            QRadioButton::indicator:hover {
                border-color: #4a90e2;
            }
            QListWidget {
                background-color: white;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                padding: 5px;
                outline: none;
            }
            QListWidget::item {
                padding: 12px 15px;
                border-radius: 5px;
                color: #333;
            }
            QListWidget::item:selected {
                background-color: #4a90e2;
                color: white;
            }
            QListWidget::item:hover {
                background-color: #b0cef2;
            }
        """)
        
        # Central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # Left side - Navigation menu
        self.menu_list = QListWidget()
        self.menu_list.setMaximumWidth(200)
        self.menu_list.addItem("Ⓐ  Train Aligner")
        self.menu_list.addItem("Ⓑ  Predict Alignments")
        self.menu_list.addItem("Ⓒ  Extract PLLR Scores")
        main_layout.addWidget(self.menu_list)
        
        # Right side - Stacked widget for different pages
        self.stacked_widget = QStackedWidget()
        main_layout.addWidget(self.stacked_widget, stretch=1)
        
        # Add pages
        self.stacked_widget.addWidget(self.create_training_page())
        self.stacked_widget.addWidget(self.create_predict_page())
        self.stacked_widget.addWidget(self.create_extract_page())
        
        # Connect signal AFTER stacked_widget is created and populated
        self.menu_list.currentRowChanged.connect(self.change_page)
        self.menu_list.setCurrentRow(0)
    
    def change_page(self, index):
        """Change the displayed page based on menu selection"""
        self.stacked_widget.setCurrentIndex(index)
    
    def create_training_page(self):
        """Create the training page (placeholder)"""
        page = QWidget()
        page.setMinimumWidth(600)
        layout = QVBoxLayout(page)
        layout.setSpacing(15)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # Header with title and settings button
        header_layout = QHBoxLayout()
        
        # Title
        title = QLabel("Training")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #2c3e50;")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        # Settings button
        settings_btn = QPushButton("⚙️")
        settings_btn.setFixedSize(40, 40)
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
        header_layout.addWidget(settings_btn)
        
        layout.addLayout(header_layout)
        
        layout.addSpacing(20)
        
        # Placeholder text
        placeholder = QLabel("Training module coming soon...")
        placeholder.setStyleSheet("font-size: 16px; color: #7f8c8d;")
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(placeholder)
        
        layout.addStretch()
        return page
    
    def create_predict_page(self):
        """Create the predict alignments page"""
        page = QWidget()
        page.setMinimumWidth(600)
        layout = QVBoxLayout(page)
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
        settings_btn.setFixedSize(40, 40)
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
        
        layout.addSpacing(10)
        
        # Model selection group
        model_group = QGroupBox()
        model_layout = QVBoxLayout()
        model_layout.setSpacing(8)
        
        # Info label
        info_label = QLabel("ⓘ Select alignment model")
        info_label.setStyleSheet("font-size: 12px; color: #7f8c8d;")
        model_layout.addWidget(info_label)
        
        # MFA radio button
        self.mfa_radio = QRadioButton("Montreal Forced Aligner (MFA)")
        self.mfa_radio.setChecked(True)
        self.mfa_radio.toggled.connect(lambda: self.on_model_changed("MFA"))
        model_layout.addWidget(self.mfa_radio)
        
        mfa_info = QLabel("Default phonetic alignment model")
        mfa_info.setStyleSheet("color: #95a5a6; font-size: 11px; margin-left: 25px;")
        model_layout.addWidget(mfa_info)
        
        model_layout.addSpacing(5)
        
        # Wav2TextGrid radio button
        self.wav2text_radio = QRadioButton("Wav2TextGrid")
        self.wav2text_radio.toggled.connect(lambda: self.on_model_changed("Wav2TextGrid"))
        model_layout.addWidget(self.wav2text_radio)
        
        wav2text_info = QLabel("Neural network-based alignment")
        wav2text_info.setStyleSheet("color: #95a5a6; font-size: 11px; margin-left: 25px;")
        model_layout.addWidget(wav2text_info)
        
        model_group.setLayout(model_layout)
        layout.addWidget(model_group)
        
        layout.addSpacing(10)
        
        # Data Corpus Path
        corpus_label = QLabel("Data Corpus Path")
        corpus_label.setStyleSheet("font-weight: bold; color: #34495e;")
        layout.addWidget(corpus_label)
        
        corpus_layout = QHBoxLayout()
        corpus_layout.setSpacing(8)
        self.corpus_path = QLineEdit("/path/to/data/corpus")
        self.corpus_browse = QPushButton("Browse")
        self.corpus_browse.setFixedWidth(100)
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
        self.textgrid_browse.clicked.connect(lambda: self.browse_directory(self.textgrid_output_path))
        output_layout.addWidget(self.textgrid_output_path, stretch=1)
        output_layout.addWidget(self.textgrid_browse)
        layout.addLayout(output_layout)
        
        layout.addSpacing(15)
        
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
        return page
    
    def on_training_settings(self):
        """Handle settings button click on training page"""
        QMessageBox.information(self, "Settings", "Training page settings coming soon...")
    
    def on_predict_settings(self):
        """Handle settings button click on predict page"""
        QMessageBox.information(self, "Settings", "Predict page settings coming soon...")
    
    def on_extract_settings(self):
        """Handle settings button click on extract page"""
        QMessageBox.information(self, "Settings", "Extract page settings coming soon...")
    
    def create_extract_page(self):
        """Create the extract PLLR scores page"""
        page = QWidget()
        page.setMinimumWidth(600)
        layout = QVBoxLayout(page)
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
        settings_btn.setFixedSize(40, 40)
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
        self.textgrid_path_browse.clicked.connect(lambda: self.browse_directory(self.textgrid_path))
        textgrid_layout.addWidget(self.textgrid_path, stretch=1)
        textgrid_layout.addWidget(self.textgrid_path_browse)
        layout.addLayout(textgrid_layout)
        
        # Wav/lab Path
        wavlab_label = QLabel("Wav/Lab Path")
        wavlab_label.setStyleSheet("font-weight: bold; color: #34495e;")
        layout.addWidget(wavlab_label)
        
        wavlab_layout = QHBoxLayout()
        wavlab_layout.setSpacing(8)
        self.wavlab_path = QLineEdit("/path/to/data/corpus")
        self.wavlab_browse = QPushButton("Browse")
        self.wavlab_browse.setFixedWidth(100)
        self.wavlab_browse.clicked.connect(lambda: self.browse_directory(self.wavlab_path))
        wavlab_layout.addWidget(self.wavlab_path, stretch=1)
        wavlab_layout.addWidget(self.wavlab_browse)
        layout.addLayout(wavlab_layout)
        
        # Output Path
        extract_output_label = QLabel("Output Path")
        extract_output_label.setStyleSheet("font-weight: bold; color: #34495e;")
        layout.addWidget(extract_output_label)
        
        extract_output_layout = QHBoxLayout()
        extract_output_layout.setSpacing(8)
        self.extract_output_path = QLineEdit("/path/to/output/directory")
        self.extract_browse = QPushButton("Browse")
        self.extract_browse.setFixedWidth(100)
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
        return page
    
    def on_model_changed(self, model_name):
        """Handle model selection change"""
        if self.sender().isChecked():
            self.selected_model = model_name
            print(f"Model changed to: {self.selected_model}")
    
    def browse_directory(self, line_edit):
        """Open directory browser and update the line edit"""
        directory = QFileDialog.getExistingDirectory(
            self,
            "Select Directory",
            line_edit.text() if Path(line_edit.text()).exists() else str(Path.home())
        )
        if directory:
            line_edit.setText(directory)
            if not self.validate_path(directory):
                QMessageBox.warning(self, "Invalid Path", f"The path does not exist:\n{directory}")
    
    def validate_path(self, path):
        """Validate if a path exists"""
        return Path(path).exists()
    
    def validate_inputs(self, paths_dict):
        """Validate multiple paths and show error if any are invalid"""
        invalid_paths = []
        for label, path in paths_dict.items():
            if not self.validate_path(path):
                invalid_paths.append(f"{label}: {path}")
        
        if invalid_paths:
            QMessageBox.warning(
                self,
                "Invalid Paths",
                "The following paths do not exist:\n\n" + "\n".join(invalid_paths)
            )
            return False
        return True
    
    def on_predict_alignments(self):
        """Handle Predict Alignments button click"""
        # Validate inputs
        paths = {
            "Data Corpus Path": self.corpus_path.text(),
            "Textgrid Output Path": self.textgrid_output_path.text()
        }
        
        if not self.validate_inputs(paths):
            return
        
        # Get current settings
        corpus_path = self.corpus_path.text()
        output_path = self.textgrid_output_path.text()
        model = self.selected_model
        
        print("Predict Alignments clicked!")
        print(f"Model: {model}")
        print(f"Corpus Path: {corpus_path}")
        print(f"Output Path: {output_path}")
        
        # Update UI
        self.predict_status.setText("Processing...")
        self.predict_status.setStyleSheet("color: #f39c12; font-size: 12px; margin-top: 5px;")
        self.predict_btn.setEnabled(False)
        
        # Start worker thread
        self.worker = WorkerThread(lambda: self.predict_alignments_logic(
            corpus_path, output_path, model
        ))
        self.worker.finished.connect(self.on_predict_finished)
        self.worker.start()
    
    def predict_alignments_logic(self, wav_files_path, textgrid_output_path, model):
        """Actual alignment prediction logic"""
        if model == "MFA":
            # Activate conda environment and run MFA
            subprocess.run(
                'conda run -n aligner mfa align ' +
                f'"{wav_files_path}" english_us_arpa english_us_arpa "{textgrid_output_path}"',
                shell=True,
                check=True
            )
        elif model == "Wav2TextGrid":
            # Call Wav2TextGrid alignment function here
            align_dirs(
                wavfile_or_dir=wav_files_path, 
                transcriptfile_or_dir=wav_files_path, 
                outfile_or_dir=textgrid_output_path
            )
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
    
    def on_extract_pllr(self):
        """Handle Extract PLLR button click"""
        # Validate inputs
        paths = {
            "TextGrid Path": self.textgrid_path.text(),
            "Wav/lab Path": self.wavlab_path.text(),
            "Output Path": self.extract_output_path.text()
        }
        
        if not self.validate_inputs(paths):
            return
        
        # Get current settings
        textgrid_path = self.textgrid_path.text()
        wavlab_path = self.wavlab_path.text()
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
        self.worker = WorkerThread(lambda: self.extract_pllr_logic(
            textgrid_path, wavlab_path, output_path
        ))
        self.worker.finished.connect(self.on_extract_finished)
        self.worker.start()
    
    def extract_pllr_logic(self, textgrid_path, wavlab_path, output_path):
        """Actual PLLR extraction logic"""
        compute_pllr(
            tg_files_path=textgrid_path,
            wav_files_path=wavlab_path,
            phone_key="phones",
            phonewise_proba_df=str(Path(output_path) / "phonewise_proba.csv"),
            framewise_proba_df=str(Path(output_path) / "framewise_proba.csv")
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


def main():
    app = QApplication(sys.argv)
    
    # Set application style
    app.setStyle('Fusion')
    
    window = AlignmentGUI()
    window.show()
    
    sys.exit(app.exec())


if __name__ == '__main__':
    main()