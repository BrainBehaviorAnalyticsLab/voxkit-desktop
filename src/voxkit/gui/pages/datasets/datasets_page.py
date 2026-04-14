"""Datasets Page Module.

Main widget for registering, validating, and managing speech datasets.

API
---
- **DatasetsPage**: Dataset management page with alignment viewer panel
"""

import csv as csv_mod
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QGraphicsBlurEffect,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from voxkit.analyzers import ManageAnalyzers
from voxkit.gui.components import GripSplitter, HuggingFaceButton
from voxkit.gui.components.csv_viewer_dialog import CSVViewerDialog
from voxkit.gui.styles import Buttons, Containers, Labels
from voxkit.gui.workers import DatasetRegistrationWorker
from voxkit.storage import alignments, datasets
from voxkit.storage.alignments import AlignmentMetadata
from voxkit.storage.datasets import DatasetMetadata


class DatasetsPage(QWidget):
    """Main datasets management page"""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.parent_window = parent
        self.registration_worker: DatasetRegistrationWorker | None = None
        self.selected_dataset: str | None = None
        self.init_ui()
        self.refresh_datasets()

    def get_engines(self) -> list:
        """Return engines that have the 'align' tool available."""
        from voxkit.engines import engines

        all_engine_ids = engines.list_engines()
        filtered_engines = []
        for engine_id in all_engine_ids:
            engine = engines.get_engine(engine_id)
            if engine.has_tool("align"):
                filtered_engines.append(engine_id)
        return filtered_engines

    def init_ui(self):
        """Initialize the UI components"""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # Title header with HuggingFace button
        header_layout = QHBoxLayout()

        title = QLabel("Dataset Management")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #2c3e50;")
        header_layout.addWidget(title)

        header_layout.addStretch()

        # HuggingFace button in top right
        self.hf_button = HuggingFaceButton("Browse Datasets")
        self.hf_button.clicked.connect(self.on_huggingface_browse)
        header_layout.addWidget(self.hf_button)

        main_layout.addLayout(header_layout)

        # Load available analysis methods
        self.analysis_methods = list(ManageAnalyzers.list_analyzers())

        # Create splitter for resizable sections with custom grip handle
        self.splitter = GripSplitter(Qt.Orientation.Vertical)
        self.splitter.setHandleWidth(14)
        self.splitter.setChildrenCollapsible(False)

        # Add datasets section to splitter
        self.datasets_section = self._create_list_section()
        self.splitter.addWidget(self.datasets_section)

        # Add alignments panel to splitter
        self.alignments_panel = self._create_alignments_panel()
        self.splitter.addWidget(self.alignments_panel)

        # Set initial sizes (60% datasets, 40% alignments)
        self.splitter.setSizes([600, 400])

        main_layout.addWidget(self.splitter, stretch=1)

        # Apply initial blur to alignments panel
        self._set_alignments_blur(True)

        # Add register section at bottom
        main_layout.addWidget(self._create_register_section())

        main_layout.setSpacing(20)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # === Footer Credit ===
        credit = QLabel("VoxKit by BrainBehaviorAnalyticsLab")
        credit.setStyleSheet("color: #999; font-size: 10px; padding: 5px;")
        credit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(credit)

    def refresh_page(self):
        """Refresh the entire page content"""
        self.dataset_table.clearSelection()
        self.refresh_datasets()

    def refresh_selected_dataset(self):
        """Refresh alignments for the currently selected dataset"""
        if self.selected_dataset:
            self._load_alignments(self.selected_dataset)

    def _create_register_section(self):
        """Create the dataset registration section"""
        group = QGroupBox()
        layout = QVBoxLayout()

        # Action buttons
        action_layout = QHBoxLayout()
        action_layout.setSpacing(10)

        self.import_btn = QPushButton("Import")
        self.import_btn.setStyleSheet(Buttons.INFO_ACTION)
        self.import_btn.clicked.connect(self.on_import)
        action_layout.addWidget(self.import_btn)

        self.export_btn = QPushButton("Export Selected")
        self.export_btn.setStyleSheet(Buttons.SUCCESS)
        self.export_btn.clicked.connect(self.on_export)
        action_layout.addWidget(self.export_btn)

        self.delete_btn = QPushButton("Delete Selected")
        self.delete_btn.setStyleSheet(Buttons.DANGER)
        self.delete_btn.clicked.connect(self.on_delete)
        action_layout.addWidget(self.delete_btn)

        layout.addLayout(action_layout)

        group.setLayout(layout)
        return group

    def on_huggingface_browse(self):
        """Handle HuggingFace button click"""
        # TODO: Implement HuggingFace dataset browsing/import
        QMessageBox.information(
            self,
            "HuggingFace Integration",
            "HuggingFace dataset browsing will be available soon!\n\n"
            "This will allow you to browse and import datasets directly from HuggingFace Hub.",
        )

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

        success, message = datasets.import_dataset(Path(dir_path))

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

        dir_path = QFileDialog.getExistingDirectory(
            self,
            "Select Directory to Save Exported Dataset",
            "",
            QFileDialog.Option.ShowDirsOnly,
        )

        if not dir_path:
            QMessageBox.warning(self, "No Destination Selected", "Please select a destination.")
            return

        success, message = datasets.export_dataset(self.selected_dataset, Path(dir_path))
        if success:
            QMessageBox.information(self, "Success", message)
        else:
            QMessageBox.critical(self, "Export Failed", message)

    def on_delete(self):
        """Handle delete button click for selected dataset"""
        if not self.selected_dataset:
            QMessageBox.warning(self, "No Dataset Selected", "Please select a dataset to delete.")
            return
        else:
            success, message = datasets.delete_dataset(self.selected_dataset)
            if success:
                QMessageBox.information(self, "Deleted", message)
                self.selected_dataset = None
                self.refresh_page()

            else:
                QMessageBox.critical(self, "Delete Failed", message)

    def _create_list_section(self):
        """Create the dataset list section"""

        group = QGroupBox("Datasets")
        group.setStyleSheet(Containers.GROUP_BOX)
        layout = QVBoxLayout()

        # Add plus button at the top
        button_container = QWidget()
        button_container.setStyleSheet("background-color: transparent;")
        button_layout = QHBoxLayout(button_container)
        button_layout.setContentsMargins(0, 0, 0, 10)

        plus_btn = QPushButton("+ Register New Dataset")
        plus_btn.setStyleSheet(Buttons.INFO_LARGE)
        plus_btn.clicked.connect(self.open_registration_dialog)
        button_layout.addWidget(plus_btn)
        button_layout.addStretch()

        layout.addWidget(button_container)

        # Helper text
        helper_label = QLabel("💡 Select a dataset to view its alignments below")

        helper_label.setStyleSheet(Containers.HELPER_TEXT)
        helper_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout.addWidget(helper_label)

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
                "De-identified",
                "Transcribed",
                "Registration Date",
                "Actions",
            ]
        )

        # Configure table
        header = self.dataset_table.horizontalHeader()
        if header is not None:
            header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
            for i in range(2, 6):
                header.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)
        self.dataset_table.setColumnWidth(6, 100)

        self.dataset_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.dataset_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.dataset_table.itemSelectionChanged.connect(self._on_dataset_selected)

        self.dataset_table.setAlternatingRowColors(True)
        self.dataset_table.setStyleSheet(
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

        list_container_layout.addWidget(self.dataset_table)

        # Add empty state label
        self.empty_label = QLabel(
            "No datasets registered yet.\nUse the form above to register your first dataset."
        )
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setStyleSheet(Containers.EMPTY_STATE)
        self.empty_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.empty_label.hide()  # Hidden by default
        list_container_layout.addWidget(self.empty_label)

        layout.addWidget(list_container, 1)

        group.setLayout(layout)
        return group

    def _create_alignments_panel(self):
        """Create the alignments panel for selected dataset"""
        group = QGroupBox("↓ Alignments for Selected Dataset")
        group.setStyleSheet(Containers.GROUP_BOX)

        # Create container widget for blurrable content
        self.alignments_content = QWidget()
        content_layout = QVBoxLayout(self.alignments_content)
        content_layout.setContentsMargins(0, 0, 0, 0)

        # Engine filter
        filter_layout = QHBoxLayout()
        filter_label = QLabel("Filter by Engine:")
        filter_label.setStyleSheet(Labels.SECTION_LABEL)
        filter_layout.addWidget(filter_label)

        self.engine_filter_combo = QComboBox()
        self.engine_filter_combo.addItem("All Engines")

        self.engine_filter_combo.setStyleSheet(Containers.COMBOBOX_STANDARD)
        self.engine_filter_combo.currentTextChanged.connect(self._filter_alignments)
        filter_layout.addWidget(self.engine_filter_combo)
        filter_layout.addStretch()
        content_layout.addLayout(filter_layout)

        # Alignments table
        self.alignments_table = QTableWidget()
        self.alignments_table.setColumnCount(5)
        self.alignments_table.setHorizontalHeaderLabels(
            ["Engine", "Model", "Date Aligned", "Status", "Actions"]
        )

        # Configure alignments table
        align_header = self.alignments_table.horizontalHeader()
        if align_header is not None:
            align_header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
            align_header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
            align_header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
            align_header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
            align_header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.alignments_table.setColumnWidth(4, 150)

        # Disable selection and editing
        self.alignments_table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.alignments_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.alignments_table.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self.alignments_table.setAlternatingRowColors(True)
        self.alignments_table.setStyleSheet(Containers.TABLE_WIDGET)

        content_layout.addWidget(self.alignments_table)

        # Add content container to group box
        group_layout = QVBoxLayout()
        group_layout.addWidget(self.alignments_content)
        group.setLayout(group_layout)
        return group

    def _on_dataset_selected(self):
        """Handle dataset selection change"""
        selected_items = self.dataset_table.selectedItems()

        if not selected_items:
            self.selected_dataset = None
            self.alignments_table.setRowCount(0)
            self._set_alignments_blur(True)  # Blur when no selection
            return

        # Get dataset name from first column of selected row
        row = selected_items[0].row()

        print(f"Dataset row selected: {row}")
        item = self.dataset_table.item(row, 0)  # The item we stored the ID on

        print(item)

        if item:
            dataset_id = item.data(Qt.ItemDataRole.UserRole)
            print(f"Selected dataset ID: {dataset_id}")
            self.selected_dataset = dataset_id
            self._set_alignments_blur(False)  # Unblur when dataset selected

        self._load_alignments(dataset_id)

    def _set_alignments_blur(self, blurred: bool):
        """Set the blur state of the alignments panel contents.

        Args:
            blurred: True to blur, False to unblur
        """
        if blurred:
            blur_effect = QGraphicsBlurEffect()
            blur_effect.setBlurRadius(10)
            self.alignments_content.setGraphicsEffect(blur_effect)
            self.alignments_content.setEnabled(False)
        else:
            self.alignments_content.setGraphicsEffect(None)
            self.alignments_content.setEnabled(True)

    def _load_alignments(self, dataset_id: str) -> None:
        """Load alignments for the selected dataset"""

        print(f"Loading alignments for dataset ID: {dataset_id}")
        alignments_metadata: list = alignments.list_alignments(dataset_id)

        # Populate engine filter (block signals to prevent recursion)
        current_filter = self.engine_filter_combo.currentText()
        self.engine_filter_combo.blockSignals(True)
        self.engine_filter_combo.clear()
        self.engine_filter_combo.addItem("All Engines")
        self.engine_filter_combo.addItems(sorted(self.get_engines()))
        self.engine_filter_combo.setCurrentText(current_filter)
        self.engine_filter_combo.blockSignals(False)

        self._display_alignments(alignments_metadata)

    def _filter_alignments(self):
        """Filter alignments by selected engine"""
        if not self.selected_dataset:
            return
        self._load_alignments(self.selected_dataset)

    def _display_alignments(self, alignments: list[alignments.AlignmentMetadata]):
        """Display alignments in the table"""
        # Filter by engine if selected

        print("Displaying alignments:")
        print(alignments)
        engine_filter = self.engine_filter_combo.currentText()
        if engine_filter != "All Engines":
            alignments = [a for a in alignments if a["engine_id"] == engine_filter]

        self.alignments_table.setRowCount(len(alignments))

        if not alignments:
            return

        for row, alignment in enumerate(alignments):
            # Engine
            print(alignment)
            engine_item = QTableWidgetItem(alignment["engine_id"])
            engine_item.setFlags(engine_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.alignments_table.setItem(row, 0, engine_item)

            # Model (clickable)
            model_item = QTableWidgetItem(alignment["model_metadata"]["name"])
            model_item.setFlags(model_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            model_item.setForeground(Qt.GlobalColor.blue)
            model_item.setToolTip("Click to view model details")
            font = model_item.font()
            font.setUnderline(True)
            model_item.setFont(font)
            self.alignments_table.setItem(row, 1, model_item)

            # Date Aligned
            date_item = QTableWidgetItem(alignment["alignment_date"])
            date_item.setFlags(date_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.alignments_table.setItem(row, 2, date_item)

            # Status
            status_item = QTableWidgetItem(alignment.get("status", "Unknown"))
            status_item.setFlags(status_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            status = alignment.get("status", "").lower()
            if status == "completed":
                status_item.setForeground(Qt.GlobalColor.darkGreen)
            elif status == "pending":
                status_item.setForeground(Qt.GlobalColor.darkYellow)
            elif status == "failed":
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
                f"Model clicked: {model_name}\n\nModel details will be shown here.",
            )

    def _create_alignment_action_buttons(self, alignment: alignments.AlignmentMetadata) -> QWidget:
        """Create action buttons for an alignment row"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(5, 2, 5, 2)
        layout.setSpacing(5)

        # Delete button
        delete_btn = QPushButton("Delete")
        delete_btn.setStyleSheet(Buttons.DELETE_SMALL)
        delete_btn.clicked.connect(lambda: self._delete_alignment(alignment))
        layout.addWidget(delete_btn)

        # View button
        view_btn = QPushButton("View")
        view_btn.setStyleSheet(Buttons.TABLE_VIEW)
        view_btn.clicked.connect(lambda: self._view_alignment(alignment))
        layout.addWidget(view_btn)

        return widget

    def convert_alignments(self, dataset_name: str) -> list:
        """Generate mock alignment data (to be replaced with actual data loading)"""
        data_set_alignments = alignments.list_alignments(dataset_name)
        return data_set_alignments

    def _view_alignment(self, alignment: AlignmentMetadata):
        """View alignment details"""
        # TODO: Implement alignment details view
        QMessageBox.information(
            self,
            "Alignment Details",
            f"Engine: {alignment['engine_id']}\n"
            f"Model: {alignment['model_metadata']['id']}\n"
            f"Date: {alignment['alignment_date']}\n"
            f"Status: {alignment['status']}",
        )

    def _export_alignment(self, alignment: dict):
        """Export alignment results"""
        # TODO: Implement alignment export
        QMessageBox.information(
            self,
            "Export Alignment",
            f"Export functionality for alignment '{alignment['model']}' will be implemented.",
        )

    def _delete_alignment(self, alignment: AlignmentMetadata):
        """Delete an alignment"""
        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to delete the alignment with model "
            f"'{alignment['model_metadata']['id']}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            if self.selected_dataset is None:
                return
            success, msg = alignments.delete_alignment(
                dataset_id=self.selected_dataset, alignment_id=alignment["id"]
            )

            if not success:
                QMessageBox.critical(self, "Delete Failed", f"Failed to delete alignments: {msg}")
                return
            QMessageBox.information(self, "Deleted", "Alignments deleted successfully.")
            # Refresh alignments list
            if self.selected_dataset:
                self._load_alignments(self.selected_dataset)

    def open_registration_dialog(self):
        """Open the dataset registration settings dialog"""
        from voxkit.gui.frameworks.settings_modal import (
            FieldConfig,
            FieldType,
            GenericDialog,
            SettingsConfig,
        )

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
                    label="De-identified",
                    field_type=FieldType.CHECKBOX,
                    default_value=False,
                    tooltip="Has personally identifiable information been removed?",
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
            print("Registration values:", values)
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
            QMessageBox.warning(self, "Input Error", "Please provide a dataset path.")
            return

        if not dataset_name:
            QMessageBox.warning(self, "Input Error", "Please enter a dataset name.")
            return

        if not description:
            QMessageBox.warning(self, "Input Error", "Please enter a description.")
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
        if self.registration_worker is None:
            return

        self.registration_worker.progress.connect(self.show_progress)
        self.registration_worker.finished.connect(self.registration_complete)
        self.registration_worker.start()

    def browse_dataset_path(self):
        """Open directory picker for dataset path"""
        directory = QFileDialog.getExistingDirectory(self, "Select Dataset Root Directory")
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

        metadata_list = datasets.list_datasets_metadata()

        if not metadata_list:
            self.dataset_table.hide()
            self.empty_label.show()
            self.empty_label.raise_()
            return

        self.empty_label.hide()
        self.dataset_table.show()

        self.dataset_table.setRowCount(len(metadata_list))

        for index, meta in enumerate(metadata_list):
            # Name — store the dataset ID on this item
            name_item = QTableWidgetItem(meta["name"])
            name_item.setData(Qt.ItemDataRole.UserRole, meta["id"])  # ← Store ID here
            self.dataset_table.setItem(index, 0, name_item)  # ← Use the same item!

            # Description
            desc_item = QTableWidgetItem(meta["description"])
            desc_item.setToolTip(meta["description"])
            self.dataset_table.setItem(index, 1, desc_item)

            # Cached
            self.dataset_table.setItem(
                index, 2, QTableWidgetItem("Yes" if meta["cached"] else "No")
            )

            # Anonymized
            self.dataset_table.setItem(
                index, 3, QTableWidgetItem("Yes" if meta["anonymize"] else "No")
            )

            self.dataset_table.setItem(
                index, 4, QTableWidgetItem("Yes" if meta.get("transcribed", False) else "No")
            )

            # Registration date
            reg_date = meta.get("registration_date", "Unknown")
            if reg_date != "Unknown":
                reg_date = reg_date.split("T")[0]  # Show only date part
            self.dataset_table.setItem(index, 5, QTableWidgetItem(reg_date))

            # Actions - Details button
            actions_widget = self._create_dataset_action_buttons(meta)
            self.dataset_table.setCellWidget(index, 6, actions_widget)

    def _create_dataset_action_buttons(self, dataset_meta: DatasetMetadata):
        """Create action buttons for a dataset row.

        Args:
            dataset_meta: Dataset metadata dictionary

        Returns:
            QWidget containing action buttons
        """
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(5, 2, 5, 2)
        layout.setSpacing(5)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Details button
        details_btn = QPushButton("Details")
        details_btn.setStyleSheet(Buttons.TABLE_VIEW)
        details_btn.clicked.connect(lambda: self._view_dataset_details(dataset_meta))
        layout.addWidget(details_btn)

        return widget

    def _view_dataset_details(self, dataset_meta: DatasetMetadata | dict):
        """View dataset analysis CSV details.

        Args:
            dataset_meta: Dataset metadata dictionary
        """

        # Get dataset directory
        dataset_id = dataset_meta["id"]
        dataset_dir = datasets._get_dataset_root(dataset_id)

        if not dataset_dir or not dataset_dir.exists():
            QMessageBox.warning(
                self,
                "Dataset Not Found",
                f"Dataset directory not found for '{dataset_meta['name']}'.",
            )
            return

        # Search for CSV files matching the pattern *_summary.csv
        csv_files = list(dataset_dir.glob("*_summary.csv"))

        if not csv_files:
            QMessageBox.information(
                self,
                "No Analysis Data",
                f"No analysis CSV file found for dataset '{dataset_meta['name']}'.\n\n"
                "Analysis data is generated during dataset registration.",
            )
            return

        # Use the first CSV file found
        csv_path = str(csv_files[0])

        # Try to get a visual representation from the analyzer
        visualization = None
        try:
            file_name = csv_files[0].stem.replace("_summary", "").lower()
            analyzer = None
            for key, a in ManageAnalyzers.get_analyzers().items():
                if key.lower() == file_name:
                    analyzer = a
                    break
            if analyzer is None:
                raise ValueError(f"No analyzer matching '{file_name}'")
            with open(csv_path, "r", encoding="utf-8") as f:
                data = list(csv_mod.DictReader(f))
            visualization = analyzer.visualize(data)
        except Exception as e:
            print(f"Visualization failed for analyzer '{csv_files[0].stem}': {e}")

        # Open viewer dialog (falls back to table if no visualization)
        dialog = CSVViewerDialog(csv_path, parent=self.parent_window, visualization=visualization)
        dialog.exec()
