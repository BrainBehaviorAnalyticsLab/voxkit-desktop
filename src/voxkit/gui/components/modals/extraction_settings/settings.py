from voxkit.gui.frameworks.modal.generic import FieldConfig, FieldType

TITLE = "Extraction Settings"

DIMS = (375, 425)  # Width, Height

APPLY_BLUR = True

FIELDS = [
    FieldConfig(
        name="acoustic_model",
        label="Acoustic Model:",
        field_type=FieldType.LINEEDIT,
        default_value="pkadambi/w2v2_pronunciation_score_model",
        tooltip="HuggingFace model name or path to local model directory.",
    ),
    FieldConfig(
        name="phone_key",
        label="Phone Key:",
        field_type=FieldType.LINEEDIT,
        default_value="ha phones",
        tooltip="Key in the model's config for phone labels.",
    ),
    FieldConfig(
        name="recompute_probas",
        label="Recompute Probabilities:",
        field_type=FieldType.CHECKBOX,
        default_value=False,
        tooltip="Check to recompute framewise probabilities even if cached data exists.",
    ),
    FieldConfig(
        name="likelihood_dct",
        label="Likelihood Dict Path:",
        field_type=FieldType.LINEEDIT,
        default_value="./computed-likelihoods/likelihood_dict.pkl",
        tooltip="Path to save/load the computed likelihood dictionary.",
    ),
    FieldConfig(
        name="aggregation_function",
        label="Aggregation Function:",
        field_type=FieldType.COMBOBOX,
        default_value="aggregate_by_phoneme_occurrence",
        options=[
            "aggregate_by_phoneme_occurrence",
            "aggregate_by_phoneme_average",
            "aggregate_by_phoneme_median",
        ],
        tooltip="Method to aggregate framewise probabilities into phonewise scores.",
    ),
]
