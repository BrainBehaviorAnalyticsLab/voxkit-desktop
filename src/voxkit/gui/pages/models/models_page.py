from typing import Any

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel, QMessageBox

from voxkit.engines import engines
from voxkit.gui.frameworks.categorical_table.categorical_table import CategoricalTableWidget
from voxkit.storage import models

from .import_dialog import ImportModelDialog
from .utils import handle_delete, handle_export, handle_import

ENGINE_IDS = engines.list_engines()
# TODO : Implement Aligner managment logic by see
# frameworks/widget/categorical_list/api.py | __init__.py


class ManageAlignersWidget(CategoricalTableWidget):
    """Widget to manage and display alignment models."""

    def __init__(self, parent=None):
        self.parent = parent
        self.data = {}

        def refresh_models_function() -> dict[str, list[dict[Any, Any]]]:
            try:
                model_dict = {}
                for engine in ENGINE_IDS:
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

        self.layout().setSpacing(20)
        self.layout().setContentsMargins(0, 0, 0, 0)

        # === Footer Credit ===
        credit = QLabel("VoxKit by BrainBehaviorAnalyticsLab")
        credit.setStyleSheet("color: #999; font-size: 10px; padding: 5px;")
        credit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout().addWidget(credit)

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
