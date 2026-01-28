"""Dataset Utilities Module.

Helper functions for dataset export and delete operations.

API
---
- **on_export**: Handle export button click for selected dataset
- **on_delete**: Handle delete button click for selected dataset
"""

from PyQt6.QtWidgets import QFileDialog, QMessageBox

from voxkit.storage import datasets


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

    success, message = datasets.export_dataset(self.selected_dataset["id"], dir_path)
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
        success, message = datasets.delete_dataset(self.selected_dataset["id"])
        if success:
            QMessageBox.information(self, "Deleted", message)
            self.selected_dataset = None

        else:
            QMessageBox.critical(self, "Delete Failed", message)
