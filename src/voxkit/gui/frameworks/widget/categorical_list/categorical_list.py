from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .styles import Buttons, Colors, Labels


class CategoryListItem(QWidget):
    """Custom widget for each list item with checkbox, date, and info button"""

    def __init__(self, item_key, item_data, parent=None):
        super().__init__(parent)
        self.item_key = item_key
        self.item_data = item_data
        self.setMinimumHeight(30)  # Adjust the number as needed

        # Extract path and date from item_data dict
        self.path = item_data.get("path", "") if isinstance(item_data, dict) else ""
        self.date = item_data.get("date", "") if isinstance(item_data, dict) else ""

        layout = QHBoxLayout()
        layout.setContentsMargins(8, 5, 8, 5)
        layout.setSpacing(5)

        # Checkbox
        self.checkbox = QCheckBox()
        self.checkbox.setStyleSheet(f"""
            QCheckBox {{
                spacing: 8px;
            }}
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
                border-radius: 5px;
            }}
            QCheckBox::indicator:unchecked {{
                border: 2px solid {Colors.GRAY};
                border-radius: 5px;
                background-color: white;
            }}
            QCheckBox::indicator:checked {{
                border: 2px solid {Colors.PRIMARY};
                background-color: {Colors.PRIMARY};
            }}
            QCheckBox::indicator:hover {{
                border-color: {Colors.PRIMARY};
            }}
        """)
        layout.addWidget(self.checkbox)

        # Item label
        self.label = QLabel(item_key)
        self.label.setMinimumWidth(150)
        self.label.setStyleSheet(f"""
            QLabel {{
                color: {Colors.TEXT_PRIMARY};
                background-color: {Colors.BG_SECONDARY};
                font-weight: 500;
            }}
        """)
        layout.addWidget(self.label)

        # Date label
        self.date_label = QLabel(str(self.date))
        self.date_label.setMinimumWidth(100)
        self.date_label.setStyleSheet(f"""
            QLabel {{
                color: {Colors.TEXT_TERTIARY};
                font-size: 12px;
            }}
        """)
        layout.addWidget(self.date_label)
        self.date_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # Dotted line separator
        separator = QLabel()
        separator.setFixedHeight(1)
        separator.setStyleSheet(f"""
            QLabel {{
                background-color: transparent;
                border-bottom: 1px dotted {Colors.GRAY};
            }}
        """)
        layout.addWidget(separator, stretch=2)

        self.info_btn = QPushButton("i")
        self.info_btn.setFixedSize(50, 24)
        self.info_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.BG_SECONDARY};
                border: 1px solid {Colors.GRAY};
                border-radius: 6px;
                font-size: 14px;
                font-weight: bold;
                color: {Colors.TEXT_SECONDARY};
            }}
            QPushButton:hover {{
                background-color: {Colors.LIGHT_GRAY};
                color: {Colors.PRIMARY};
                border-color: {Colors.PRIMARY};
            }}
        """)
        self.info_btn.clicked.connect(self.on_info_clicked)

        layout.addWidget(self.info_btn)

        self.setLayout(layout)

        # Style the item widget
        self.setStyleSheet("""
            CategoryListItem {
                background-color: white;
                border-radius: 5px;
            }
            CategoryListItem:hover {
                background-color: #f8f9fa;
            }
        """)

    def sizeHint(self):
        self.layout().activate()
        return self.layout().minimumSize()

    def on_info_clicked(self):
        """Show info dialog with item details"""
        info_text = f"""
        <b>Item:</b> {self.item_key}<br>
        <b>Path:</b> {self.path}<br>
        <b>Date:</b> {self.date}
        """
        QMessageBox.information(self, "Item Information", info_text)

    def is_checked(self):
        return self.checkbox.isChecked()

    def set_checked(self, checked):
        self.checkbox.setChecked(checked)


class CategoricalListWidget(QWidget):
    """Widget for viewing and managing categorical lists"""

    # Signals for export, delete, and import actions
    export_requested = pyqtSignal(str, list)  # folder_name, selected_items
    delete_requested = pyqtSignal(str, dict)  # category, selected_items
    import_requested = pyqtSignal(str)  # category

    def __init__(self, data=None, parent=None):
        super().__init__(parent)
        self.data = data if data else {}
        self.current_category_index = 0
        self.category_keys = list(self.data.keys())

        self.init_ui()
        self.update_display()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # Title
        title = QLabel("Model Manager")
        title.setStyleSheet(Labels.TITLE)
        main_layout.addWidget(title)

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

        main_layout.addLayout(selection_layout)

        # List widget container
        list_container = QWidget()
        list_container.setStyleSheet(f"""
            QWidget {{
                background-color: {Colors.BG_PRIMARY};
                border: 1px solid {Colors.BORDER};
                border-radius: 8px;
            }}
        """)
        list_container_layout = QVBoxLayout(list_container)
        list_container_layout.setContentsMargins(10, 10, 10, 10)

        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet("""
            QListWidget {
                background-color: transparent;
                border: none;
                outline: none;
            }
            QListWidget::item {
                padding: 5px;
                border: none;
                background-color: transparent;
            }
            QListWidget::item:selected {
                background-color: transparent;
            }
        """)
        self.list_widget.setSpacing(5)
        list_container_layout.addWidget(self.list_widget)

        # Add empty state label (overlays the list widget)
        self.empty_label = QLabel("No items in this category")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setStyleSheet(f"""
            QLabel {{
                color: {Colors.TEXT_TERTIARY};
                font-style: italic;
                font-size: 14px;
            }}
        """)
        self.empty_label.hide()  # Hidden by default
        list_container_layout.addWidget(self.empty_label)

        # Stack them using absolute positioning
        self.list_widget.raise_()
        main_layout.addWidget(list_container, stretch=1)

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

        main_layout.addLayout(action_layout)

    def set_data(self, data):
        """Update the widget with new data"""
        self.data = data
        self.category_keys = list(self.data.keys())
        self.current_category_index = 0
        self.update_display()

    def update_display(self):
        """Update the display for the current category"""
        self.list_widget.clear()

        self.list_widget.clear()
        if not self.category_keys:
            self.category_label.setText("No Categories")
            self.prev_btn.setEnabled(False)
            self.next_btn.setEnabled(False)
            self.list_widget.hide()
            self.empty_label.show()
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

        # Populate list with items
        category_data = self.data[current_category]

        if not category_data:
            self.list_widget.hide()
            self.empty_label.show()
            return

        # If we have items, show list and hide empty label
        self.empty_label.hide()
        self.list_widget.show()

        for item_key, item_data in category_data.items():
            list_item = QListWidgetItem(self.list_widget)
            item_widget = CategoryListItem(item_key, item_data)
            list_item.setSizeHint(item_widget.sizeHint())
            self.list_widget.addItem(list_item)
            self.list_widget.setItemWidget(list_item, item_widget)

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
        """Select all items in the current list"""
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            widget = self.list_widget.itemWidget(item)
            if widget and isinstance(widget, CategoryListItem):
                widget.set_checked(True)

    def deselect_all(self):
        """Deselect all items in the current list"""
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            widget = self.list_widget.itemWidget(item)
            if widget and isinstance(widget, CategoryListItem):
                widget.set_checked(False)

    def get_selected_items(self):
        """Get list of selected item keys"""
        selected = {}
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            widget = self.list_widget.itemWidget(item)
            if widget and isinstance(widget, CategoryListItem) and widget.is_checked():
                selected[widget.item_key] = widget.item_data
        return selected

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

        # Ask for folder name with styled dialog
        folder_name, ok = QInputDialog.getText(
            self,
            "Export Selected Items",
            f"Enter folder name for exporting {len(selected_items)} item(s):",
        )

        if ok and folder_name:
            self.export_requested.emit(folder_name, selected_items)
            QMessageBox.information(
                self,
                "Export Started",
                f"Exporting {len(selected_items)} item(s) to '{folder_name}'",
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

        # Confirm deletion with styled message box
        reply = QMessageBox.question(
            self,
            "Confirm Deletion",
            f"Are you sure you want to delete {len(selected_items.keys())} item(s)?\n\nThis action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            current_category = self.category_keys[self.current_category_index]
            print("Emmitting: ", selected_items)
            self.delete_requested.emit(current_category, selected_items)

            # Remove deleted items from display
            for item_key in selected_items:
                if item_key in self.data[current_category]:
                    del self.data[current_category][item_key]

            self.update_display()

            QMessageBox.information(
                self,
                "Deletion Complete",
                f"Successfully deleted {len(selected_items.keys())} item(s)",
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
        self.import_requested.emit(current_category)

        # Show info message
        QMessageBox.information(
            self,
            "Import",
            f"Import functionality for category '{current_category}' will be implemented here.",
            QMessageBox.StandardButton.Ok,
        )


# Example usage
if __name__ == "__main__":
    import sys

    from PyQt6.QtWidgets import QApplication

    app = QApplication(sys.argv)

    # Sample data
    sample_data = {
        "MFA Models": {
            "english_us_arpa": {"path": "/models/mfa/english_us_arpa", "date": "2025-01-15"},
            "german_mfa": {"path": "/models/mfa/german_mfa", "date": "2025-02-20"},
            "french_prosodylab": {"path": "/models/mfa/french_prosodylab", "date": "2025-03-10"},
        },
        "W2TG Models": {
            "charsiu_en": {"path": "/models/w2tg/charsiu_en", "date": "2025-04-05"},
            "custom_model_v1": {"path": "/models/w2tg/custom_v1", "date": "2025-05-12"},
            "custom_model_v2": {"path": "/models/w2tg/custom_v2", "date": "2025-06-18"},
        },
        "Dictionaries": {
            "english_us": {"path": "/dicts/en_us.dict", "date": "2025-01-01"},
            "german": {"path": "/dicts/de.dict", "date": "2025-02-01"},
        },
    }

    widget = CategoricalListWidget(sample_data)

    # Connect signals to see output
    widget.export_requested.connect(
        lambda folder, items: print(f"Export signal: {folder}, {items}")
    )
    widget.delete_requested.connect(lambda cat, items: print(f"Delete signal: {cat}, {items}"))
    widget.import_requested.connect(lambda cat: print(f"Import signal: {cat}"))

    widget.setWindowTitle("Model Manager")
    widget.resize(700, 600)
    widget.show()

    sys.exit(app.exec())
