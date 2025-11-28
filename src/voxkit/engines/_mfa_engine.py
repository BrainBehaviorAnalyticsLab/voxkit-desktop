from pathlib import Path

from voxkit.gui.frameworks.settings_modal import (
    FieldConfig,
    FieldType,
    SettingsConfig,
)

from .base import AlignmentEngine
from .register import register_engine


@register_engine(author="Beckett")
class MFAEngine(AlignmentEngine):
    """
    Alignment engine implementation using the Montreal Forced Aligner (MFA) toolkit.
    """

    def __init__(self, id: str | None = None):
        super().__init__(
            settings_configurations={
                "align": SettingsConfig(
                    title="MFA Aligner Settings",
                    dimensions=(400, 300),
                    apply_blur=True,
                    fields=[
                        FieldConfig(
                            name="use_speaker_adaptation",
                            label="Use Speaker Adaptation",
                            field_type=FieldType.CHECKBOX,
                            default_value=False,
                            tooltip="Enable speaker adaptation for better alignment results.",
                        ),
                        FieldConfig(
                            name="file_type",
                            label="Audio File Type",
                            field_type=FieldType.LINEEDIT,
                            default_value="wav",
                            tooltip="Specify the audio file type (e.g., wav, flac).",
                        ),
                    ],
                    store_file="MFAENGINE/aligner/aligner_settings.json",
                ),
            },
            reference_url="https://montreal-forced-aligner.readthedocs.io/en/latest/",
            description=(
                "The Montreal Forced Aligner (MFA) is a tool for "
                "aligning audio files to their corresponding transcripts, "
                "producing TextGrid files. It uses a combination of acoustic and language models "
                "to perform the alignment."
            ),
            human_readable_name="Montreal Forced Aligner",
            id=id,
        )

    def align(self, audio_root: Path, output_root: Path, model_id: str) -> None:
        print(f"Aligning with MFA using model: {model_id}")
        pass  # Implement the alignment logic using MFA here

    def train_aligner(
        self, audio_root: Path, textgrid_root: Path, base_model_id: str | None, new_model_id: str
    ) -> None:
        print(
            f"Training MFA aligner with base model: {base_model_id} "
            f"and new model id: {new_model_id}"
        )
        pass  # Implement the training logic for MFA here

    def _validate_align_settings(self, settings: dict) -> bool:
        return True  # Implement validation logic for align settings here

    def _validate_train_settings(self, settings: dict) -> bool:
        return True  # Implement validation logic for train settings here
