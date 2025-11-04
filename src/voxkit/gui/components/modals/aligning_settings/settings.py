from voxkit.gui.frameworks.modal.generic import FieldConfig, FieldType

TITLE = "Alignment Settings"

DIMS = (375, 300)  # Width, Height

APPLY_BLUR = True

FIELDS = [
    FieldConfig(
        name="expected_pairs",
        label="Max Files to Align:",
        field_type=FieldType.SPINBOX,
        default_value=None,
        min_value=1,
        max_value=1000000,
    ),
    FieldConfig(
        name="assert_num_pairs",
        label="Validate Number of Pairs:",
        field_type=FieldType.CHECKBOX,
        default_value=10,
        min_value=1,
        max_value=100,
    ),
    FieldConfig(
        name="use_gpu",
        label="Use GPU if aval:",
        field_type=FieldType.CHECKBOX,
        default_value=False,
        tooltip="Enable to use GPU for training if available.",
    ),
]
