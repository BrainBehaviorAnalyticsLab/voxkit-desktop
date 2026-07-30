"""Regression tests for tooltip handling in the settings-modal framework."""

from PyQt6.QtWidgets import QFormLayout

from voxkit.gui.frameworks.settings_modal import (
    FieldConfig,
    FieldType,
    GenericDialog,
    SettingsConfig,
)


def _build_dialog(qtbot, tooltip):
    config = SettingsConfig(
        title="Test",
        dimensions=(400, 200),
        apply_blur=False,
        store_file="test_tooltips_settings.json",
        fields=[
            FieldConfig(
                name="field",
                label="Field Label",
                field_type=FieldType.CHECKBOX,
                default_value=False,
                tooltip=tooltip,
            ),
        ],
    )
    dialog = GenericDialog(None, config=config)
    qtbot.addWidget(dialog)
    return dialog


def _label_at(dialog, row):
    item = dialog.form_layout.itemAt(row, QFormLayout.ItemRole.LabelRole)
    return item.widget()


class TestSettingsModalTooltips:
    def test_tooltip_set_on_both_label_and_widget(self, qtbot):
        dialog = _build_dialog(qtbot, "Helpful explanation")

        # The input widget carries the tooltip...
        assert dialog.field_widgets["field"].toolTip() == "Helpful explanation"
        # ...and so does the field label, since users hover the label text.
        assert _label_at(dialog, 0).toolTip() == "Helpful explanation"

    def test_no_tooltip_leaves_label_empty(self, qtbot):
        dialog = _build_dialog(qtbot, None)

        assert _label_at(dialog, 0).toolTip() == ""
