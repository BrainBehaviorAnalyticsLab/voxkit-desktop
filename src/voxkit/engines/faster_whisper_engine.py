"""Faster Whisper Engine Module.

Faster-Whisper integration for VoxKit transcription.

Tools Provided
--------------
- **transcribe**: Transcribe audio files to produce ``.lab`` label files

Settings
--------
Stored at ``~/.voxkit/FASTERWHISPERENGINE/transcribe/transcriber_settings.json``:

- **model_size**: Whisper model size (tiny, base, small, medium, large-v3)
- **language**: Language code for transcription (empty for auto-detect)
- **device**: Compute device (auto, cpu, cuda)
- **compute_type**: Numerical precision (float16, int8, float32)

Notes
-----
- Uses CTranslate2 backend via faster-whisper for efficient inference
- Produces one ``.lab`` file per ``.wav`` file, placed adjacent to the source audio
- See https://github.com/SYSTRAN/faster-whisper
"""

from pathlib import Path

from faster_whisper import WhisperModel

from voxkit.gui.frameworks.settings_modal import (
    FieldConfig,
    FieldType,
    SettingsConfig,
)
from voxkit.storage import datasets

from .base import AlignmentEngine

TranscriberConfiguration: SettingsConfig = SettingsConfig(
    title="Faster Whisper Transcription Settings",
    dimensions=(400, 350),
    apply_blur=True,
    fields=[
        FieldConfig(
            name="model_size",
            label="Model Size",
            field_type=FieldType.COMBOBOX,
            default_value="base",
            options=["tiny", "base", "small", "medium", "large-v3"],
            tooltip="Whisper model size. Larger models are more accurate but slower.",
        ),
        FieldConfig(
            name="language",
            label="Language",
            field_type=FieldType.LINEEDIT,
            default_value="en",
            placeholder="e.g. en, fr, de (empty for auto-detect)",
            tooltip="Language code for transcription. Leave empty for auto-detection.",
        ),
        FieldConfig(
            name="device",
            label="Device",
            field_type=FieldType.COMBOBOX,
            default_value="auto",
            options=["auto", "cpu", "cuda"],
            tooltip="Compute device for inference.",
        ),
        FieldConfig(
            name="compute_type",
            label="Compute Type",
            field_type=FieldType.COMBOBOX,
            default_value="int8",
            options=["float16", "int8", "float32"],
            tooltip="Numerical precision for model weights.",
        ),
    ],
    store_file="FASTERWHISPERENGINE/transcribe/transcriber_settings.json",
)


class FasterWhisperEngine(AlignmentEngine):
    """Transcription engine using faster-whisper (CTranslate2 backend)."""

    def __init__(self, id: str | None = None):
        super().__init__(
            settings_configurations={"transcribe": TranscriberConfiguration},
            reference_url="https://github.com/SYSTRAN/faster-whisper",
            description=(
                "Faster Whisper is a transcription engine that uses OpenAI's Whisper model "
                "via CTranslate2 to transcribe audio files into text label files."
            ),
            human_readable_name="Faster Whisper",
            id=id,
        )

    def transcribe(self, dataset_id: str) -> None:
        """Transcribe all .wav files in a dataset, writing .lab files adjacent to each.

        Args:
            dataset_id: Identifier of the dataset to transcribe.

        Raises:
            ValueError: If the dataset is not found or audio root cannot be resolved.
            RuntimeError: If transcription fails for any file.
        """
        settings = self.get_settings("transcribe")
        dataset_meta = datasets.get_dataset_metadata(dataset_id)

        if not dataset_meta:
            raise ValueError(f"Dataset '{dataset_id}' not found.")

        # Resolve the audio root directory
        if dataset_meta["cached"]:
            dataset_root = datasets._get_dataset_root(dataset_id)
            if dataset_root is None:
                raise ValueError(f"Dataset root not found for '{dataset_id}'.")
            audio_root = dataset_root / "cache"
        else:
            audio_root = Path(dataset_meta["original_path"])

        if not audio_root.exists():
            raise ValueError(f"Audio root does not exist: {audio_root}")

        # Load the model
        model_size = settings.get("model_size", "base")
        device = settings.get("device", "auto")
        compute_type = settings.get("compute_type", "int8")
        language = settings.get("language", "en") or None

        print(f"[FasterWhisper] Loading model: {model_size} on {device} ({compute_type})")
        model = WhisperModel(model_size, device=device, compute_type=compute_type)

        # Walk speaker directories and transcribe each .wav file
        for speaker_dir in sorted(audio_root.iterdir()):
            if not speaker_dir.is_dir() or speaker_dir.name.startswith("."):
                continue

            wav_files = sorted(speaker_dir.glob("*.wav"))
            for wav_path in wav_files:
                lab_path = wav_path.with_suffix(".lab")

                if lab_path.exists():
                    print(f"[FasterWhisper] Skipping (lab exists): {wav_path.name}")
                    continue

                print(f"[FasterWhisper] Transcribing: {wav_path.name}")
                segments, _ = model.transcribe(
                    str(wav_path),
                    language=language,
                    beam_size=5,
                )

                transcript = " ".join(segment.text.strip() for segment in segments)
                lab_path.write_text(transcript.strip(), encoding="utf-8")
                print(f"[FasterWhisper] Wrote: {lab_path.name}")

    # -- Abstract method stubs (this engine does not provide align/train) --

    def align(self, dataset_id: str, model_id: str) -> None:
        raise NotImplementedError("FasterWhisperEngine does not support alignment.")

    def train_aligner(
        self, audio_root: Path, textgrid_root: Path, base_model_id: str | None, new_model_id: str
    ) -> None:
        raise NotImplementedError("FasterWhisperEngine does not support training.")

    def _validate_align_settings(self, settings: dict) -> bool:
        return False

    def _validate_train_settings(self, settings: dict) -> bool:
        return False

    def _validate_transcribe_settings(self, settings: dict) -> bool:
        model_size = settings.get("model_size")
        if model_size not in ("tiny", "base", "small", "medium", "large-v3"):
            print(f"Invalid model_size: {model_size}")
            return False
        if not isinstance(settings.get("device"), str):
            print("Invalid device setting. Must be a string.")
            return False
        if not isinstance(settings.get("compute_type"), str):
            print("Invalid compute_type setting. Must be a string.")
            return False
        return True
