from voxkit.engines.w2tg_engine import TrainerSettings
from voxkit.gui.frameworks.modal.generic import GenericDialog

from .settings import APPLY_BLUR, DIMS, FIELDS, TITLE


class W2TGTrainingSettingsDialog(GenericDialog):
    """Training settings dialog using the reusable framework"""

    def __init__(self, parent=None, store_values_path=None):
        # Initialize the base dialog
        super().__init__(
            parent=parent,
            title=TITLE,
            dims=DIMS,
            fields=FIELDS,
            apply_blur=APPLY_BLUR,
            store_values_path=store_values_path
        )

    # Settings
    @property
    def capture_settings(self) -> TrainerSettings:
        """Get the current training settings as a TrainerSettings object"""
        return TrainerSettings(
            num_epochs=self.field_widgets["num_epochs"].value(),
            tokenizer_id=self.field_widgets["tokenizer_id"].text(),
            use_gpu=self.field_widgets["use_gpu"].isChecked(),
            save_checkpoints=self.field_widgets["save_checkpoints"].isChecked(),
            start_from_scratch=self.field_widgets["start_from_scratch"].isChecked(),
        )
    
