from pathlib import Path

from voxkit.gui.frameworks.settings_modal import (
    FieldConfig,
    FieldType,
    SettingsConfig,
)
from voxkit.storage import alignments, datasets, models
from Wav2TextGrid.wav2textgrid import align_dirs
from Wav2TextGrid.wav2textgrid_train import train_aligner

from .base import AlignmentEngine

TrainerConfiguration: SettingsConfig = SettingsConfig(
    title="Wav2TextGrid Trainer Settings",
    dimensions=(400, 300),
    apply_blur=True,
    fields=[
        FieldConfig(
            name="start_from_scratch",
            label="Start from Scratch",
            field_type=FieldType.CHECKBOX,
            default_value=False,
            tooltip="Whether to start training from scratch or fine-tune an existing model.",
        ),
        FieldConfig(
            name="tokenizer_id",
            label="Tokenizer ID",
            field_type=FieldType.LINEEDIT,
            default_value="charsiu/tokenizer_en_cmu",
            tooltip="The Hugging Face tokenizer ID to use for training.",
        ),
        FieldConfig(
            name="epochs",
            label="Number of Epochs",
            field_type=FieldType.SPINBOX,
            default_value=50,
            min_value=1,
            max_value=1000,
            tooltip="The number of epochs to train the model for.",
        ),
        FieldConfig(
            name="use_gpu",
            label="Use GPU",
            field_type=FieldType.CHECKBOX,
            default_value=False,
            tooltip="Enable GPU acceleration for faster training.",
        ),
    ],
    store_file="W2TGENGINE/train/trainer_settings.json",
)

AlignerConfiguration: SettingsConfig = SettingsConfig(
    title="Wav2TextGrid Aligner Settings",
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
        FieldConfig(
            name="use_gpu",
            label="Use GPU",
            field_type=FieldType.CHECKBOX,
            default_value=False,
            tooltip="Enable GPU acceleration for faster processing.",
        ),
    ],
    store_file="W2TGENGINE/aligner/aligner_settings.json",
)


