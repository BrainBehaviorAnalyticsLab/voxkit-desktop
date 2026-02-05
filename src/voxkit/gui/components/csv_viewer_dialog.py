"""CSV Viewer Dialog Module.

Modal dialog for viewing CSV files in a formatted table.

API
---
- **CSVViewerDialog**: Dialog that displays CSV data with blur background effect
"""

import csv
import os
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QGraphicsBlurEffect,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from voxkit.gui.styles import Buttons, Containers, Labels


class CSVViewerDialog(QDialog):
    """
    A dialog for displaying CSV files in a formatted table view.

    Args:
        csv_path: Path to the CSV file to display
        parent: Parent widget for the dialog
    """

    def __init__(self, csv_path: str, parent=None, visualization=None):
        super().__init__(parent)
        self.csv_path = csv_path
        self.visualization = visualization
        self.setWindowTitle("Dataset Analysis Details")
        self.setModal(True)
        self.resize(800, 600)

        # Apply blur effect to parent if provided
        if parent:
            self.blur_effect = QGraphicsBlurEffect()
            self.blur_effect.setBlurRadius(10)
            parent.setGraphicsEffect(self.blur_effect)

        self.parent = parent
        self._init_ui()
        if not self.visualization:
            self._load_csv()

    def _init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # Header with file name
        filename = Path(self.csv_path).name
        header_label = QLabel(f"📊 {filename}")
        header_label.setStyleSheet(Labels.HEADER)
        layout.addWidget(header_label)

        if self.visualization:
            layout.addWidget(self.visualization)
        else:
            # Table widget
            self.table = QTableWidget()
            self.table.setAlternatingRowColors(True)
            self.table.setStyleSheet(Containers.TABLE_WIDGET)
            layout.addWidget(self.table)

            # Stats label
            self.stats_label = QLabel()
            self.stats_label.setStyleSheet(Labels.STATS)
            layout.addWidget(self.stats_label)

        # Close button
        close_btn = QPushButton("Close")
        close_btn.setFixedWidth(100)
        close_btn.setStyleSheet(Buttons.PRIMARY)
        close_btn.clicked.connect(self.reject)
        layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignCenter)

    def _load_csv(self):
        """Load and display the CSV file."""
        if not os.path.exists(self.csv_path):
            self.stats_label.setText("❌ CSV file not found")
            return

        try:
            with open(self.csv_path, "r", encoding="utf-8") as f:
                reader = csv.reader(f)
                rows = list(reader)

                if not rows:
                    self.stats_label.setText("❌ CSV file is empty")
                    return

                # Set headers
                headers = rows[0]
                data = rows[1:]

                self.table.setRowCount(len(data))
                self.table.setColumnCount(len(headers))
                self.table.setHorizontalHeaderLabels(headers)

                # Populate cells
                for row_idx, row_data in enumerate(data):
                    for col_idx, cell_data in enumerate(row_data):
                        item = QTableWidgetItem(str(cell_data))
                        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)  # Read-only
                        self.table.setItem(row_idx, col_idx, item)

                # Auto-resize columns
                header = self.table.horizontalHeader()
                for i in range(len(headers)):
                    header.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)

                # Make last column stretch
                if len(headers) > 0:
                    header.setSectionResizeMode(len(headers) - 1, QHeaderView.ResizeMode.Stretch)

                # Update stats
                self.stats_label.setText(f"✅ {len(data)} rows × {len(headers)} columns")

        except Exception as e:
            self.stats_label.setText(f"❌ Error loading CSV: {str(e)}")

    def closeEvent(self, event):
        """Handle dialog close event to remove blur effect."""
        print("Dialog closed, removing blur effect from parent")
        if self.parent:
            print("Removing blur effect from parent")
            self.parent.setGraphicsEffect(None)
        event.accept()

    def reject(self):
        """Handle dialog rejection to remove blur effect."""
        if self.parent:
            print("Removing blur effect from parent")
            self.parent.setGraphicsEffect(None)
        super().reject()
