from voxkit.gui.frameworks.modal.generic import GenericDialog
from .settings import FIELDS, TITLE, DIMS, APPLY_BLUR


class TrainingSettingsDialog(GenericDialog):
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
    def batch_size(self):
        """Get the batch size spinbox widget"""
        return self.field_widgets["batch_size"]
    
    @property
    def num_epochs(self):
        """Get the num_epochs spinbox widget"""
        return self.field_widgets["num_epochs"]
    
    @property
    def use_gpu(self):
        """Get the use_gpu checkbox widget"""
        return self.field_widgets["use_gpu"]
    
    @property
    def save_checkpoints(self):
        """Get the save_checkpoints checkbox widget"""
        return self.field_widgets["save_checkpoints"]