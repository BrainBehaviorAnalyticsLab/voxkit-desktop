"""MFA Engine Module.

Montreal Forced Aligner (MFA) integration for VoxKit.

Tools Provided
--------------
- **align**: Force-align audio to transcripts using pretrained models
- **train**: Adapt existing models to new data via MFA's adapt command

Settings
--------
Stored at ``~/.voxkit/MFAENGINE/{tool}/settings.json``:

- **align**: dictionary, file_type
- **train**: epochs, use_gpu

Notes
-----
- MFA models use .zip extension
- Requires base model for training (adaptation only, no from-scratch training)
- See https://montreal-forced-aligner.readthedocs.io/
"""

from pathlib import Path

from voxkit.gui.frameworks.settings_modal import (
    FieldConfig,
    FieldType,
    SettingsConfig,
)
from voxkit.services.mfa import run_mfa_adapt, run_mfa_align
from voxkit.storage import alignments, datasets, models

from .base import AlignmentEngine


class MFAEngine(AlignmentEngine):
    """
    Alignment engine implementation using the Montreal Forced Aligner (MFA) toolkit.
    """

    def __init__(self, id: str | None = None):
        super().__init__(
            settings_configurations={
                "align": SettingsConfig(
                    title="MFA Aligner Settings",
                    dimensions=(400, 350),
                    apply_blur=True,
                    fields=[
                        FieldConfig(
                            name="dictionary",
                            label="Dictionary",
                            field_type=FieldType.LINEEDIT,
                            default_value="english_us_arpa",
                            tooltip="MFA dictionary name (e.g., english_us_arpa, english_mfa).",
                        ),
                        FieldConfig(
                            name="file_type",
                            label="Audio File Type",
                            field_type=FieldType.LINEEDIT,
                            default_value="wav",
                            tooltip="Specify the audio file type (e.g., wav, flac).",
                        ),
                    ],
                    store_file="MFAENGINE/align/settings.json",
                ),
                "train": SettingsConfig(
                    title="MFA Trainer Settings",
                    dimensions=(400, 350),
                    apply_blur=True,
                    fields=[
                        FieldConfig(
                            name="dictionary",
                            label="Dictionary",
                            field_type=FieldType.LINEEDIT,
                            default_value="english_us_arpa",
                            tooltip="MFA dictionary name (e.g., english_us_arpa, english_mfa).",
                        ),
                        FieldConfig(
                            name="num_iterations",
                            label="Number of Iterations",
                            field_type=FieldType.SPINBOX,
                            default_value=1,
                            min_value=1,
                            max_value=100,
                            tooltip="Number of adaptation iterations.",
                        ),
                        FieldConfig(
                            name="use_gpu",
                            label="Use GPU",
                            field_type=FieldType.CHECKBOX,
                            default_value=False,
                            tooltip="Enable GPU acceleration for faster training.",
                        ),
                    ],
                    store_file="MFAENGINE/train/settings.json",
                ),
            },
            reference_url="https://montreal-forced-aligner.readthedocs.io/en/latest/",
            description=(
                "The Montreal Forced Aligner (MFA) is a tool for "
                "aligning audio files to their corresponding transcripts with a focus on "
                "speech pathology. "
            ),
            human_readable_name="MFA",
            id=id,
        )


    def align(self, dataset_id: str, model_id: str) -> None:
        print(f"Aligning with MFA using model: {model_id}")

        model_metadata = models.get_model_metadata(self.id, model_id)

        dataset_metadata = datasets.get_dataset_metadata(dataset_id)

        corpus_path = None

        if bool(dataset_metadata["cached"]):
            corpus_path = datasets._get_dataset_root(dataset_id)

        else:
            corpus_path = Path(dataset_metadata["original_path"])

        model_path = Path(model_metadata["model_path"])

        result, msg = alignments.create_alignment(
            engine_id=self.id,
            model_id=model_id,
            dataset_id=dataset_id,
        )

        alignment_output_path = msg["tg_path"]

        print(
            f"Running MFA align with corpus: {corpus_path}, "
            f"model: {model_path}, output: {alignment_output_path}"
        )

        try:
            run_mfa_align(
                corpus_dir=str(corpus_path),
                model_path=str(model_path),
                output_dir=str(alignment_output_path),
            )
            alignments.update_alignment(
                dataset_id=dataset_id,
                alignment_id=msg["id"],
                updates={"status": "completed"},
            )
        except Exception:
            alignments.update_alignment(
                dataset_id=dataset_id,
                alignment_id=msg["id"],
                updates={"status": "failed"},
            )

    def train_aligner(
        self, audio_root: Path, textgrid_root: Path, base_model_id: str | None, new_model_id: str
    ) -> None:
        base_model_metadata = (
            models.get_model_metadata(self.id, base_model_id) if base_model_id else None
        )

        if not base_model_metadata:
            raise ValueError("MFA requires a base model for training.")

        base_model_path = base_model_metadata["model_path"]

        success, msg = models.create_model(
            engine_id=self.id,
            model_name=new_model_id,
        )

        # ========= TEMP FIX FOR MFA MODEL EXTENSION ========
        # MFA models use .model extension, so we need to adjust the model path accordingly
        # This should ideally be handled in the storage/models.py create_model function
        # ==================================================

        # Check if metadata['modle_path'] ends with .model and adjust if necessary
        old_model_path = msg["model_path"]
        new_metadata = msg
        new_model_path = new_metadata["model_path"]
        if str(new_model_path).endswith(".model"):
            new_model_path = str(new_model_path).split(".model")[0] + ".zip"
            new_metadata["model_path"] = new_model_path
        # ==================================================

        # Save updated metadata with correct model path
        model_metadata_path = Path(new_metadata["model_path"]).parent / "voxkit_model.json"

        # Make metadata dict serializable
        for key in new_metadata:
            if isinstance(new_metadata[key], Path):
                new_metadata[key] = str(new_metadata[key])
        with open(model_metadata_path, "w") as f:
            import json

            json.dump(new_metadata, f, indent=4)

        # ==================================================

        # Lastly rename old_model_path to new_model_path if they differ
        if old_model_path != new_model_path:
            # Ignore old model path and create new file
            # Create an empty file at new_model_path
            new_path = Path(new_model_path)
            new_path.touch()

        # ==================================================

        if not success:
            raise ValueError(f"Failed to create model entry: {msg}")

        new_model_path = new_metadata["model_path"]

        print(
            f"Training MFA model from base: {base_model_path} "
            f"to new model: {new_model_path} with audio: {audio_root} "
            f"and textgrids: {textgrid_root}"
        )

        try:
            run_mfa_adapt(
                corpus_dir=str(audio_root),
                base_model_path=str(base_model_path),
                output_model_path=str(new_model_path),
            )
        except Exception as e:
            raise RuntimeError(f"MFA model training failed: {e}")

    def _validate_align_settings(self, settings: dict) -> bool:
        return True  # Implement validation logic for align settings here

    def _validate_train_settings(self, settings: dict) -> bool:
        return True  # Implement validation logic for train settings here
