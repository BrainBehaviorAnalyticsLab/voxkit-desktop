"""
Datasets management page for registering, validating, and managing speech datasets.
"""


from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from voxkit.analyzers import ManageAnalyzers
from voxkit.gui.formatting import humanize_timestamp
from voxkit.gui.frameworks.settings_modal import (
    FieldConfig,
    FieldType,
    GenericDialog,
    SettingsConfig,
)
from voxkit.gui.workers import DatasetRegistrationWorker
from voxkit.storage.alignments import list_alignments
from voxkit.storage.datasets import (
    delete_dataset,
    export_dataset,
    import_dataset,
    list_datasets,
    update_dataset,
)

from .styles import Colors


class DatasetsPage(QWidget):
    """Main datasets management page"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.registration_worker = None
        self.selected_dataset = None
        self.init_ui()
        self.refresh_datasets()

    def init_ui(self):
        """Initialize the UI components"""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # Title
        title = QLabel("Dataset Management")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #2c3e50;")
        main_layout.addWidget(title)

        # Load available analysis methods
        self.analysis_methods = list(ManageAnalyzers.list_analyzers())

        # Add sections
        main_layout.addWidget(self._create_list_section())
        
        # Add alignments panel
        main_layout.addWidget(self._create_alignments_panel())
        
        # Add register section at bottom
        main_layout.addWidget(self._create_register_section())

        main_layout.setSpacing(20)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # === Footer Credit ===
        credit = QLabel("VoxKit by BrainBehaviorAnalyticsLab")
        credit.setStyleSheet("color: #999; font-size: 10px; padding: 5px;")
        credit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(credit)
    
    def _create_register_section(self):
        """Create the dataset registration section"""
        group = QGroupBox()
        layout = QVBoxLayout()
        
        # # Description text
        # desc_label = QLabel(
        #     "Register a new dataset by providing its path, name, and configuration options."
        # )
        # desc_label.setWordWrap(True)
        # desc_label.setStyleSheet("color: #7f8c8d; font-size: 12px; margin-bottom: 10px;")
        # layout.addWidget(desc_label)

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

        layout.addLayout(action_layout)

        group.setLayout(layout)
        return group
    
    def on_import(self):
        """Handle import button click to open registration dialog"""
        dir_path = QFileDialog.getExistingDirectory(
            self,
            "Select Directory to Save Exported Dataset",
            "",
            QFileDialog.Option.ShowDirsOnly,
        )

        if not dir_path:
            QMessageBox.warning(self, "No Destination Selected", "Please select a destination.")
            return

        success, message = import_dataset(dir_path)

        if success:
            QMessageBox.information(self, "Success", message)
            self.refresh_datasets()

        else:
            QMessageBox.critical(self, "Import Failed", message)
    
    def on_export(self):
        """Handle export button click for selected dataset"""   
        if not self.selected_dataset:
            QMessageBox.warning(self, "No Dataset Selected", "Please select a dataset to export.")
            return
        else:
            self._export_dataset(self.selected_dataset)

    def on_delete(self):
        """Handle delete button click for selected dataset"""
        pass
    
    def _create_list_section(self):
        """Create the dataset list section"""
        
        group = QGroupBox()
        layout = QVBoxLayout()
        
        # Add plus button at the top
        button_container = QWidget()
        button_container.setStyleSheet("background-color: transparent;")
        button_layout = QHBoxLayout(button_container)
        button_layout.setContentsMargins(0, 0, 0, 10)

        plus_btn = QPushButton("+ Register New Dataset")
        plus_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.INFO};
                color: white;
                border: none;
                border-radius: 5px;
                padding: 8px 16px;
                font-size: 13px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #2980b9;
            }}
            QPushButton:pressed {{
                background-color: #21618c;
            }}
        """)
        plus_btn.clicked.connect(self.open_registration_dialog)
        button_layout.addWidget(plus_btn)
        button_layout.addStretch()
        
        layout.addWidget(button_container)
        
        # Helper text
        helper_label = QLabel("💡 Select a dataset to view its alignments below")
        helper_label.setStyleSheet("""
            QLabel {
                color: #3498db;
                font-size: 12px;
                font-weight: 500;
                padding: 5px;
                background-color: #ebf5fb;
                border-left: 3px solid #3498db;
                border-radius: 3px;
            }
        """)
        layout.addWidget(helper_label)

        # Container for table and empty label
        list_container = QWidget()
        list_container_layout = QVBoxLayout(list_container)
        list_container_layout.setContentsMargins(0, 0, 0, 0)

        # Dataset table
        self.dataset_table = QTableWidget()
        self.dataset_table.setColumnCount(6)
        self.dataset_table.setHorizontalHeaderLabels(
            [
                "Name",
                "Description",
                "Cached",
                "De-identified",
                "Transcribed",
                "Registration Date",
                # "Actions",
            ]
        )

        # Configure table
        header = self.dataset_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        for i in range(2, 7):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.Fixed)
        self.dataset_table.setColumnWidth(7, 150)

        self.dataset_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.dataset_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.dataset_table.itemSelectionChanged.connect(self._on_dataset_selected)
        self.dataset_table.setAlternatingRowColors(True)
        self.dataset_table.setStyleSheet(
            """
            QTableWidget {
                gridline-color: #ecf0f1;
                background-color: white;
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

        list_container_layout.addWidget(self.dataset_table)

        # Add empty state label
        self.empty_label = QLabel(
            "No datasets registered yet.\n"
            "Use the form above to register your first dataset."
        )
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setStyleSheet("""
            QLabel {
                color: #7f8c8d;
                font-style: italic;
                font-size: 14px;
                padding: 40px;
            }
        """)
        self.empty_label.hide()  # Hidden by default
        list_container_layout.addWidget(self.empty_label)

        layout.addWidget(list_container)

        group.setLayout(layout)
        return group
    
    def _create_alignments_panel(self):
        """Create the alignments panel for selected dataset"""
        group = QGroupBox("↓ Alignments for Selected Dataset")
        group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #3498db;
                border-radius: 8px;
                margin-top: 12px;
                padding: 15px;
                background-color: #ebf5fb;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 5px;
                color: #2c3e50;
            }
        """)
        
        layout = QVBoxLayout()
        
        # Engine filter
        filter_layout = QHBoxLayout()
        filter_label = QLabel("Filter by Engine:")
        filter_label.setStyleSheet("color: #2c3e50; font-weight: 500;")
        filter_layout.addWidget(filter_label)
        
        self.engine_filter_combo = QComboBox()
        self.engine_filter_combo.addItem("All Engines")
        self.engine_filter_combo.setStyleSheet("""
            QComboBox {
                padding: 4px 8px;
                border: 2px solid #d0d0d0;
                border-radius: 4px;
                background-color: white;
                min-width: 150px;
            }
            QComboBox:hover {
                border: 2px solid #3498db;
            }
        """)
        self.engine_filter_combo.currentTextChanged.connect(self._filter_alignments)
        filter_layout.addWidget(self.engine_filter_combo)
        filter_layout.addStretch()
        layout.addLayout(filter_layout)
        
        # Alignments table
        self.alignments_table = QTableWidget()
        self.alignments_table.setColumnCount(5)
        self.alignments_table.setHorizontalHeaderLabels(
            ["Engine", "Model", "Date Aligned", "Status", "Actions"]
        )
        
        # Configure alignments table
        align_header = self.alignments_table.horizontalHeader()
        align_header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        align_header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        align_header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        align_header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        align_header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.alignments_table.setColumnWidth(4, 150)
        
        self.alignments_table.setAlternatingRowColors(True)
        self.alignments_table.setMaximumHeight(300)
        self.alignments_table.setStyleSheet("""
            QTableWidget {
                gridline-color: #ecf0f1;
                background-color: white;
                border: 1px solid #bdc3c7;
                border-radius: 4px;
            }
            QTableWidget::item {
                padding: 0px;
            }
            QHeaderView::section {
                background-color: #34495e;
                color: white;
                padding: 8px;
                font-weight: bold;
                border: none;
            }
        """)
        
        layout.addWidget(self.alignments_table)
        
        # Empty state for alignments
        self.alignments_empty_label = QLabel(
            "No alignments found for this dataset.\n"
            "Run alignment on this dataset to see results here."
        )
        self.alignments_empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.alignments_empty_label.setStyleSheet("""
            QLabel {
                color: #95a5a6;
                font-style: italic;
                font-size: 13px;
                padding: 30px;
            }
        """)
        self.alignments_empty_label.hide()
        layout.addWidget(self.alignments_empty_label)
        
        group.setLayout(layout)
        return group
    
    def _on_dataset_selected(self):
        """Handle dataset selection change"""
        selected_items = self.dataset_table.selectedItems()
        if not selected_items:
            self.selected_dataset = None
            self.alignments_info_label.setText("👆 Select a dataset above to view its alignments")
            self.alignments_table.setRowCount(0)
            self.alignments_empty_label.hide()
            return
        
        # Get dataset name from first column of selected row
        row = selected_items[0].row()
        dataset_name = self.dataset_table.item(row, 0).text()
        self.selected_dataset = dataset_name

        self._load_alignments(dataset_name)
    
    def _load_alignments(self, dataset_name: str):
        """Load alignments for the selected dataset"""
        # TODO: Implement actual alignment loading from storage
        # For now, show mock data
        mock_alignments = self.convert_alignments(dataset_name)
        
        # Populate engine filter (block signals to prevent recursion)
        engines = set([align["engine_id"] for align in mock_alignments])
        current_filter = self.engine_filter_combo.currentText()
        self.engine_filter_combo.blockSignals(True)
        self.engine_filter_combo.clear()
        self.engine_filter_combo.addItem("All Engines")
        self.engine_filter_combo.addItems(sorted(engines))
        self.engine_filter_combo.setCurrentText(current_filter)
        self.engine_filter_combo.blockSignals(False)
        
        self._display_alignments(mock_alignments)
    
    def _filter_alignments(self):
        """Filter alignments by selected engine"""
        if not self.selected_dataset:
            return
        self._load_alignments(self.selected_dataset)
    
    def _display_alignments(self, alignments: list):
        """Display alignments in the table"""
        # Filter by engine if selected
        engine_filter = self.engine_filter_combo.currentText()
        if engine_filter != "All Engines":
            alignments = [a for a in alignments if a["engine"] == engine_filter]
        
        if not alignments:
            self.alignments_table.hide()
            self.alignments_empty_label.show()
            return
        
        self.alignments_empty_label.hide()
        self.alignments_table.show()
        
        self.alignments_table.setRowCount(len(alignments))
        
        for row, alignment in enumerate(alignments):
            # Engine
            self.alignments_table.setItem(row, 0, QTableWidgetItem(alignment["engine_id"]))
            
            # Model (clickable)
            model_item = QTableWidgetItem(alignment["model_id"])
            model_item.setForeground(Qt.GlobalColor.blue)
            model_item.setToolTip("Click to view model details")
            font = model_item.font()
            font.setUnderline(True)
            model_item.setFont(font)
            self.alignments_table.setItem(row, 1, model_item)
            
            # Date Aligned
            self.alignments_table.setItem(row, 2, QTableWidgetItem(humanize_timestamp(alignment["alignment_date"])))
            
            # Status
            status_item = QTableWidgetItem(alignment.get("status", ""))
            if alignment.get("status") == "Complete":
                status_item.setForeground(Qt.GlobalColor.darkGreen)
            elif alignment.get("status")     == "Failed":
                status_item.setForeground(Qt.GlobalColor.red)
            self.alignments_table.setItem(row, 3, status_item)
            
            # Actions
            actions_widget = self._create_alignment_action_buttons(alignment)
            self.alignments_table.setCellWidget(row, 4, actions_widget)
        
        # Disconnect old connections and connect cell click for model column
        try:
            self.alignments_table.cellClicked.disconnect()
        except TypeError:
            # No connections exist yet
            pass
        self.alignments_table.cellClicked.connect(self._on_alignment_cell_clicked)
    
    def _on_alignment_cell_clicked(self, row: int, col: int):
        """Handle click on alignment table cell"""
        # If model column (col 1) is clicked
        if col == 1:
            model_name = self.alignments_table.item(row, 1).text()
            # TODO: Implement model details view
            QMessageBox.information(
                self,
                "Model Details",
                f"Model clicked: {model_name}\n\nModel details will be shown here."
            )
    
    def _create_alignment_action_buttons(self, alignment: dict):
        """Create action buttons for an alignment row"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(5, 2, 5, 2)
        layout.setSpacing(5)
        
        button_style = f"""
            QPushButton {{
                background-color: {Colors.SUCCESS};
                border: 1px solid #d0d0d0;
                border-radius: 5px;
                padding: 5px 10px;
                color: white;
            }}
            QPushButton:hover {{
                background-color: #229954;
            }}
            QPushButton:pressed {{
                background-color: #1e8449;
            }}
        """
        
        # Export button
        export_btn = QPushButton("Export")
        export_btn.setMaximumWidth(60)
        export_btn.setStyleSheet(button_style)
        export_btn.clicked.connect(lambda: self._export_alignment(alignment))
        layout.addWidget(export_btn)
        
        # Delete button
        delete_btn = QPushButton("Delete")
        delete_btn.setMaximumWidth(60)
        delete_btn.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 5px 10px;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
            QPushButton:pressed {
                background-color: #a93226;
            }
        """)
        delete_btn.clicked.connect(lambda: self._delete_alignment(alignment))
        layout.addWidget(delete_btn)
        
        return widget
    
    def convert_alignments(self, dataset_name: str) -> list:
        """Generate mock alignment data (to be replaced with actual data loading)"""
        data_set_alignments = list_alignments(dataset_name)
        return data_set_alignments
    
    def _view_alignment(self, alignment: dict):
        """View alignment details"""
        # TODO: Implement alignment details view
        QMessageBox.information(
            self,
            "Alignment Details",
            f"Engine: {alignment['engine']}\n"
            f"Model: {alignment['model']}\n"
            f"Date: {alignment['date_aligned']}\n"
            f"Status: {alignment['status']}"
        )
    
    def _export_alignment(self, alignment: dict):
        """Export alignment results"""
        # TODO: Implement alignment export
        QMessageBox.information(
            self,
            "Export Alignment",
            f"Export functionality for alignment '{alignment['model']}' will be implemented."
        )
    
    def _delete_alignment(self, alignment: dict):
        """Delete an alignment"""
        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to delete the alignment with model '{alignment['model']}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # TODO: Implement actual alignment deletion
            QMessageBox.information(
                self,
                "Deleted",
                f"Alignment '{alignment['model']}' deleted successfully."
            )
            # Refresh alignments list
            if self.selected_dataset:
                self._load_alignments(self.selected_dataset)

    def open_registration_dialog(self):
        """Open the dataset registration settings dialog"""
        # Create settings config
        config = SettingsConfig(
            title="Register New Dataset",
            dimensions=(500, 400),
            apply_blur=False,  # Disable blur to avoid parent issues
            store_file="dataset_registration_settings.json",
            fields=[
                FieldConfig(
                    name="dataset_path",
                    label="Dataset Path",
                    field_type=FieldType.LINEEDIT,
                    default_value="",
                    placeholder="Browse for dataset directory...",
                    tooltip="Root directory containing speaker subdirectories",
                ),
                FieldConfig(
                    name="dataset_name",
                    label="Dataset Name",
                    field_type=FieldType.LINEEDIT,
                    default_value="",
                    placeholder="e.g., timit_train",
                    tooltip="Unique identifier for this dataset",
                ),
                FieldConfig(
                    name="description",
                    label="Description",
                    field_type=FieldType.LINEEDIT,
                    default_value="",
                    placeholder="Semantic description of the dataset...",
                    tooltip="Brief description of the dataset purpose and contents",
                ),
                FieldConfig(
                    name="analysis_method",
                    label="Analysis Method",
                    field_type=FieldType.COMBOBOX,
                    default_value=self.analysis_methods[0] if self.analysis_methods else "Default",
                    options=self.analysis_methods,
                    tooltip="Select the analysis method for generating the dataset summary CSV",
                ),
                FieldConfig(
                    name="cache",
                    label="Cache Dataset",
                    field_type=FieldType.CHECKBOX,
                    default_value=False,
                    tooltip="Copy entire dataset to storage (recommended for remote datasets)",
                ),
                FieldConfig(
                    name="anonymize",
                    label="De-identify",
                    field_type=FieldType.CHECKBOX,
                    default_value=False,
                    tooltip="Mark dataset for anonymization during inference/training",
                ),
                FieldConfig(
                    name="transcribed",
                    label="Transcribed",
                    field_type=FieldType.CHECKBOX,
                    default_value=False,
                    tooltip="Mark as already containing transcriptions",
                ),
            ],
        )
        
        # Create and show dialog - pass self as parent
        dialog = GenericDialog(self, config=config)
        result = dialog.exec()
        
        if result == QDialog.DialogCode.Accepted:
            # Get values from dialog
            values = dialog.get_values()
            self.process_registration(values)

    def process_registration(self, values: dict):
        """Process the registration with values from the dialog"""
        dataset_path = values.get("dataset_path", "").strip()
        dataset_name = values.get("dataset_name", "").strip()
        description = values.get("description", "").strip()
        analysis_method = values.get("analysis_method", "Default")
        cache = values.get("cache", False)
        anonymize = values.get("anonymize", False)
        transcribed = values.get("transcribed", False)
        
        # Validation
        if not dataset_path:
            QMessageBox.warning(
                self, "Input Error", "Please provide a dataset path."
            )
            return
        
        if not dataset_name:
            QMessageBox.warning(
                self, "Input Error", "Please enter a dataset name."
            )
            return
        
        if not description:
            QMessageBox.warning(
                self, "Input Error", "Please enter a description."
            )
            return
        
        # Start registration in worker thread
        print(
            f"Starting dataset registration with params: {dataset_path}, {dataset_name}, "
            f"{description}, cache={cache}, anonymize={anonymize}, transcribed={transcribed}, "
            f"analysis_method={analysis_method}"
        )
        self.registration_worker = DatasetRegistrationWorker(
            dataset_path, dataset_name, description, cache, anonymize, transcribed, analysis_method
        )
        self.registration_worker.progress.connect(self.show_progress)
        self.registration_worker.finished.connect(self.registration_complete)
        self.registration_worker.start()

    def browse_dataset_path(self):
        """Open directory picker for dataset path"""
        directory = QFileDialog.getExistingDirectory(
            self, "Select Dataset Root Directory"
        )
        if directory:
            return directory
        return None

    def show_progress(self, message):
        """Show progress message"""
        print(message)

    def registration_complete(self, success, message):
        """Handle registration completion"""
        if success:
            QMessageBox.information(self, "Success", message)
            # Refresh list
            self.refresh_datasets()
        else:
            QMessageBox.critical(self, "Registration Failed", message)

    def refresh_datasets(self):
        """Refresh the dataset list"""
        datasets = list_datasets()

        # Show empty label if no datasets, otherwise show table
        if not datasets:
            self.dataset_table.hide()
            self.empty_label.show()
            self.empty_label.raise_()
            return
        else:
            self.empty_label.hide()
            self.dataset_table.show()

        self.dataset_table.setRowCount(len(datasets))

        for row, dataset in enumerate(datasets):
            # Name
            self.dataset_table.setItem(row, 0, QTableWidgetItem(dataset["name"]))

            # Description
            desc_item = QTableWidgetItem(dataset["description"])
            desc_item.setToolTip(dataset["description"])
            self.dataset_table.setItem(row, 1, desc_item)

            # Cached
            self.dataset_table.setItem(
                row, 2, QTableWidgetItem("Yes" if dataset["cached"] else "No")
            )

            # Anonymized
            self.dataset_table.setItem(
                row, 3, QTableWidgetItem("Yes" if dataset["anonymize"] else "No")
            )

            self.dataset_table.setItem(
                row, 4, QTableWidgetItem("Yes" if dataset.get("transcribed", False) else "No")
            )

            # Registration date
            reg_date = dataset.get("registration_date", "Unknown")
            if reg_date != "Unknown":
                reg_date = reg_date.split("T")[0]  # Show only date part
            self.dataset_table.setItem(row, 5, QTableWidgetItem(reg_date))

            # # Actions
            # actions_widget = self._create_action_buttons(dataset)
            # self.dataset_table.setCellWidget(row, 6, actions_widget)

    def _create_action_buttons(self, dataset):
        """Create action buttons for a dataset row"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(5, 2, 5, 2)
        layout.setSpacing(5)

        button_style = """
            QPushButton {
                background-color: white;
                border: 1px solid #d0d0d0;
                border-radius: 5px;
                padding: 5px 10px;
                color: #333;
            }
            QPushButton:hover {
                background-color: #f0f0f0;
                border-color: #b0b0b0;
            }
            QPushButton:pressed {
                background-color: #e0e0e0;
            }
        """
        
        # Export button
        export_btn = QPushButton("Export")
        export_btn.setMaximumWidth(60)
        export_btn.setStyleSheet(button_style)
        export_btn.clicked.connect(lambda: self._export_dataset(dataset))
        layout.addWidget(export_btn)
        
        # Delete button
        delete_btn = QPushButton("Delete")
        delete_btn.setMaximumWidth(60)
        delete_btn.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 5px 10px;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
            QPushButton:pressed {
                background-color: #a93226;
            }
        """)
        delete_btn.clicked.connect(lambda: self.delete_dataset(dataset))
        layout.addWidget(delete_btn)

        return widget

    def view_dataset(self, dataset):
        """Show detailed dataset information"""
        info_text = (
            f"Dataset: {dataset['name']}\n\n"
            f"Description: {dataset['description']}\n\n"
            f"Original Path: {dataset['original_path']}\n"
            f"Cached: {'Yes' if dataset['cached'] else 'No'}\n"
            f"Anonymized: {'Yes' if dataset['anonymize'] else 'No'}\n"
            f"Transcribed: {'Yes' if dataset.get('transcribed', False) else 'No'}\n\n"
            f"Registration Date: {dataset.get('registration_date', 'Unknown')}"
        )

        QMessageBox.information(self, "Dataset Information", info_text)

    def edit_dataset(self, dataset):
        """Edit dataset metadata"""
        from PyQt6.QtWidgets import QDialog, QDialogButtonBox

        dialog = QDialog(self)
        dialog.setWindowTitle(f"Edit Dataset: {dataset['name']}")
        dialog.setMinimumWidth(400)

        layout = QVBoxLayout(dialog)

        form_layout = QFormLayout()

        # Description
        desc_edit = QTextEdit()
        desc_edit.setPlainText(dataset["description"])
        desc_edit.setMaximumHeight(100)
        form_layout.addRow("Description:", desc_edit)

        # Anonymize
        anonymize_check = QCheckBox()
        anonymize_check.setChecked(dataset["anonymize"])
        form_layout.addRow("Anonymize:", anonymize_check)

        # Transcribed
        transcribed_check = QCheckBox()
        transcribed_check.setChecked(dataset.get("transcribed", False))
        form_layout.addRow("Transcribed:", transcribed_check)

        layout.addLayout(form_layout)

        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            success, message = update_dataset(
                dataset["name"],
                description=desc_edit.toPlainText().strip(),
                anonymize=anonymize_check.isChecked(),
                transcribed=transcribed_check.isChecked(),
            )

            if success:
                QMessageBox.information(self, "Success", message)
                self.refresh_datasets()
            else:
                QMessageBox.critical(self, "Update Failed", message)

    def transcribe_dataset(self, dataset):
        """Transcribe a dataset using available transcription engines"""
        # Check if already transcribed
        if dataset.get('transcribed', False):
            reply = QMessageBox.question(
                self,
                "Already Transcribed",
                f"Dataset '{dataset['name']}' is marked as transcribed.\n\n"
                "Do you want to transcribe it again?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
        
        # Placeholder for transcription functionality
        QMessageBox.information(
            self,
            "Transcription",
            f"Transcription feature for dataset '{dataset['name']}' will be implemented.\n\n"
            "This will use WhisperX or similar transcription engines to generate "
            "transcriptions for all audio files in the dataset.",
        )
        
        # TODO: Implement actual transcription logic here
        # - Check for available transcription engines (WhisperX, etc.)
        # - Show transcription settings dialog
        # - Run transcription in a worker thread
        # - Update dataset metadata with transcribed=True on success

    def _export_dataset(self, dataset):
        """Export dataset configuration"""
        # Prompt for directory path to save exported dataset 

        dir_path = QFileDialog.getExistingDirectory(
            self,
            "Select Directory to Save Exported Dataset",
            "",
            QFileDialog.Option.ShowDirsOnly,
        )

        if dir_path:
            success, message = export_dataset(dataset, dir_path)
            if success:
                QMessageBox.information(self, "Success", message)
            else:
                QMessageBox.critical(self, "Export Failed", message)

    def delete_dataset(self, dataset):
        """Delete a dataset"""
        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to delete dataset '{dataset['name']}'?\n\n"
            f"This will delete the metadata"
            + (
                " and all cached files."
                if dataset["cached"]
                else " (original files will not be affected)."
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            success, message = delete_dataset(
                dataset["name"], remove_cached_files=True
            )

            if success:
                QMessageBox.information(self, "Success", message)
                self.refresh_datasets()
            else:
                QMessageBox.critical(self, "Delete Failed", message)
