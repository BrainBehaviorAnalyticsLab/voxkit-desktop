"""
A custom ComboBox widget that supports multiple columns in its dropdown list.

Single selection only.
"""     

import sys
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QComboBox, QTableView, QHeaderView
)
from PyQt6.QtGui import QStandardItemModel, QStandardItem
from PyQt6.QtCore import Qt

class MultiColumnComboBox(QComboBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Use a table view for the dropdown popup to show multiple columns
        table_view = QTableView()
        table_view.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        table_view.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        table_view.verticalHeader().hide()
        table_view.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table_view.setShowGrid(False)
        
        self.setView(table_view)
        
        # Optional: make the popup wider
        self.view().setMinimumWidth(400)

    def set_data(self, rows, headers=None, placeholder=None):
        """
        Populate the combo box with multi-column data.
        
        :param rows: List of dicts with 'id' key and 'data' key containing tuple/list of column values
                     e.g., [{'id': 1, 'data': ("Alice", 30, "New York")}, ...]
        :param headers: Optional list of column headers
        :param placeholder: Optional placeholder text to show when no item is selected
        """
        num_cols = len(rows[0]['data']) if rows else 0
        model = QStandardItemModel(len(rows), num_cols)
        
        if headers:
            model.setHorizontalHeaderLabels(headers)
        
        for row_idx, row in enumerate(rows):
            row_id = row['id']
            row_data = row['data']
            
            for col_idx, value in enumerate(row_data):
                item = QStandardItem(str(value))
                item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                # Store the ID in the first column item
                if col_idx == 0:
                    item.setData(row_id, Qt.ItemDataRole.UserRole)
                model.setItem(row_idx, col_idx, item)
        
        self.setModel(model)
        
        # The line edit (current visible item) will show the first column by default
        self.setModelColumn(0)
        
        # Set placeholder and clear selection if provided
        if placeholder:
            self.setPlaceholderText(placeholder)
            self.setCurrentIndex(-1)
    
    def current_id(self):
        """Get the ID of the currently selected row."""
        index = self.model().index(self.currentIndex(), 0)

        if not index.isValid():
            return None
        
        return self.model().data(index, Qt.ItemDataRole.UserRole)
    
if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    window = QWidget()
    layout = QVBoxLayout(window)
    
    combo = MultiColumnComboBox()
    data = [
        {'id': 1, 'data': ("Alice", 30, "New York")},
        {'id': 2, 'data': ("Bob", 25, "Los Angeles")},
        {'id': 3, 'data': ("Charlie", 35, "Chicago")},
    ]
    headers = ["Name", "Age", "City"]
    combo.set_data(data, headers)
    
    layout.addWidget(combo)
    
    window.setWindowTitle("Multi-Column ComboBox Example")
    window.resize(500, 200)
    window.show()
    
    sys.exit(app.exec())
