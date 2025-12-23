"""
CSV Visualization Component

A PyQt6 widget for displaying CSV files in a themed table view with
search, filtering, and export capabilities.
"""

import csv
import os
from pathlib import Path
from typing import Any, Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


class CSVVisualizationWidget(QWidget):
    """
    A themed widget for visualizing CSV files with search and export functionality.

    Args:
        csv_path: Optional path to CSV file to load on initialization
        parent: Parent widget

    Example:
        >>> csv_widget = CSVVisualizationWidget("/path/to/data.csv")
        >>> layout.addWidget(csv_widget)
    """

    def __init__(self, csv_path: Optional[str] = None, parent=None):
        super().__init__(parent)
        self.csv_path = csv_path
        self.data: list[Any] = []
        self.headers: list[str] = []
        self.filtered_data: list[Any] = []

        self._init_ui()

        if csv_path:
            self.load_csv(csv_path)

    def _init_ui(self):
        """Initialize the user interface"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Main container
        container = QGroupBox("CSV Viewer")
        container.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 14px;
                color: #2c3e50;
                border: 2px solid #ecf0f1;
                border-radius: 8px;
                margin-top: 12px;
                padding: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 5px;
            }
        """)

        container_layout = QVBoxLayout()

        # Top bar with file info and controls
        top_bar = self._create_top_bar()
        container_layout.addLayout(top_bar)

        # Search bar
        search_bar = self._create_search_bar()
        container_layout.addLayout(search_bar)

        # Table widget
        self.table = QTableWidget()
        self.table.setAlternatingRowColors(True)
        self._style_table()
        container_layout.addWidget(self.table)

        # Stats bar
        self.stats_label = QLabel("No data loaded")
        self.stats_label.setStyleSheet("""
            QLabel {
                color: #7f8c8d;
                font-size: 12px;
                font-style: italic;
                padding: 5px;
            }
        """)
        container_layout.addWidget(self.stats_label)

        container.setLayout(container_layout)
        layout.addWidget(container)

    def _create_top_bar(self) -> QHBoxLayout:
        """Create the top bar with file info and action buttons"""
        top_layout = QHBoxLayout()

        # File path label
        self.file_label = QLabel("No file loaded")
        self.file_label.setStyleSheet("""
            QLabel {
                color: #34495e;
                font-weight: 600;
                font-size: 13px;
            }
        """)
        top_layout.addWidget(self.file_label)

        top_layout.addStretch()

        # Load button
        load_btn = QPushButton("Load CSV")
        load_btn.setFixedWidth(100)
        load_btn.setStyleSheet(self._button_style())
        load_btn.clicked.connect(self.browse_csv)
        top_layout.addWidget(load_btn)

        # Export button
        self.export_btn = QPushButton("Export")
        self.export_btn.setFixedWidth(80)
        self.export_btn.setEnabled(False)
        self.export_btn.setStyleSheet(self._button_style())
        self.export_btn.clicked.connect(self.export_filtered)
        top_layout.addWidget(self.export_btn)

        # Refresh button
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.setFixedWidth(80)
        self.refresh_btn.setEnabled(False)
        self.refresh_btn.setStyleSheet(self._button_style())
        self.refresh_btn.clicked.connect(self.refresh)
        top_layout.addWidget(self.refresh_btn)

        return top_layout

    def _create_search_bar(self) -> QHBoxLayout:
        """Create the search/filter bar"""
        search_layout = QHBoxLayout()

        search_label = QLabel("Search:")
        search_label.setStyleSheet("color: #2c3e50; font-weight: 500;")
        search_layout.addWidget(search_label)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Filter rows by any column value...")
        self.search_input.textChanged.connect(self.filter_data)
        self.search_input.setStyleSheet("""
            QLineEdit {
                padding: 6px;
                border: 2px solid #d0d0d0;
                border-radius: 4px;
                background-color: white;
            }
            QLineEdit:focus {
                border: 2px solid #3498db;
            }
        """)
        search_layout.addWidget(self.search_input, stretch=1)

        # Clear search button
        clear_btn = QPushButton("Clear")
        clear_btn.setFixedWidth(60)
        clear_btn.setStyleSheet(self._button_style())
        clear_btn.clicked.connect(self.clear_search)
        search_layout.addWidget(clear_btn)

        return search_layout

    def _style_table(self):
        """Apply theme-matching styles to the table"""
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

    def _button_style(self) -> str:
        """Return consistent button styling"""
        return """
            QPushButton {
                background-color: white;
                border: 1px solid #d0d0d0;
                border-radius: 4px;
                padding: 6px 12px;
                color: #333;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #f0f0f0;
                border-color: #3498db;
            }
            QPushButton:pressed {
                background-color: #e0e0e0;
            }
            QPushButton:disabled {
                background-color: #f5f5f5;
                color: #aaa;
                border-color: #e0e0e0;
            }
        """

    def load_csv(self, csv_path: str) -> bool:
        """
        Load a CSV file and display it in the table.

        Args:
            csv_path: Path to the CSV file

        Returns:
            True if successful, False otherwise
        """
        if not os.path.exists(csv_path):
            QMessageBox.warning(self, "File Not Found", f"The file '{csv_path}' does not exist.")
            return False

        try:
            with open(csv_path, "r", encoding="utf-8") as f:
                reader = csv.reader(f)
                rows = list(reader)

                if not rows:
                    QMessageBox.warning(self, "Empty File", "The CSV file is empty.")
                    return False

                self.headers = rows[0]
                self.data = rows[1:]
                self.filtered_data = self.data.copy()
                self.csv_path = csv_path

                self._populate_table()
                self._update_ui_state()

                return True

        except Exception as e:
            QMessageBox.critical(self, "Error Loading CSV", f"Failed to load CSV file:\n{str(e)}")
            return False

    def _populate_table(self):
        """Populate the table with current filtered data"""
        self.table.clear()
        self.table.setRowCount(len(self.filtered_data))
        self.table.setColumnCount(len(self.headers))
        self.table.setHorizontalHeaderLabels(self.headers)

        # Populate cells
        for row_idx, row_data in enumerate(self.filtered_data):
            for col_idx, cell_data in enumerate(row_data):
                item = QTableWidgetItem(str(cell_data))
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)  # Read-only
                self.table.setItem(row_idx, col_idx, item)

        # Auto-resize columns
        header = self.table.horizontalHeader()
        for i in range(len(self.headers)):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)

        # Make last column stretch
        if len(self.headers) > 0:
            header.setSectionResizeMode(len(self.headers) - 1, QHeaderView.ResizeMode.Stretch)

    def _update_ui_state(self):
        """Update UI elements based on current state"""
        if self.csv_path:
            filename = Path(self.csv_path).name
            self.file_label.setText(f"File: {filename}")
            self.export_btn.setEnabled(True)
            self.refresh_btn.setEnabled(True)

            total_rows = len(self.data)
            filtered_rows = len(self.filtered_data)
            cols = len(self.headers)

            if filtered_rows < total_rows:
                self.stats_label.setText(
                    f"Showing {filtered_rows} of {total_rows} rows | {cols} columns"
                )
            else:
                self.stats_label.setText(f"{total_rows} rows × {cols} columns")
        else:
            self.file_label.setText("No file loaded")
            self.export_btn.setEnabled(False)
            self.refresh_btn.setEnabled(False)
            self.stats_label.setText("No data loaded")

    def filter_data(self, search_text: str):
        """Filter table data based on search text"""
        if not search_text:
            self.filtered_data = self.data.copy()
        else:
            search_lower = search_text.lower()
            self.filtered_data = [
                row for row in self.data if any(search_lower in str(cell).lower() for cell in row)
            ]

        self._populate_table()
        self._update_ui_state()

    def clear_search(self):
        """Clear the search filter"""
        self.search_input.clear()

    def browse_csv(self):
        """Open file dialog to select a CSV file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select CSV File", "", "CSV Files (*.csv);;All Files (*)"
        )

        if file_path:
            self.load_csv(file_path)

    def refresh(self):
        """Reload the current CSV file"""
        if self.csv_path:
            self.load_csv(self.csv_path)
            self.search_input.clear()

    def export_filtered(self):
        """Export the currently filtered data to a new CSV file"""
        if not self.filtered_data:
            QMessageBox.information(self, "No Data", "No data to export.")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Filtered Data", "filtered_data.csv", "CSV Files (*.csv)"
        )

        if not file_path:
            return

        try:
            with open(file_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(self.headers)
                writer.writerows(self.filtered_data)

            QMessageBox.information(self, "Export Successful", f"Data exported to:\n{file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Export Failed", f"Failed to export data:\n{str(e)}")

    def get_data(self) -> list:
        """
        Get the current filtered data.

        Returns:
            List of rows (each row is a list of values)
        """
        return self.filtered_data.copy()

    def get_headers(self) -> list:
        """
        Get the CSV headers.

        Returns:
            List of column header names
        """
        return self.headers.copy()

    def set_data(self, headers: list, data: list):
        """
        Programmatically set data without loading from file.

        Args:
            headers: List of column header names
            data: List of rows (each row is a list of values)
        """
        self.headers = headers
        self.data = data
        self.filtered_data = data.copy()
        self.csv_path = None

        self._populate_table()
        self._update_ui_state()
