from voxkit.gui.frameworks.modal.generic import GenericDialog
from .settings import FIELDS, TITLE, DIMS, APPLY_BLUR


class AlignmentSettingsDialog(GenericDialog):
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
    def expected_pairs(self):
        """Get the expected_pairs spinbox widget"""
        return self.field_widgets["expected_pairs"]
    
    @property
    def assert_num_pairs(self):
        """Get the assert_num_pairs checkbox widget"""
        return self.field_widgets["assert_num_pairs"] 
    
    @property
    def use_gpu(self):
        """Get the use_gpu checkbox widget"""
        return self.field_widgets["use_gpu"]