import subprocess
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from voxkit.storage.validation import validate_paths
from voxkit.workers.worker_thread import WorkerThread

from .styles import BrowseButtonStyle


class EvaluationStacker(QWidget):
    """Page for evaluating aligner performance against reference alignments."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.reference_path = None
        self.predicted_path = None
        self.output_path = None
        self.init_ui()

    def init_ui(self):
        self.setMinimumWidth(600)
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(30, 30, 30, 30)

        # Header
        header_layout = QHBoxLayout()
        title = QLabel("Evaluate Aligner")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #2c3e50;")
        header_layout.addWidget(title)
        header_layout.addStretch()
        layout.addLayout(header_layout)

        layout.addSpacing(15)

        # Evaluation method selector
        method_group = QGroupBox("Select Evaluation Method")
        method_layout = QHBoxLayout()
        self.method_dropdown = QComboBox()
        self.method_dropdown.addItems(["Cross-Validation", "Holdout Test", "Custom Evaluation"])
        self.method_dropdown.setStyleSheet("color: #34495e; font-size: 13px;")
        method_layout.addWidget(self.method_dropdown)
        method_group.setLayout(method_layout)
        layout.addWidget(method_group)

        layout.addSpacing(10)

        # Reference Alignments
        ref_label = QLabel("Reference Alignment Path")
        ref_label.setStyleSheet("font-weight: bold; color: #34495e;")
        layout.addWidget(ref_label)

        ref_layout = QHBoxLayout()
        self.reference_path = QLineEdit("/path/to/reference/alignments")
        ref_browse = QPushButton("Browse")
        ref_browse.setFixedWidth(100)
        ref_browse.setStyleSheet(BrowseButtonStyle)
        ref_browse.clicked.connect(lambda: self.browse_directory(self.reference_path))
        ref_layout.addWidget(self.reference_path, stretch=1)
        ref_layout.addWidget(ref_browse)
        layout.addLayout(ref_layout)

        # Predicted Alignments
        pred_label = QLabel("Predicted Alignment Path")
        pred_label.setStyleSheet("font-weight: bold; color: #34495e;")
        layout.addWidget(pred_label)

        pred_layout = QHBoxLayout()
        self.predicted_path = QLineEdit("/path/to/predicted/alignments")
        pred_browse = QPushButton("Browse")
        pred_browse.setFixedWidth(100)
        pred_browse.setStyleSheet(BrowseButtonStyle)
        pred_browse.clicked.connect(lambda: self.browse_directory(self.predicted_path))
        pred_layout.addWidget(self.predicted_path, stretch=1)
        pred_layout.addWidget(pred_browse)
        layout.addLayout(pred_layout)

        # Output Path
        out_label = QLabel("Evaluation Output Path")
        out_label.setStyleSheet("font-weight: bold; color: #34495e;")
        layout.addWidget(out_label)

        out_layout = QHBoxLayout()
        self.output_path = QLineEdit("/path/to/evaluation/results")
        out_browse = QPushButton("Browse")
        out_browse.setFixedWidth(100)
        out_browse.setStyleSheet(BrowseButtonStyle)
        out_browse.clicked.connect(lambda: self.browse_directory(self.output_path))
        out_layout.addWidget(self.output_path, stretch=1)
        out_layout.addWidget(out_browse)
        layout.addLayout(out_layout)

        layout.addSpacing(15)

        # Evaluate Button
        self.evaluate_btn = QPushButton("Evaluate Aligner")
        self.evaluate_btn.setMinimumHeight(45)
        self.evaluate_btn.setStyleSheet("""
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
        self.evaluate_btn.clicked.connect(self.on_evaluate)
        layout.addWidget(self.evaluate_btn)

        # Status label
        self.status_label = QLabel("Ready")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("color: #7f8c8d; font-size: 12px; margin-top: 5px;")
        layout.addWidget(self.status_label)

        layout.addStretch()

    def browse_directory(self, line_edit):
        """Open a file dialog to select directory."""
        directory = QFileDialog.getExistingDirectory(
            self,
            "Select Directory",
            line_edit.text() if Path(line_edit.text()).exists() else str(Path.home()),
        )
        if directory:
            line_edit.setText(directory)

    def on_evaluate(self):
        """Start evaluation process."""
        paths = {
            "Reference Path": self.reference_path.text(),
            "Predicted Path": self.predicted_path.text(),
            "Output Path": self.output_path.text(),
        }

        if not validate_paths(self, paths):
            return

        method = self.method_dropdown.currentText()
        ref = self.reference_path.text()
        pred = self.predicted_path.text()
        out = self.output_path.text()

        self.status_label.setText("Evaluating...")
        self.status_label.setStyleSheet("color: #f39c12; font-size: 12px; margin-top: 5px;")
        self.evaluate_btn.setEnabled(False)

        self.worker = WorkerThread(lambda: self.evaluate_logic(method, ref, pred, out))
        self.worker.finished.connect(self.on_evaluation_finished)
        self.worker.start()

    def evaluate_logic(self, method, ref_path, pred_path, out_path):
        """Perform evaluation logic."""
        try:
            # Example evaluation logic (replace with real evaluation later)
            subprocess.run(
                f'python scripts/evaluate_aligner.py --method "{method}" '
                f'--reference "{ref_path}" --predicted "{pred_path}" --output "{out_path}"',
                shell=True,
                check=True,
            )
            return f"Evaluation completed successfully using {method}"
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Evaluation failed: {e}")

    def on_evaluation_finished(self, success, message):
        """Handle evaluation completion."""
        self.evaluate_btn.setEnabled(True)
        if success:
            self.status_label.setText("✓ " + message)
            self.status_label.setStyleSheet("color: #27ae60; font-size: 12px; margin-top: 5px;")
            QMessageBox.information(self, "Success", message)
        else:
            self.status_label.setText("✗ Error occurred")
            self.status_label.setStyleSheet("color: #e74c3c; font-size: 12px; margin-top: 5px;")
            QMessageBox.critical(self, "Error", message)
