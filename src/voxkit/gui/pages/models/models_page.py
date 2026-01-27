from typing import Any

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog, QLabel, QMessageBox

from voxkit.gui.frameworks.categorical_table.categorical_table import CategoricalTableWidget
from voxkit.gui.frameworks.settings_modal import (
    FieldConfig,
    FieldType,
    GenericDialog,
    SettingsConfig,
)
from voxkit.gui.workers import ModelRegistrationWorker
from voxkit.storage import models

from .import_dialog import ImportModelDialog
from .utils import handle_delete, handle_export, handle_import

# TODO : Implement Aligner managment logic by see
# frameworks/widget/categorical_list/api.py | __init__.py


class ManageAlignersWidget(CategoricalTableWidget):
    """Widget to manage and display alignment models."""

    def __init__(self, parent=None):
        self.parent = parent
        self.data = {}
        self.registration_worker = None

        def refresh_models_function() -> dict[str, list[dict[Any, Any]]]:
            try:
                model_dict = {}
                for engine in self.get_engines():
                    engine_models = models.list_models(engine)
                    model_dict[engine] = engine_models

                return model_dict

            except Exception as e:
                print(f"Error refreshing models: {e}")
                return {}

        def export_models_function(category: str, items: list[dict[Any, Any]]) -> tuple[bool, str]:
            print(f"Export requested for category: {category}")
            return handle_export(self, items, category)

        def import_model_function(category: str) -> tuple[bool, str]:
            print(f"Import requested for category: {category}")
            return handle_import(self, category)

        def delete_models_function(category: str, items: list[dict[Any, Any]]) -> tuple[bool, str]:
            print(f"Delete requested for category: {category}, items: {items}")
            return handle_delete(self, items, category)

        super().__init__(
            refresh_data_function=refresh_models_function,
            export_function=export_models_function,
            import_function=import_model_function,
            delete_function=delete_models_function,
            columns_shown=["name", "download_date", "id"],
            huggingface_callback=self.on_huggingface_browse,
            parent=self.parent,
        )

        self.setWindowTitle("Model Manager")

        # Add register button to the models group
        self._add_register_button()

        self.layout().setSpacing(20)
        self.layout().setContentsMargins(0, 0, 0, 0)

        # === Footer Credit ===
        credit = QLabel("VoxKit by BrainBehaviorAnalyticsLab")
        credit.setStyleSheet("color: #999; font-size: 10px; padding: 5px;")
        credit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout().addWidget(credit)

    def get_engines(self) -> list:
        from voxkit.engines import engines

        return engines.list_engines()
    def showEvent(self, event):
        """Refresh models when the widget is shown.

        This ensures that the model list is always up-to-date when the user
        navigates to the Model Management tab, including after training new models.

        Args:
            event: The show event from Qt
        """
        super().showEvent(event)
        self.refresh_data()
        self.update_display()

    def _add_register_button(self):
        """Add the '+ Register New Model' button to the models group"""
        from PyQt6.QtWidgets import QHBoxLayout, QPushButton, QWidget

        from voxkit.gui.styles import Buttons

        # Find the models group box (it's the widget containing the table)
        models_group = None
        for i in range(self.layout().count()):
            widget = self.layout().itemAt(i).widget()
            if widget and hasattr(widget, "layout") and widget.layout() is not None:
                # Check if this widget contains the table_widget
                for j in range(widget.layout().count()):
                    item = widget.layout().itemAt(j)
                    if item and item.widget() == self.table_widget:
                        models_group = widget
                        break
            if models_group:
                break

        if not models_group:
            return

        # Create button container
        button_container = QWidget()
        button_container.setStyleSheet("background-color: transparent;")
        button_layout = QHBoxLayout(button_container)
        button_layout.setContentsMargins(0, 0, 0, 10)

        plus_btn = QPushButton("+ Register New Model")
        plus_btn.setStyleSheet(Buttons.INFO_LARGE)
        plus_btn.clicked.connect(self.open_registration_dialog)
        button_layout.addWidget(plus_btn)
        button_layout.addStretch()

        # Insert button at the beginning of the models group layout
        models_group.layout().insertWidget(0, button_container)

    def on_huggingface_browse(self):
        """Handle HuggingFace button click"""
        # TODO: Implement HuggingFace model browsing/import
        QMessageBox.information(
            self,
            "HuggingFace Integration",
            "HuggingFace model browsing will be available soon!\n\n"
            "This will allow you to browse and import models directly from HuggingFace Hub.",
        )

    def scrub_training_runs(self, mode, items: dict):
        for model in items.keys():
            if "MFA" in mode:
                mode = "MFAENGINE"
            elif "W2TG" in mode:
                mode = "W2TGENGINE"
            else:
                raise ValueError("Invalid mode")

            print(f"Scrubbing training run for model: {items}")
            models.delete_model(mode, items[model]["id"])

    def reload_models(self):
        """Reload models in the dropdowns"""

        w2tg_models = models.list_models("W2TGENGINE")
        self.set_items("W2TGENGINE", w2tg_models)

    def open_import_dialog(self, category):
        print(f"Opening import dialog for category: {category}")
        dialog = ImportModelDialog(parent=self, engine_id=category)
        if dialog.exec():
            path = dialog.field_widgets["model_path"].text()
            print(f"Importing {category} Model from {path}")
            self.reload_models()
        # Clean up
        self.parent.setGraphicsEffect(None)

    def open_registration_dialog(self):
        """Open the model registration settings dialog"""
        # Create settings config
        config = SettingsConfig(
            title="Register New Model",
            dimensions=(400, 250),
            apply_blur=False,
            store_file="model_registration_settings.json",
            fields=[
                FieldConfig(
                    name="model_path",
                    label="Model Path",
                    field_type=FieldType.LINEEDIT,
                    default_value="",
                    placeholder="Browse for model directory...",
                    tooltip="Path to the model directory or file",
                ),
                FieldConfig(
                    name="model_name",
                    label="Model Name",
                    field_type=FieldType.LINEEDIT,
                    default_value="",
                    placeholder="e.g., english_us_arpa",
                    tooltip="Unique identifier for this model",
                ),
                FieldConfig(
                    name="engine_id",
                    label="Engine",
                    field_type=FieldType.COMBOBOX,
                    default_value=self.get_engines()[0] if self.get_engines() else "MFAENGINE",
                    options=self.get_engines(),
                    tooltip="Select the engine for this model",
                ),
            ],
        )

        # Create and show dialog
        dialog = GenericDialog(self, config=config)
        result = dialog.exec()

        if result == QDialog.DialogCode.Accepted:
            # Get values from dialog
            values = dialog.get_values()
            print("Registration values:", values)
            self.process_registration(values)

    def process_registration(self, values: dict):
        """Process the registration with values from the dialog"""
        model_path = values.get("model_path", "").strip()
        model_name = values.get("model_name", "").strip()
        engine_id = values.get("engine_id", "MFAENGINE")

        # Validation
        if not model_path:
            QMessageBox.warning(self, "Input Error", "Please provide a model path.")
            return

        if not model_name:
            QMessageBox.warning(self, "Input Error", "Please enter a model name.")
            return

        # Start registration in worker thread
        print(
            f"Starting model registration with params: {model_path}, {model_name}, "
            f"engine_id={engine_id}"
        )
        self.registration_worker = ModelRegistrationWorker(model_path, model_name, engine_id)

        if self.registration_worker is None:
            return

        self.registration_worker.progress.connect(self.show_progress)
        self.registration_worker.finished.connect(self.registration_complete)
        self.registration_worker.start()

    def show_progress(self, message):
        """Show progress message"""
        print(message)

    def registration_complete(self, success, message):
        """Handle registration completion"""
        if success:
            QMessageBox.information(self, "Success", message)
            # Refresh models list
            self.refresh_data()
            self.update_display()
        else:
            QMessageBox.critical(self, "Registration Failed", message)


#  Example usage
# if __name__ == "__main__":
#     from PyQt6.QtWidgets import QApplication
#     import sys

#     app = QApplication(sys.argv)

#     # Sample data
#     sample_data = {
#         'MFA Models': {
#             'english_us_arpa': {'path': '~/Users/beckett/Data', 'date': '2025-01-15'},
#             'german_mfa': {'path': '/Users/beckett/Documents/', 'date': '2025-02-20'},
#         },
#         'W2TG Models': {
#             'charsiu_en': {'path': '/Users/beckett/Models/charsiu_en', 'date': '2025-04-05'},
#         }
#     }

#     widget = CategoricalListWidget(sample_data)

#     # Connect signals to see output
#     widget.export_requested.connect(
#             handle_export_lambda(widget, sample_data)
#         )
#     widget.delete_requested.connect(lambda cat, items: print(f"Delete signal: {cat}, {items}"))
#     widget.import_requested.connect(lambda cat: print(f"Import signal: {cat}"))

#     widget.setWindowTitle("Model Manager")
#     widget.resize(700, 600)
#     widget.show()

#     sys.exit(app.exec())
