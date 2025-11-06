from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel

from voxkit.gui.components.modals.import_model_dialog.import_model_dialog import ImportModelDialog
from voxkit.gui.frameworks.widget.categorical_list import CategoricalListWidget
from voxkit.storage.paths import list_modelz, scrub_training_run

from .utils import handle_export_lambda

# TODO : Implement Aligner managment logic by see frameworks/widget/categorical_list/api.py | __init__.py


class ManageAlignersWidget(CategoricalListWidget):
    """Widget to manage and display alignment models."""

    def __init__(self, parent=None):
        mfa_models = list_modelz("MFA", True)
        w2tg_models = list_modelz("W2TG", True)
        self.parent = parent
        data = {"MFA Models": mfa_models, "W2TG Models": w2tg_models}

        super().__init__(data, parent)

        self.export_requested.connect(handle_export_lambda(self, data))

        self.delete_requested.connect(lambda cat, items: self.scrub_training_runs(cat, items))
        self.import_requested.connect(lambda cat: self.open_import_dialog(cat))

        self.setWindowTitle("Model Manager")

        self.layout().setSpacing(20)
        self.layout().setContentsMargins(0, 0, 0, 0)

        # === Footer Credit ===
        credit = QLabel("VoxKit by BrainBehaviorAnalyticsLab")
        credit.setStyleSheet("color: #999; font-size: 10px; padding: 5px;")
        credit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout().addWidget(credit)
    
    def scrub_training_runs(self, mode, items: dict):
        for model in items.keys():
            if "MFA" in mode:
                mode = "MFA"
            elif "W2TG" in mode:
                mode = "W2TG"
            else:
                raise ValueError("Invalid mode")
            scrub_training_run(mode, items[model]["train_root"])
            # Implement deletion logic here
            # Example: delete files or database entries associated with the model
            # You might want to add error handling and confirmation dialogs

    def open_import_dialog(self, category):
        dialog = ImportModelDialog(parent=self, engine_id=category)
        if dialog.exec():
            path = dialog.field_widgets["model_path"].text()
            print(f"Importing {category} Model from {path}")
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
