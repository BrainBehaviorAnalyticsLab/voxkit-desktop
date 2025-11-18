"""
Datasets management page for registering, validating, and managing speech datasets.
"""

import os

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from voxkit.analyzers import ManageAnalyzers
from voxkit.storage.datasets import (
    create_dataset,
    delete_dataset,
    export_dataset_config,
    get_datasets_root,
    list_datasets,
    update_dataset,
    validate_kaldi_dataset,
)


class DatasetRegistrationWorker(QThread):
    """Worker thread for dataset registration to avoid blocking the UI"""

    finished = pyqtSignal(bool, str)
    progress = pyqtSignal(str)

    def __init__(
        self, dataset_path, dataset_name, description, cache, anonymize, analysis_method
    ):
        super().__init__()
        self.dataset_path = dataset_path
        self.dataset_name = dataset_name
        self.description = description
        self.cache = cache
        self.anonymize = anonymize
        self.analysis_method = analysis_method

    def run(self):
        self.progress.emit("Validating dataset structure...")
        
        # First validate the dataset
        success = validate_kaldi_dataset(self.dataset_path)
        
        if not success:
            self.finished.emit(False, " Dataset validation failed. " \
            "Please ensure the dataset follows the Kaldi organization pattern.")
            return
        
        success, message = create_dataset(
            name=self.dataset_name,
            description=self.description,
            original_path=self.dataset_path,
            cached=self.cache,
            anonymize=self.anonymize,
        )

        if not success:
            self.finished.emit(False, message)
            return  
        else:
            self.progress.emit("Dataset metadata created successfully.")
        
        # Determine output path for CSV file
        dataset_dir = os.path.join(get_datasets_root(), self.dataset_name)

        csv_path = os.path.join(dataset_dir, f"{self.analysis_method.lower()}_summary.csv")
        
        csv_data = ManageAnalyzers.get_analyzers()[self.analysis_method].analyze(
            self.dataset_path
        )

        csv_success, csv_message = self._save_csv(csv_data, csv_path)
        
        if not csv_success:
            self.finished.emit(True, f"Warning: {csv_message}")
        else:
            self.finished.emit(True, csv_message)


    def _save_csv(self, data: list[dict], path: str) -> tuple[bool, str]:
        """
        Save the analysis data to a CSV file.

        Args:
            data: List of dictionaries where each dictionary represents a row.
            path: Output path for the CSV file.    
        Returns:
            Tuple of (success, message) where success is True if the file was saved successfully.
        """
        import csv

        if not os.path.exists(os.path.dirname(path)):
            return False, "Expected directory does not exist: " + os.path.dirname(path)

        try:
            with open(path, "w", newline="", encoding="utf-8") as csvfile:
                if not data:
                    return False, "No data to write to CSV."

                fieldnames = data[0].keys()
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                for row in data:
                    writer.writerow(row)
            return True, f"CSV saved successfully to {path}."
        except Exception as e:
            return False, f"Failed to save CSV: {e}"


