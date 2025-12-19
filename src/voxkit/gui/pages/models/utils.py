"""
Export handler for copying model files to a download folder
"""

import shutil
from pathlib import Path
from datetime import datetime
import json

from voxkit.storage import models
from PyQt6.QtWidgets import QFileDialog, QMessageBox


def handle_import(parent_widget, current_category: str):
    """
    Handle importing models into the storage.

    Args:
        parent_widget: Parent widget for dialogs
        current_category: Current category being viewed

    Returns:
        tuple: (success: bool, message: str)
    """
    # Ask user to select model files or directory
    import_path = QFileDialog.getExistingDirectory(
        parent_widget, "Select Models Directory", str(Path.home())
    )

    if not import_path:
        return False, ""
    


    return models.import_models(current_category, Path(import_path))


def handle_delete(parent_widget, selected_items: list, current_category: str) -> tuple[bool, str]:
    """
    Handle deleting selected models from storage.   

    Args:
        parent_widget: Parent widget for dialogs
        selected_items: List of selected item keys
        current_category: Current category being viewed
    Returns:
        tuple: (success: bool, message: str)
    """
    try:
        for item in selected_items:
            success, msg = models.delete_model(current_category, item["id"])
            if not success:
                return False, f"Failed to delete model {item['id']}: {msg}"
            
        return True, "Selected models deleted successfully."
    except Exception as e:
        return False, f"Error deleting models: {str(e)}"


def handle_export(
    parent_widget, selected_items: list[dict], current_category: str
) -> tuple[bool, str]:
    """
    Export selected items by copying their paths to a new folder.

    Args:
        parent_widget: Parent widget for dialogs
        folder_name: Name of the folder to create for exported items
        selected_items: List of selected item keys
        data: Dictionary containing all category data
        current_category: Current category being viewed

    Returns:
        tuple: (success: bool, message: str)
    """
    try:
        # Ask user where to save the export folder
        export_base_dir = QFileDialog.getExistingDirectory(
            parent_widget, "Select Export Location", str(Path.home() / "Downloads")
        )

        if not export_base_dir:
            return False, ""
        
        folder_name = f'voxkit_models_{datetime.now().strftime("%Y%m%d_%H%M%S")}'

        # Create the export folder
        export_folder = Path(export_base_dir) / folder_name
        export_folder.mkdir(parents=True, exist_ok=True)


        # Track success/failure
        copied_count = 0
        failed_items = []

        # Copy each selected item
        for item in selected_items:

            if not item:
                failed_items.append(f"{item} (not found in data)")
                continue

            # Get source path
            if isinstance(item, dict):
                source_path = models._get_model_root(current_category, item["id"])
            else:
               failed_items.append(f"{item} (invalid item format)")

            if not source_path.exists():
                failed_items.append(f"{str(source_path)} (source path does not exist)")
                continue

            # Determine destination
            if source_path.is_dir():
                # Copy directory
                dest_path = export_folder / source_path.name
                shutil.copytree(source_path, dest_path, dirs_exist_ok=True)
                copied_count += 1
            else:
                failed_items.append(f"{item} (unknown type)")

        

        # Build result message
        if copied_count == len(selected_items):
            message = f"Successfully exported {copied_count} item(s) to:\n{export_folder}"
            return True, message
        elif copied_count > 0:
            message = (
                f"Exported {copied_count}/{len(selected_items)} item(s) to:\n{export_folder}\n\n"
            )
            message += "Failed items:\n" + "\n".join(failed_items)
            return True, message
        else:
            message = "Export failed for all items:\n" + "\n".join(failed_items)
            return False, message

    except Exception as e:
        return False, f"Export error: {str(e)}"


def handle_export_lambda(widget, data):
    """
    Create a lambda-compatible export handler.

    Usage:
        widget.export_requested.connect(
            lambda folder, items: handle_export_lambda(widget, data)(folder, items)
        )

    Or better yet:
        export_handler = handle_export_lambda(widget, data)
        widget.export_requested.connect(export_handler)

    Args:
        widget: The CategoricalListWidget instance
        data: Dictionary containing all category data

    Returns:
        Callable that handles the export signal
    """

    def _handler(folder_name: str, selected_items: list):
        # Get current category
        if not widget.category_keys:
            QMessageBox.warning(widget, "Error", "No category selected")
            return

        current_category = widget.category_keys[widget.current_category_index]

        # Call the main export function
        success, message = handle_export(
            widget, folder_name, selected_items, data, current_category
        )

        # Show result to user
        if success:
            QMessageBox.information(widget, "Export Complete", message)
        else:
            QMessageBox.critical(widget, "Export Failed", message)

    return _handler


# Alternative: Simpler inline lambda version
def create_export_handler(widget, data):
    """
    Simpler version that returns a handler function.

    Usage:
        widget.export_requested.connect(create_export_handler(widget, data))
    """
    return lambda folder_name, selected_items: handle_export(
        widget,
        folder_name,
        selected_items,
        data,
        widget.category_keys[widget.current_category_index],
    )


# Example usage in your application
if __name__ == "__main__":
    """
    Example of how to use the export handlers
    """
    import sys

    from PyQt6.QtWidgets import QApplication

    # Mock data
    sample_data = {
        "MFA Models": {
            "english_us_arpa": {
                "path": "/Users/beckett/models/mfa/english_us_arpa",
                "date": "2025-01-15",
            },
            "german_mfa": {"path": "/Users/beckett/models/mfa/german_mfa", "date": "2025-02-20"},
        },
        "W2TG Models": {
            "charsiu_en": {"path": "/Users/beckett/models/w2tg/charsiu_en", "date": "2025-04-05"},
        },
    }

    app = QApplication(sys.argv)

    # Import your widget
    # from categorical_list_widget_styled import CategoricalListWidget
    # widget = CategoricalListWidget(sample_data)

    # Method 1: Using handle_export_lambda
    # widget.export_requested.connect(handle_export_lambda(widget, sample_data))

    # Method 2: Using create_export_handler (simpler)
    # widget.export_requested.connect(create_export_handler(widget, sample_data))

    # Method 3: Direct lambda (most explicit)
    # widget.export_requested.connect(
    #     lambda folder, items: handle_export(
    #         widget, folder, items, sample_data,
    #         widget.category_keys[widget.current_category_index]
    #     ) and QMessageBox.information(widget, "Done", "Export complete")
    # )

    print("Export handlers created successfully!")
