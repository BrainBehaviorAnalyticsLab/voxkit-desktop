from voxkit.gui.frameworks.modal.generic import FieldConfig, FieldType

TITLE = "Training Settings"

DIMS = (400, 350)  # Width, Height

APPLY_BLUR = True

FIELDS = [
    FieldConfig(
        name="tokenizer_id",
        label="Tokenizer:",
        field_type=FieldType.LINEEDIT,
        default_value="charsiu/tokenizer_en_cmu",
        tooltip="Specify the tokenizer ID to use for training.",
    ),
    FieldConfig(
        name="num_epochs",
        label="Number of Epochs:",
        field_type=FieldType.SPINBOX,
        default_value=100,
        min_value=1,
        max_value=1000,
    ),
    FieldConfig(
        name="use_gpu",
        label="Use GPU if aval:",
        field_type=FieldType.CHECKBOX,
        default_value=False,
        tooltip="Enable to use GPU for training if available.",
    ),
    FieldConfig(
        name="save_checkpoints",
        label="Save Checkpoints:",
        field_type=FieldType.CHECKBOX,
        default_value=True,
        tooltip="Enable to save model checkpoints during training.",
    ),
    FieldConfig(
        name="start_from_scratch",
        label="Start From Scratch:",
        field_type=FieldType.CHECKBOX,
        default_value=False,
        tooltip="Enable to start training from scratch without using a pre-trained model.",
    )
]