class W2TGEngine(AlignmentEngine):
    """
    Alignment engine implementation using the Wav2TextGrid toolkit.
    """

    def __init__(self, id: str | None = None):
        super().__init__(
            settings_configurations={"align": AlignerConfiguration, "train": TrainerConfiguration},
            reference_url="https://huggingface.co/pkadambi/Wav2TextGrid",
            description=(
                "Wav2TextGrid is a forced alignment tool that uses a Wav2Vec 2.0 model "
                "to align audio files to their corresponding transcripts, producing TextGrid files."
            ),
            human_readable_name="W2TG",
            id=id,
        )
        # for tool, config in self.settings_configurations.items():
        #     # Assert settings files exist
        #     print(f"Ensuring settings file exists: {config.store_file}")
        #     os.makedirs(os.path.dirname(config.store_file), exist_ok=True)

    def align(self, dataset_id: str, model_id: str) -> None:
        print(f"Args received for align: dataset_id={dataset_id}, model_id={model_id}")
        settings = self.get_settings("align")

        print(f"Validating align settings: {settings}")
        result, msg = alignments.create_alignment(
            engine_id=self.id,
            model_id=model_id,
            dataset_id=dataset_id,
        )
        print(f"Alignment creation result: {result}, message: {msg}")

        if result is False:
            print(f"Alignment creation failed: {msg}")
            return

        alignment_meta = msg
        dataset_meta = datasets.get_dataset_metadata(dataset_id)
        model_meta = models.get_model_metadata(self.id, model_id)

        print(f"Aligning with settings: {settings}")
        print(f"Dataset meta: {dataset_meta}")
        print(f"Alignment meta: {alignment_meta}")
        print(f"Model meta: {model_meta}")

        model_path = model_meta["model_path"]
        print(f"Using model path: {model_path}")
        audio_root = datasets._get_dataset_root(dataset_id)

        try:
            align_dirs(
                wavfile_or_dir=audio_root,
                transcriptfile_or_dir=audio_root,
                outfile_or_dir=alignment_meta["tg_path"],
                aligner_model=model_path,
                filetype=settings.get("file_type", "wav"),
                use_speaker_adaptation=settings.get("use_speaker_adaptation", False),
            )
            alignments.update_alignment(
                dataset_id=dataset_id,
                alignment_id=alignment_meta["id"],
                updates={"status": "completed"},
            )

        except Exception as e:
            print(f"Alignment failed: {e}")
            alignments.update_alignment(
                dataset_id=dataset_id,
                alignment_id=alignment_meta["id"],
                updates={"status": "failed"},
            )

    def train_aligner(
        self, audio_root: Path, textgrid_root: Path, base_model_id: str | None, new_model_id: str
    ) -> None:
        new_model_actual_id = None
        try:
            success, message = models.create_model(
                engine_id=self.id,
                model_name=new_model_id,
            )

            if not success:
                raise ValueError(f"Failed to create model entry: {message}")

            model_meta = message
            model_path = Path(model_meta["model_path"])
            data_path = Path(model_meta["data_path"])
            eval_path = Path(model_meta["eval_path"])

            new_model_actual_id = model_meta["id"]

            settings = self.get_settings("train")
            base_model_path = (
                models.get_model_metadata(engine_id=self.id, model_id=base_model_id)["model_path"]
                if base_model_id
                else None
            )

            if base_model_path is None:
                raise ValueError(f"Invalid base model specified: {base_model_id}. ")
            print(
                f"Args received for train_aligner: "
                f"audio_root={audio_root}, textgrid_root={textgrid_root}, "
                f"base_model_path={base_model_path}, model_path={model_path}, "
                f"eval_path={eval_path}, new_model_id={new_model_id}, "
                f"ntrain_epochs={settings.get('epochs', 50)}"
            )

            print(f"Training aligner with settings: {settings}")
            print(f"Using base model path: {base_model_path}")
            train_aligner(
                train_audio_dir=audio_root,
                train_textgrid_dir=textgrid_root,
                tokenizer_name=settings.get("tokenizer_id", "charsiu/tokenizer_en_cmu"),
                model_output_dir=model_path,
                tg_output_dir=eval_path,
                model_name=base_model_path,
                dataset_dir=data_path,
                words_key="words",
                device="cuda" if settings.get("use_gpu", False) else "cpu",
                ntrain_epochs=settings.get("epochs", 50),
                phone_key="phones",
                has_eval_dataset=False,
                retrain=settings.get("start_from_scratch", False),
                download_nltk=True,
            )
        except Exception as e:
            print(f"Training failed: {e}")
            # CLean up model entry on failure
            models.delete_model(engine_id=self.id, model_id=new_model_actual_id)
            raise e

    def _validate_align_settings(self, settings: dict) -> bool:
        if not isinstance(settings.get("use_speaker_adaptation"), bool):
            print("Invalid use_speaker_adaptation setting. Must be a boolean.")
            return False
        if not isinstance(settings.get("file_type"), (str, type(None))):
            print("Invalid file_type setting. Must be a string or None.")
            return False
        if not isinstance(settings.get("use_gpu"), bool):
            print("Invalid use_gpu setting. Must be a boolean.")
            return False
        return True

    def _validate_train_settings(self, settings: dict) -> bool:
        if not isinstance(settings.get("start_from_scratch"), bool):
            print("Invalid start_from_scratch setting. Must be a boolean.")
            return False
        if not isinstance(settings.get("tokenizer_id"), (str, type(None))):
            print("Invalid tokenizer_id setting. Must be a string or None.")
            return False
        if not isinstance(settings.get("epochs"), int):
            print("Invalid epochs setting. Must be an integer.")
            return False
        if not isinstance(settings.get("use_gpu"), bool):
            print("Invalid use_gpu setting. Must be a boolean.")
            return False
        return True
