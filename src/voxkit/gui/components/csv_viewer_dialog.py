"""
CSV Viewer Dialog Component

A blurred popup dialog for viewing CSV files in a formatted table.
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


class CSVViewerDialog(QDialog):
    """
    A dialog for displaying CSV files in a formatted table view.

    Args:
        csv_path: Path to the CSV file to display
        parent: Parent widget for the dialog
    """

    def __init__(self, csv_path: str, parent=None):
        super().__init__(parent)
        self.csv_path = csv_path
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
        self._load_csv()

    def _init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # Header with file name
        filename = Path(self.csv_path).name
        header_label = QLabel(f"📊 {filename}")
        header_label.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: bold;
                color: #2c3e50;
                padding: 10px;
            }
        """)
        layout.addWidget(header_label)

        # Table widget
        self.table = QTableWidget()
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet("""
            QTableWidget {
                gridline-color: #ecf0f1;
                background-color: white;
                border: 1px solid #bdc3c7;
                border-radius: 4px;
                selection-background-color: #3498db;
                selection-color: white;
            }
            QTableWidget::item {
                padding: 8px;
                border-bottom: 1px solid #ecf0f1;
            }
            QTableWidget::item:selected {
                background-color: #3498db;
                color: white;
            }
            QHeaderView::section {
                background-color: #34495e;
                color: white;
                padding: 10px;
                font-weight: bold;
                border: none;
                border-right: 1px solid #2c3e50;
            }
            QHeaderView::section:last {
                border-right: none;
            }
            QTableWidget::item:alternate {
                background-color: #f8f9fa;
            }
        """)
        layout.addWidget(self.table)

        # Stats label
        self.stats_label = QLabel()
        self.stats_label.setStyleSheet("""
            QLabel {
                color: #7f8c8d;
                font-size: 12px;
                font-style: italic;
                padding: 5px;
            }
        """)
        layout.addWidget(self.stats_label)

        # Close button
        close_btn = QPushButton("Close")
        close_btn.setFixedWidth(100)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 8px 16px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:pressed {
                background-color: #21618c;
            }
        """)
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
