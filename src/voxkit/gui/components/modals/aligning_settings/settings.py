from voxkit.gui.frameworks.modal.generic import FieldConfig, FieldType

TITLE = "Alignment Settings"

DIMS = (375, 300)  # Width, Height

APPLY_BLUR = True

FIELDS = [
    FieldConfig(
        name="file_type",
        label="File Type:",
        field_type=FieldType.COMBOBOX,
        default_value="wav",
        options=["wav", "flac", "mp3"],
        tooltip="Select the audio file type for alignment.",
    ),
    FieldConfig(
        name="use_speaker_adaptation",
        label="Use Speaker Adaptation:",
        field_type=FieldType.CHECKBOX,
        default_value=True,
        tooltip="Enable to use speaker adaptation during alignment.",
    ),
    FieldConfig(
        name="use_gpu",
        label="Use GPU if available:",
        field_type=FieldType.CHECKBOX,
        default_value=False,
        tooltip="Enable to use GPU for training if available.",
    ),
]
