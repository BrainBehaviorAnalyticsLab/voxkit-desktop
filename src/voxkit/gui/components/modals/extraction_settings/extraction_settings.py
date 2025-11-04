from voxkit.gui.frameworks.modal.generic import GenericDialog
from .settings import FIELDS, TITLE, DIMS, APPLY_BLUR


class ExtractionSettingsDialog(GenericDialog):
    """Training settings dialog using the reusable framework"""
    
    def __init__(self, parent=None):
        
        # Initialize the base dialog
        super().__init__(
            parent=parent,
            title=TITLE,
            dims=DIMS,
            fields=FIELDS,
            apply_blur=APPLY_BLUR,
        )
    
    # Convenience properties
    @property
    def acoustic_model(self):
        """Get the acoustic_model textbox widget"""
        return self.field_widgets["acoustic_model"]
    
    @property
    def phone_key(self):
        """Get the phone_key textbox widget"""
        return self.field_widgets["phone_key"]
    
    @property
    def recompute_probas(self):
        """Get the recompute_probas checkbox widget"""
        return self.field_widgets["recompute_probas"]
    
    @property
    def likelihood_dct(self):
        """Get the likelihood_dct textbox widget"""
        return self.field_widgets["likelihood_dct"]
    
    @property
    def aggregation_function(self):
        """Get the aggregation_function combobox widget"""
        return self.field_widgets["aggregation_function"]
    
