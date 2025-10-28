from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QRadioButton, QLabel, QLineEdit, QPushButton, QFileDialog,
    QGroupBox, QMessageBox
)
from PyQt6.QtCore import Qt
from workers.worker_thread import WorkerThread
from config import Defaults
from utils.validation import validate_path, validate_paths
from Wav2TextGrid.wav2textgrid_train import train_aligner
from utils.storage import list_models, create_train_destination

class TrainingPage(QWidget):
    def __init__(self, parent):
        super().__init__()
        self.train_audio_path = Defaults['audio_path']
        self.train_textgrid_path = Defaults['textgrid_path']
        self.train_model_name = 'default_model'
        self.selected_mode = Defaults["mode"]
        self.parent = parent
        self.init_ui()
    
    def on_mode_changed(self, model_name):
        """Handle model selection change"""
        if self.sender().isChecked():
            self.selected_mode = model_name
            print(f"Model changed to: {self.selected_mode}")

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
    
    def on_train_model(self):
        """Handle Start Training button click"""
        # Validate inputs
        paths = {
            "Training Audio Directory": self.train_audio_path.text(),
            "Training Text Grid Directory": self.train_textgrid_path.text()
        }
        
        if not validate_paths(self, paths):
            return
        
        # Get current settings
        audio_path = self.train_audio_path.text()
        textgrid_path = self.train_textgrid_path.text()
        model_name = self.train_model_name.text()
        mode = self.selected_mode

        # Check that model name isn't used
        if not model_name:
            QMessageBox.warning(self, "Invalid Model Name", "Please enter a valid model name.")
            return
        names_taken = list_models(mode).keys()
        
        if model_name in names_taken:
            QMessageBox.warning(self, "Model Name Taken", f"The model name '{model_name}' is already in use. Please choose a different name.")
            return
        
        print("Start Training clicked!")
        print(f"Model: {mode}")
        print(f"Training Audio Directory: {audio_path}")
        print(f"Training Text Grid Directory: {textgrid_path}")
        print(f"Model Name: {model_name}")
        
        # Update UI
        self.train_status.setText("Training...")
        self.train_status.setStyleSheet("color: #f39c12; font-size: 12px; margin-top: 5px;")
        self.train_btn.setEnabled(False)
        
        # Start worker thread
        self.worker = WorkerThread(lambda: self.train_model_logic(
            audio_path, textgrid_path, model_name, mode
        ))
        self.worker.finished.connect(self.on_train_finished)
        self.worker.start()
    
    def train_model_logic(self, audio_path, textgrid_path, model_name, model):
        """Actual model training logic"""
        print("Training logic would be implemented here.")
        print(f"Audio Path: {audio_path}"
              f"\nTextGrid Path: {textgrid_path}"
              f"\nModel Name: {model_name}"
              f"\nModel: {model}")
        
        data_path, model_path, root_path, eval_path = create_train_destination(model_name, model)

        print(f"Created training run directories at: {root_path}")

        train_aligner(
            train_audio_dir=audio_path,
            train_textgrid_dir=textgrid_path,
            tokenizer_name="charsiu/tokenizer_en_cmu",
            model_output_dir=model_path,
            tg_output_dir=eval_path,
            dataset_dir=data_path,
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
        QMessageBox.information(self, "Settings", "Training page settings coming soon...")

    def init_ui(self):
        """Create the training page"""
        self.setMinimumWidth(600)
        layout = QVBoxLayout(self)
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

        # Model selection group
        model_group = QGroupBox()
        model_layout = QVBoxLayout()
        model_layout.setSpacing(8)
        
        # Info label
        info_label = QLabel("ⓘ Select training method")
        info_label.setStyleSheet("font-size: 12px; color: #7f8c8d;")
        model_layout.addWidget(info_label)
        
        # MFA radio button
        self.mfa_radio = QRadioButton("Montreal Forced Aligner (MFA)")
        self.mfa_radio.setChecked(True)
        self.mfa_radio.toggled.connect(lambda: self.on_mode_changed('MFA'))
        model_layout.addWidget(self.mfa_radio)
        
        mfa_info = QLabel("Default phonetic alignment strategy")
        mfa_info.setStyleSheet("color: #95a5a6; font-size: 11px; margin-left: 25px;")
        model_layout.addWidget(mfa_info)
        
        model_layout.addSpacing(5)
        
        # Wav2TextGrid radio button
        self.wav2text_radio = QRadioButton("Wav2TextGrid")
        self.wav2text_radio.toggled.connect(lambda: self.on_mode_changed("W2TG"))
        model_layout.addWidget(self.wav2text_radio)
        
        wav2text_info = QLabel("Neural network-based alignment")
        wav2text_info.setStyleSheet("color: #95a5a6; font-size: 11px; margin-left: 25px;")
        model_layout.addWidget(wav2text_info)
        
        model_group.setLayout(model_layout)
        layout.addWidget(model_group)
        
        layout.addSpacing(10)
        
        # Training Audio Directory
        audio_label = QLabel("Training Audio Directory:")
        audio_label.setStyleSheet("font-weight: bold; color: #2c3e50; margin-bottom: 5px;")
        layout.addWidget(audio_label)
        
        train_audio_layout = QHBoxLayout()
        train_audio_layout.setSpacing(8)
        self.train_audio_path = QLineEdit(Defaults['audio_path'])
        self.train_audio_browse = QPushButton("Browse")
        self.train_audio_browse.setFixedWidth(100)
        self.train_audio_browse.clicked.connect(lambda: self.browse_directory(self.train_audio_path))
        train_audio_layout.addWidget(self.train_audio_path, stretch=1)
        train_audio_layout.addWidget(self.train_audio_browse)
        layout.addLayout(train_audio_layout)
        
        layout.addSpacing(10)
        
        # Training Text Grid Directory
        textgrid_label = QLabel("Training Text Grid Directory:")
        textgrid_label.setStyleSheet("font-weight: bold; color: #2c3e50; margin-bottom: 5px;")
        layout.addWidget(textgrid_label)
        
        train_textgrid_layout = QHBoxLayout()
        train_textgrid_layout.setSpacing(8)
        self.train_textgrid_path = QLineEdit(Defaults['textgrid_path'])
        self.train_textgrid_browse = QPushButton("Browse")
        self.train_textgrid_browse.setFixedWidth(100)
        self.train_textgrid_browse.clicked.connect(lambda: self.browse_directory(self.train_textgrid_path))
        train_textgrid_layout.addWidget(self.train_textgrid_path, stretch=1)
        train_textgrid_layout.addWidget(self.train_textgrid_browse)
        layout.addLayout(train_textgrid_layout)
        
        layout.addSpacing(10)
        
        # Model Name
        model_name_label = QLabel("Model Name:")
        model_name_label.setStyleSheet("font-weight: bold; color: #2c3e50; margin-bottom: 5px;")
        layout.addWidget(model_name_label)
        
        self.train_model_name = QLineEdit("my_custom_model")
        layout.addWidget(self.train_model_name)
        
        layout.addSpacing(15)
        
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
