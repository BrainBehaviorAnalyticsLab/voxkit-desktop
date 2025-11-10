from voxkit.gui.frameworks.modal.generic import GenericDialog

from .settings import APPLY_BLUR, DIMS, FIELDS, TITLE


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
