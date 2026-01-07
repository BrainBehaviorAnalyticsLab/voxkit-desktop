from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from voxkit.gui.components import HuggingFaceButton
from voxkit.gui.frameworks._______.styles import Buttons, Colors, Labels


class CategoricalTableWidget(QWidget):
    """Widget for viewing and managing categorical data in table format"""

    def __init__(
        self,
        refresh_data_function,
        export_function,
        import_function,
        delete_function,
        columns_shown=None,
        single_selection_flag=False,
        huggingface_callback=None,
        parent=None,
    ):
        """
        Initialize the CategoricalTableWidget.

        Args:
            refresh_data_function: Callable that returns dict of categorical data
            export_function: Callable(category: str, items: list[dict])
                -> (success: bool, message: str)
            import_function: Callable(category: str) -> (success: bool, message: str)
            delete_function: Callable(category: str, items: list[dict])
                -> (success: bool, message: str)
            columns_shown: Optional list of column names to display
            single_selection_flag: If True, only one item can be selected at a time
                (default: False)
            huggingface_callback: Optional callback for HuggingFace button click
            parent: Parent widget
        """
        super().__init__(parent)
        self.refresh_data_function = refresh_data_function
        self.export_function = export_function
        self.import_function = import_function
        self.delete_function = delete_function
        self.columns_shown = columns_shown if columns_shown else []
        self.single_selection_flag = single_selection_flag
        self.huggingface_callback = huggingface_callback
        self.current_category_index = 0

        # Initialize data
        self.data = {}
        self.category_keys = []

        self.init_ui()
        self.refresh_data()
        self.update_display()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # Title header with optional HuggingFace button
        header_layout = QHBoxLayout()

        title = QLabel("Model Management")
        title.setStyleSheet(Labels.TITLE)
        header_layout.addWidget(title)

        # Add HuggingFace button if callback provided
        if self.huggingface_callback:
            header_layout.addStretch()
            self.hf_button = HuggingFaceButton(title="Browse Models")
            self.hf_button.clicked.connect(self.huggingface_callback)
            header_layout.addWidget(self.hf_button)

        main_layout.addLayout(header_layout)

        main_layout.addSpacing(10)

        # Category navigation section
        nav_layout = QHBoxLayout()
        nav_layout.setSpacing(10)

        self.prev_btn = QPushButton("← Previous")
        self.prev_btn.setStyleSheet(Buttons.SECONDARY)
        self.prev_btn.clicked.connect(self.prev_category)
        nav_layout.addWidget(self.prev_btn)

        self.category_label = QLabel("Category")
        self.category_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.category_label.setStyleSheet(f"""
            QLabel {{
                font-size: 16px;
                font-weight: bold;
                color: {Colors.TEXT_PRIMARY};
                background-color: white;
                padding: 8px 16px;
                border: 1px solid {Colors.BORDER};
                border-radius: 5px;
            }}
        """)
        nav_layout.addWidget(self.category_label, stretch=1)

        self.next_btn = QPushButton("Next →")
        self.next_btn.setStyleSheet(Buttons.SECONDARY)
        self.next_btn.clicked.connect(self.next_category)
        nav_layout.addWidget(self.next_btn)

        main_layout.addLayout(nav_layout)

        # Selection controls
        selection_layout = QHBoxLayout()
        selection_layout.setSpacing(10)

        self.select_all_btn = QPushButton("Select All")
        self.select_all_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: white;
                color: {Colors.TEXT_SECONDARY};
                border: 1px solid {Colors.GRAY};
                border-radius: 5px;
                padding: 6px 12px;
                font-size: 13px;
            }}
            QPushButton:hover {{
                background-color: {Colors.LIGHT_GRAY};
                border-color: {Colors.PRIMARY};
                color: {Colors.PRIMARY};
            }}
        """)
        self.select_all_btn.clicked.connect(self.select_all)
        selection_layout.addWidget(self.select_all_btn)

        self.deselect_all_btn = QPushButton("Deselect All")
        self.deselect_all_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: white;
                color: {Colors.TEXT_SECONDARY};
                border: 1px solid {Colors.GRAY};
                border-radius: 5px;
                padding: 6px 12px;
                font-size: 13px;
            }}
            QPushButton:hover {{
                background-color: {Colors.LIGHT_GRAY};
                border-color: {Colors.PRIMARY};
                color: {Colors.PRIMARY};
            }}
        """)
        self.deselect_all_btn.clicked.connect(self.deselect_all)
        selection_layout.addWidget(self.deselect_all_btn)

        selection_layout.addStretch()

        # Hide selection buttons if single selection mode
        if self.single_selection_flag:
            self.select_all_btn.hide()
            self.deselect_all_btn.hide()

        main_layout.addLayout(selection_layout)

        # Models group box (similar to datasets alignments panel)
        models_group = QGroupBox("Models")
        models_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #3498db;
                border-radius: 8px;
                margin-top: 12px;
                padding: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 5px;
                color: #2c3e50;
            }
        """)
        table_container_layout = QVBoxLayout(models_group)
        table_container_layout.setContentsMargins(10, 10, 10, 10)

        # Table widget
        self.table_widget = QTableWidget()
        self.table_widget.setAlternatingRowColors(True)
        self.table_widget.setStyleSheet(
            """
            QTableWidget {
                gridline-color: #ecf0f1;
                background-color: white;
                border: 1px solid #bdc3c7;
                border-radius: 4px;
            }
            QTableWidget::item {
                padding: 0px;
            }
            QTableWidget::item:hover {
                background-color: #e8f4f8;
            }
            QTableWidget::item:selected {
                background-color: #3498db;
                color: white;
            }
            QHeaderView::section {
                background-color: #34495e;
                color: white;
                padding: 8px;
                font-weight: bold;
                border: none;
            }
        """
        )

        # Configure table
        self.table_widget.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        # Set selection mode based on single_selection_flag
        if self.single_selection_flag:
            self.table_widget.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        else:
            self.table_widget.setSelectionMode(QTableWidget.SelectionMode.MultiSelection)

        # Set minimum height to prevent layout shifts
        self.table_widget.setMinimumHeight(200)
        table_container_layout.addWidget(self.table_widget)

        main_layout.addWidget(models_group, stretch=1)

        # Action group
        group = QGroupBox()

        # Action buttons
        action_layout = QHBoxLayout()
        action_layout.setSpacing(10)

        self.import_btn = QPushButton("Import")
        self.import_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: white;
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.GRAY};
                border-radius: 5px;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: bold;
                min-height: 35px;
            }}
            QPushButton:hover {{
                background-color: {Colors.LIGHT_GRAY};
                border-color: {Colors.INFO};
                color: {Colors.INFO};
            }}
            QPushButton:pressed {{
                background-color: {Colors.DARK_GRAY};
            }}
        """)
        self.import_btn.clicked.connect(self.on_import)
        action_layout.addWidget(self.import_btn)

        self.export_btn = QPushButton("Export Selected")
        self.export_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.SUCCESS};
                color: white;
                border: none;
                border-radius: 5px;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: bold;
                min-height: 35px;
            }}
            QPushButton:hover {{
                background-color: #229954;
            }}
            QPushButton:pressed {{
                background-color: #1e8449;
            }}
        """)
        self.export_btn.clicked.connect(self.on_export)
        action_layout.addWidget(self.export_btn)

        self.delete_btn = QPushButton("Delete Selected")
        self.delete_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.ERROR};
                color: white;
                border: none;
                border-radius: 5px;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: bold;
                min-height: 35px;
            }}
            QPushButton:hover {{
                background-color: #c0392b;
            }}
            QPushButton:pressed {{
                background-color: #a93226;
            }}
        """)
        self.delete_btn.clicked.connect(self.on_delete)
        action_layout.addWidget(self.delete_btn)

        group.setLayout(action_layout)
        main_layout.addWidget(group)

    def refresh_data(self):
        """Refresh data by calling the refresh_data_function"""
        try:
            self.data = self.refresh_data_function()
            self.category_keys = list(self.data.keys())
            # Ensure current index is still valid
            if self.current_category_index >= len(self.category_keys):
                self.current_category_index = max(0, len(self.category_keys) - 1)
        except Exception as e:
            QMessageBox.critical(
                self,
                "Data Refresh Error",
                f"Failed to refresh data: {str(e)}",
                QMessageBox.StandardButton.Ok,
            )
            self.data = {}
            self.category_keys = []

    def set_data(self, data, columns_shown=None):
        """Update the widget with new data (legacy method for compatibility)"""
        self.data = data
        self.category_keys = list(self.data.keys())
        self.current_category_index = 0
        if columns_shown:
            self.columns_shown = columns_shown
        self.update_display()

    def update_display(self):
        """Update the display for the current category"""
        self.table_widget.clear()
        self.table_widget.setRowCount(0)

        if not self.category_keys:
            self.category_label.setText("No Categories")
            self.prev_btn.setEnabled(False)
            self.next_btn.setEnabled(False)
            # Show empty table with no columns
            self.table_widget.setColumnCount(0)
            return

        # Update category label
        current_category = self.category_keys[self.current_category_index]
        category_display = (
            f"{current_category} ({self.current_category_index + 1}/{len(self.category_keys)})"
        )
        self.category_label.setText(category_display)

        # Update navigation buttons
        self.prev_btn.setEnabled(self.current_category_index > 0)
        self.next_btn.setEnabled(self.current_category_index < len(self.category_keys) - 1)

        # Get category data
        category_data = self.data[current_category]

        if not category_data:
            # Show empty table - just set up columns but no rows
            # Will still show headers if columns were previously shown
            pass

        # Determine columns to show
        if not self.columns_shown:
            # Auto-detect columns from first few items
            all_keys = set()
            for item in category_data[:5]:  # Sample first 5 items
                if isinstance(item, dict):
                    all_keys.update(item.keys())
            self.columns_shown = sorted(list(all_keys))

        # Set up table
        display_columns = self.columns_shown + ["Actions"]
        self.table_widget.setRowCount(len(category_data))
        self.table_widget.setColumnCount(len(display_columns))
        self.table_widget.setHorizontalHeaderLabels(display_columns)

        # Populate table
        for row_idx, item_data in enumerate(category_data):
            # Data columns
            for col_idx, column_name in enumerate(self.columns_shown):
                value = (
                    item_data.get(column_name, "Unknown")
                    if isinstance(item_data, dict)
                    else "Unknown"
                )
                table_item = QTableWidgetItem(str(value))
                table_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table_widget.setItem(row_idx, col_idx, table_item)

            # View button in centered container
            button_container = QWidget()
            button_layout = QHBoxLayout(button_container)
            button_layout.setContentsMargins(0, 0, 0, 0)
            button_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

            view_btn = QPushButton("View")
            view_btn.setFixedSize(60, 24)
            view_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {Colors.BG_SECONDARY};
                    border: 1px solid {Colors.GRAY};
                    border-radius: 6px;
                    font-size: 12px;
                    font-weight: bold;
                    color: {Colors.TEXT_SECONDARY};
                }}
                QPushButton:hover {{
                    background-color: {Colors.LIGHT_GRAY};
                    color: {Colors.PRIMARY};
                    border-color: {Colors.PRIMARY};
                }}
            """)
            view_btn.clicked.connect(lambda checked, idx=row_idx: self.view_item_details(idx))
            button_layout.addWidget(view_btn)
            self.table_widget.setCellWidget(row_idx, len(self.columns_shown), button_container)

        # Configure column widths for optimal stretching
        header = self.table_widget.horizontalHeader()
        # Make data columns resize to contents or stretch
        for i in range(len(self.columns_shown)):
            if i == 0:
                # First column: resize to contents
                header.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)
            else:
                # Other data columns: stretch
                header.setSectionResizeMode(i, QHeaderView.ResizeMode.Stretch)
        # Actions column: fixed width
        header.setSectionResizeMode(len(self.columns_shown), QHeaderView.ResizeMode.Fixed)
        self.table_widget.setColumnWidth(len(self.columns_shown), 80)

    def view_item_details(self, row_index):
        """Show all details for an item"""
        if not self.category_keys:
            return

        current_category = self.category_keys[self.current_category_index]
        category_data = self.data[current_category]

        if 0 <= row_index < len(category_data):
            item_data = category_data[row_index]
            self.show_detail_dialog(item_data, row_index)

    def show_detail_dialog(self, item_data, row_index):
        """Show a dialog with all fields from the item"""
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Item Details - Row {row_index + 1}")
        dialog.setMinimumWidth(450)
        dialog.setMinimumHeight(350)

        layout = QVBoxLayout(dialog)

        # Title
        title = QLabel(f"All Fields for Row {row_index + 1}")
        title.setStyleSheet(f"""
            QLabel {{
                font-size: 14px;
                font-weight: bold;
                color: {Colors.TEXT_PRIMARY};
                padding: 10px;
                background-color: {Colors.BG_SECONDARY};
                border-radius: 5px;
            }}
        """)
        layout.addWidget(title)

        # Create scrollable area for fields
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"""
            QScrollArea {{
                border: 1px solid {Colors.BORDER};
                border-radius: 5px;
                background-color: white;
            }}
        """)

        # Container for form layout
        container = QWidget()
        form_layout = QFormLayout(container)
        form_layout.setSpacing(10)
        form_layout.setContentsMargins(10, 10, 10, 10)

        # Add all fields
        if isinstance(item_data, dict):
            sorted_keys = sorted(item_data.keys())

            for key in sorted_keys:
                value = item_data[key]

                # Key label
                key_label = QLabel(f"{key}:")
                key_label.setStyleSheet(f"""
                    QLabel {{
                        font-weight: bold;
                        color: {Colors.TEXT_SECONDARY};
                        min-width: 120px;
                    }}
                """)

                # Value label
                value_label = QLabel(str(value))
                value_label.setWordWrap(True)
                value_label.setStyleSheet(f"""
                    QLabel {{
                        color: {Colors.TEXT_PRIMARY};
                        background-color: {Colors.BG_SECONDARY};
                        padding: 8px;
                        border-radius: 3px;
                        border: 1px solid {Colors.BORDER};
                    }}
                """)

                form_layout.addRow(key_label, value_label)

        scroll.setWidget(container)
        layout.addWidget(scroll)

        # Close button
        close_btn = QPushButton("Close")
        close_btn.setStyleSheet(Buttons.SECONDARY)
        close_btn.clicked.connect(dialog.close)

        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(close_btn)
        layout.addLayout(button_layout)

        dialog.exec()

    def prev_category(self):
        """Navigate to previous category"""
        if self.current_category_index > 0:
            self.current_category_index -= 1
            self.update_display()

    def next_category(self):
        """Navigate to next category"""
        if self.current_category_index < len(self.category_keys) - 1:
            self.current_category_index += 1
            self.update_display()

    def select_all(self):
        """Select all items in the current table"""
        if self.single_selection_flag:
            return  # Not applicable in single selection mode

        self.table_widget.selectAll()

    def deselect_all(self):
        """Deselect all items in the current table"""
        self.table_widget.clearSelection()

    def get_selected_items(self):
        """Get list of selected items"""
        selected = []
        if not self.category_keys:
            return selected

        current_category = self.category_keys[self.current_category_index]
        category_data = self.data[current_category]

        # Get selected rows from table
        selected_rows = self.table_widget.selectionModel().selectedRows()
        for index in selected_rows:
            row = index.row()
            if row < len(category_data):
                selected.append(category_data[row])

        return selected

    def set_items(self, mode, items):
        """Set the items for a specific category"""
        if mode not in self.data:
            self.data[mode] = []
        self.data[mode] = items
        self.update_display()

    def on_export(self):
        """Handle export button click"""
        selected_items = self.get_selected_items()

        if not selected_items:
            QMessageBox.warning(
                self,
                "No Selection",
                "Please select at least one item to export.",
                QMessageBox.StandardButton.Ok,
            )
            return

        current_category = self.category_keys[self.current_category_index]

        try:
            success, message = self.export_function(current_category, selected_items)
            if not message:
                return
            if success:
                QMessageBox.information(
                    self,
                    "Export Successful",
                    message,
                    QMessageBox.StandardButton.Ok,
                )
            else:
                QMessageBox.warning(
                    self,
                    "Export Failed",
                    message,
                    QMessageBox.StandardButton.Ok,
                )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Export Error",
                f"An error occurred during export: {str(e)}",
                QMessageBox.StandardButton.Ok,
            )

    def on_delete(self):
        """Handle delete button click"""
        selected_items = self.get_selected_items()

        if not selected_items:
            QMessageBox.warning(
                self,
                "No Selection",
                "Please select at least one item to delete.",
                QMessageBox.StandardButton.Ok,
            )
            return

        # Confirm deletion
        reply = QMessageBox.question(
            self,
            "Confirm Deletion",
            f"Are you sure you want to delete {len(selected_items)} item(s)?\n\n"
            "This action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            current_category = self.category_keys[self.current_category_index]

            try:
                success, message = self.delete_function(current_category, selected_items)

                if not message:
                    return

                if success:
                    # Refresh data after successful deletion
                    self.refresh_data()
                    self.update_display()

                    QMessageBox.information(
                        self,
                        "Deletion Successful",
                        message,
                        QMessageBox.StandardButton.Ok,
                    )
                else:
                    QMessageBox.warning(
                        self,
                        "Deletion Failed",
                        message,
                        QMessageBox.StandardButton.Ok,
                    )
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Deletion Error",
                    f"An error occurred during deletion: {str(e)}",
                    QMessageBox.StandardButton.Ok,
                )

    def on_import(self):
        """Handle import button click"""
        if not self.category_keys:
            QMessageBox.warning(
                self,
                "No Category",
                "No categories available for import.",
                QMessageBox.StandardButton.Ok,
            )
            return

        current_category = self.category_keys[self.current_category_index]

        try:
            success, message = self.import_function(current_category)

            if not message:
                return
            if success:
                # Refresh data after successful import
                self.refresh_data()
                self.update_display()

                QMessageBox.information(
                    self,
                    "Import Successful",
                    message,
                    QMessageBox.StandardButton.Ok,
                )
            else:
                QMessageBox.warning(
                    self,
                    "Import Failed",
                    message,
                    QMessageBox.StandardButton.Ok,
                )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Import Error",
                f"An error occurred during import: {str(e)}",
                QMessageBox.StandardButton.Ok,
            )


# Example usage
if __name__ == "__main__":
    import sys

    from PyQt6.QtWidgets import QApplication

    app = QApplication(sys.argv)

    # Sample data - now each category contains a list of dictionaries
    sample_data = {
        "MFA Models": [
            {
                "name": "english_us_arpa",
                "model_path": "/models/mfa/english_us_arpa",
                "download_date": "2025-01-15",
                "size": "125MB",
            },
            {
                "name": "german_mfa",
                "model_path": "/models/mfa/german_mfa",
                "download_date": "2025-02-20",
                "size": "98MB",
            },
            {
                "name": "french_prosodylab",
                "model_path": "/models/mfa/french_prosodylab",
                "download_date": "2025-03-10",
                "size": "110MB",
            },
        ],
        "W2TG Models": [
            {
                "name": "charsiu_en",
                "model_path": "/models/w2tg/charsiu_en",
                "download_date": "2025-04-05",
                "version": "1.0",
            },
            {
                "name": "custom_model_v1",
                "model_path": "/models/w2tg/custom_v1",
                "download_date": "2025-05-12",
                "version": "1.1",
            },
            {
                "name": "custom_model_v2",
                "model_path": "/models/w2tg/custom_v2",
                "download_date": "2025-06-18",
                "version": "2.0",
            },
        ],
        "Dictionaries": [
            {
                "name": "english_us",
                "path": "/dicts/en_us.dict",
                "download_date": "2025-01-01",
                "entries": "50000",
            },
            {
                "name": "german",
                "path": "/dicts/de.dict",
                "download_date": "2025-02-01",
                "entries": "45000",
            },
        ],
    }

    # Example callback functions
    def refresh_data():
        """Simulates fetching data from a database or API"""
        print("Refreshing data...")
        return sample_data

    def export_function(category, items):
        """Simulates exporting items"""
        print(f"Exporting {len(items)} items from category '{category}':")
        for item in items:
            print(f"  - {item}")
        return True, f"Successfully exported {len(items)} item(s) from '{category}'"

    def import_function(category):
        """Simulates importing items"""
        print(f"Importing items into category '{category}'")
        # In real usage, this would add items to the data source
        return True, f"Successfully imported items into '{category}'"

    def delete_function(category, items):
        """Simulates deleting items"""
        print(f"Deleting {len(items)} items from category '{category}':")
        for item in items:
            print(f"  - {item}")
        # In real usage, this would remove items from the data source
        return True, f"Successfully deleted {len(items)} item(s) from '{category}'"

    # Specify which columns to show (or leave None to auto-detect)
    columns_shown = ["name", "download_date"]

    # Create widget with single selection mode disabled (multi-select)
    widget = CategoricalTableWidget(
        refresh_data_function=refresh_data,
        export_function=export_function,
        import_function=import_function,
        delete_function=delete_function,
        columns_shown=columns_shown,
        single_selection_flag=False,  # Set to True to enable single selection mode
    )

    widget.setWindowTitle("Model Manager - Table View")
    widget.resize(800, 600)
    widget.show()

    sys.exit(app.exec())
