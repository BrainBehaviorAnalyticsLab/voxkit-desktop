from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QFileDialog,
    QMessageBox
)
from PyQt6.QtCore import Qt
from workers.worker_thread import WorkerThread
from pypllrcomputer import compute_pllr
from config import Defaults
from utils.validation import validate_path, validate_paths


class EvaluatingPage(QWidget):
    def __init__(self, parent=None):
        super().__init__()
        self.init_ui()
        
    def on_extract_settings(self):
        """Handle settings button click on extract page"""
        QMessageBox.information(self, "Settings", "Extract page settings coming soon...")
    
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
        wavlab_label = QLabel("Audio Path")
        wavlab_label.setStyleSheet("font-weight: bold; color: #34495e;")
        layout.addWidget(wavlab_label)
        
        wavlab_layout = QHBoxLayout()
        wavlab_layout.setSpacing(8)
        self.wavlab_path = QLineEdit(Defaults['audio_path'])
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
        self.extract_output_path = QLineEdit(Defaults['output_path'])
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
        return self
    
    def browse_directory(self, line_edit):
        """Open directory browser and update the line edit"""
        directory = QFileDialog.getExistingDirectory(
            self,
            "Select Directory",
            line_edit.text() if Path(line_edit.text()).exists() else str(Path.home())
        )
        if directory:
            line_edit.setText(directory)
            if not validate_path(self, directory):
                QMessageBox.warning(self, "Invalid Path", f"The path does not exist:\n{directory}")
    
    def on_extract_pllr(self):
        """Handle Extract PLLR button click"""
        # Validate inputs
        paths = {
            "TextGrid Path": self.textgrid_path.text(),
            "Wav/lab Path": self.wavlab_path.text(),
            "Output Path": self.extract_output_path.text()
        }
        
        if not validate_paths(self, paths):
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
