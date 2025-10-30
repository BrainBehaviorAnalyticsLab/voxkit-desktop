from .utils import handle_export_lambda
from frameworks.widget.categorical_list import CategoricalListWidget

# TODO : Implement Aligner managment logic by see frameworks/widget/categorical_list/api.py | __init__.py

class ManageAlignersWidget(CategoricalListWidget):
    """Widget to manage and display alignment models."""
    
    def __init__(self, data: dict, parent=None):
        data = {
            'MFA Models': {
                'english_us_arpa': {'path': '/Users/beckett/Data', 'date': '2025-01-15'},
                'german_mfa': {'path': '/Users/beckett/Documents/', 'date': '2025-02-20'},
            },
            'W2TG Models': {
                'charsiu_en': {'path': '/Users/beckett/Models/charsiu_en', 'date': '2025-04-05'},
            }
        }
        super().__init__(data, parent)
        self.export_requested.connect(
            handle_export_lambda(self, data)
        )
        self.delete_requested.connect(lambda cat, items: print(f"Delete signal: {cat}, {items}"))
        self.import_requested.connect(lambda cat: print(f"Import signal: {cat}"))
        
        self.setWindowTitle("Model Manager")
        self.resize(700, 600)

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