class DatasetsPage(QWidget):
    """Main datasets management page"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.registration_worker = None
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
        main_layout.addWidget(self._create_register_section())
        main_layout.addWidget(self._create_validate_section())
        main_layout.addWidget(self._create_list_section())

    def _create_register_section(self):
        """Create the dataset registration section"""
        group = QGroupBox("Register New Dataset")
        layout = QVBoxLayout()

        form_layout = QFormLayout()

        # Dataset path selection
        path_layout = QHBoxLayout()
        self.dataset_path_input = QLineEdit()
        self.dataset_path_input.setPlaceholderText("Select dataset root directory...")
        browse_btn = QPushButton("Browse...")
        browse_btn.setStyleSheet("""
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
        """)
        browse_btn.clicked.connect(self.browse_dataset_path)
        path_layout.addWidget(self.dataset_path_input, stretch=1)
        path_layout.addWidget(browse_btn)
        form_layout.addRow("Dataset Path:", path_layout)

        # Dataset name
        self.dataset_name_input = QLineEdit()
        self.dataset_name_input.setPlaceholderText("e.g., timit_train")
        form_layout.addRow("Dataset Name:", self.dataset_name_input)

        # Description
        self.description_input = QTextEdit()
        self.description_input.setPlaceholderText(
            "Semantic description of the dataset..."
        )
        self.description_input.setMaximumHeight(80)
        form_layout.addRow("Description:", self.description_input)

        # Options
        options_layout = QHBoxLayout()
        
        # Analysis method dropdown
        self.analysis_method_combo = QComboBox()
        self.analysis_method_combo.addItems(self.analysis_methods)
        self.analysis_method_combo.setCurrentIndex(0)  # Default to first method
        self.analysis_method_combo.setToolTip(
            "Select the analysis method for generating the dataset summary CSV.\n"
            "Different methods provide varying levels of detail."
        )
        self.analysis_method_combo.setStyleSheet("""
            QComboBox {
                padding: 4px;
                border: 2px solid #d0d0d0;
                border-radius: 4px;
                color: #000000;
            }
        """)
        
        self.cache_checkbox = QCheckBox("Cache dataset (copy to storage)")
        self.anonymize_checkbox = QCheckBox("Mark as anonymized")
        
        options_layout.addWidget(QLabel("Analysis Method:"))
        options_layout.addWidget(self.analysis_method_combo)
        options_layout.addSpacing(20)
        options_layout.addWidget(self.cache_checkbox)
        options_layout.addWidget(self.anonymize_checkbox)
        options_layout.addStretch()
        form_layout.addRow("Options:", options_layout)

        layout.addLayout(form_layout)

        # Register button
        register_btn = QPushButton("Register Dataset")
        register_btn.setMinimumHeight(45)
        register_btn.setStyleSheet(
            """
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
        """
        )
        register_btn.clicked.connect(self.register_dataset)
        layout.addWidget(register_btn)

        group.setLayout(layout)
        return group

    def _create_validate_section(self):
        """Create the dataset validation section"""
        group = QGroupBox("Validate Dataset")
        layout = QVBoxLayout()

        desc_label = QLabel(
            "Validate that a dataset follows the Kaldi organization pattern "
            "(speaker subdirectories with audio and .lab files)."
        )
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #7f8c8d; font-size: 12px;")
        layout.addWidget(desc_label)

        # Validate button
        validate_btn = QPushButton("Validate Dataset...")
        validate_btn.setStyleSheet("""
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
        """)
        validate_btn.clicked.connect(self.validate_dataset)
        layout.addWidget(validate_btn)

        group.setLayout(layout)
        return group

    def _create_list_section(self):
        """Create the dataset list section"""
        group = QGroupBox("Registered Datasets")
        layout = QVBoxLayout()

        # Refresh button
        refresh_btn = QPushButton("Refresh")
        refresh_btn.setStyleSheet("""
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
        """)
        refresh_btn.clicked.connect(self.refresh_datasets)
        layout.addWidget(refresh_btn, alignment=Qt.AlignmentFlag.AlignRight)

        # Container for table and empty label
        list_container = QWidget()
        list_container_layout = QVBoxLayout(list_container)
        list_container_layout.setContentsMargins(0, 0, 0, 0)

        # Dataset table
        self.dataset_table = QTableWidget()
        self.dataset_table.setColumnCount(7)
        self.dataset_table.setHorizontalHeaderLabels(
            [
                "Name",
                "Description",
                "Cached",
                "Anonymized",
                "Transcribed",
                "Registration Date",
                "Actions",
            ]
        )

        # Configure table
        header = self.dataset_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        for i in range(2, 7):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.Fixed)
        self.dataset_table.setColumnWidth(7, 250)

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

    def browse_dataset_path(self):
        """Open directory picker for dataset path"""
        directory = QFileDialog.getExistingDirectory(
            self, "Select Dataset Root Directory"
        )
        if directory:
            self.dataset_path_input.setText(directory)

    def register_dataset(self):
        """Register a new dataset"""
        dataset_path = self.dataset_path_input.text().strip()
        dataset_name = self.dataset_name_input.text().strip()
        description = self.description_input.toPlainText().strip()
        cache = self.cache_checkbox.isChecked()
        anonymize = self.anonymize_checkbox.isChecked()
        analysis_method = self.analysis_method_combo.currentText()

        # Validation
        if not dataset_path:
            QMessageBox.warning(
                self, "Input Error", "Please select a dataset path."
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
        print(f"Starting dataset registration with params: {dataset_path}, {dataset_name}, "
              f"{description}, cache={cache}, anonymize={anonymize}, "
              f"analysis_method={analysis_method}"
              )
        self.registration_worker = DatasetRegistrationWorker(
            dataset_path, dataset_name, description, cache, anonymize, analysis_method
        )
        self.registration_worker.progress.connect(self.show_progress)
        self.registration_worker.finished.connect(self.registration_complete)
        self.registration_worker.start()

        # Disable register button
        for btn in self.findChildren(QPushButton):
            if btn.text() == "Register Dataset":
                btn.setEnabled(False)
                btn.setText("Registering...")

    def show_progress(self, message):
        """Show progress message"""
        print(message)

    def registration_complete(self, success, message):
        """Handle registration completion"""
        # Re-enable register button
        for btn in self.findChildren(QPushButton):
            if "Registering..." in btn.text():
                btn.setEnabled(True)
                btn.setText("Register Dataset")

        if success:
            QMessageBox.information(self, "Success", message)
            # Clear form
            self.dataset_path_input.clear()
            self.dataset_name_input.clear()
            self.description_input.clear()
            self.cache_checkbox.setChecked(False)
            self.anonymize_checkbox.setChecked(False)
            # Refresh list
            self.refresh_datasets()
        else:
            QMessageBox.critical(self, "Registration Failed", message)

    def validate_dataset(self):
        """Validate a dataset"""
        directory = QFileDialog.getExistingDirectory(
            self, "Select Dataset to Validate"
        )
        if not directory:
            return

        is_valid = validate_kaldi_dataset(directory)

        if is_valid:
            QMessageBox.information(
                self,
                "Validation Successful",
                "The dataset structure is valid and follows the Kaldi organization pattern.",
            )
        else:
            QMessageBox.warning(self, "Validation Failed", "No Message Available")

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

            # Actions
            actions_widget = self._create_action_buttons(dataset)
            self.dataset_table.setCellWidget(row, 6, actions_widget)

    def _create_action_buttons(self, dataset):
        """Create action buttons for a dataset row"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(5, 2, 5, 2)
        layout.setSpacing(5)

        # Base button style matching pipeline forms
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

        delete_button_style = """
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
        """

        # View button
        view_btn = QPushButton("View")
        view_btn.setMaximumWidth(60)
        view_btn.setStyleSheet(button_style)
        view_btn.clicked.connect(lambda: self.view_dataset(dataset))
        layout.addWidget(view_btn)

        # Edit button
        edit_btn = QPushButton("Edit")
        edit_btn.setMaximumWidth(60)
        edit_btn.setStyleSheet(button_style)
        edit_btn.clicked.connect(lambda: self.edit_dataset(dataset))
        layout.addWidget(edit_btn)

        # Export button
        export_btn = QPushButton("Export")
        export_btn.setMaximumWidth(60)
        export_btn.setStyleSheet(button_style)
        export_btn.clicked.connect(lambda: self.export_dataset(dataset))
        layout.addWidget(export_btn)

        # Delete button
        delete_btn = QPushButton("Delete")
        delete_btn.setMaximumWidth(60)
        delete_btn.setStyleSheet(delete_button_style)
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
            f"Anonymized: {'Yes' if dataset['anonymize'] else 'No'}\n\n"
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
            )

            if success:
                QMessageBox.information(self, "Success", message)
                self.refresh_datasets()
            else:
                QMessageBox.critical(self, "Update Failed", message)

    def export_dataset(self, dataset):
        """Export dataset configuration"""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Dataset Configuration",
            f"{dataset['name']}_config.json",
            "JSON Files (*.json)",
        )

        if file_path:
            success, message = export_dataset_config(dataset["name"], file_path)
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
