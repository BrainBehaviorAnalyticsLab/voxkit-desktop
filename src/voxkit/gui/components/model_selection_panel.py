"""Combined engine and model selection widget for pipeline pages."""

from PyQt6.QtWidgets import (
    QButtonGroup,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)

from voxkit.gui.components import MultiColumnComboBox
from voxkit.gui.styles import Containers, Labels
from voxkit.storage import models


class ModelSelectionPanel(QGroupBox):
    """Reusable panel for selecting alignment engines and models.

    This component displays a list of available engines with radio buttons,
    their associated model dropdowns, and description boxes. It adapts to
    window size changes and maintains proper visibility toggling.

    Args:
        engines_dict: Dictionary of engine instances keyed by engine ID
        title: Optional title for the group box
        info_text: Optional info text displayed above the engines
        placeholder: Placeholder text for model dropdowns

    Attributes:
        selected_engine: Currently selected engine ID
        engine_radios: Dictionary mapping engine IDs to radio buttons
        engine_dropdowns: Dictionary mapping engine IDs to model dropdowns
    """

    def __init__(
        self,
        engines_dict: dict,
        title: str = "",
        info_text: str = "① Choose an alignment method",
        placeholder: str = "➁ Click to select a model",
    ):
        super().__init__()
        self.engines_dict = engines_dict
        self.info_text = info_text
        self.placeholder = placeholder
        self.selected_engine: str | None = None
        self.engine_dropdowns: dict[str, MultiColumnComboBox] = {}
        self.engine_radios: dict[str, QRadioButton] = {}
        self.mode_button_group: QButtonGroup

        if title:
            self.setTitle(title)

        self._init_ui()

    def _init_ui(self):
        """Initialize the UI components."""
        layout = QVBoxLayout()
        layout.setSpacing(8)

        # Info label
        info_label = QLabel(self.info_text)
        info_label.setStyleSheet(Labels.INFO_SMALL)
        layout.addWidget(info_label)

        # Create button group for radio buttons
        self.mode_button_group = QButtonGroup(self)

        # Get list of available engines
        available_engines = list(self.engines_dict.keys())

        # Dynamically create engine options
        for idx, engine_id in enumerate(available_engines):
            engine_obj = self.engines_dict[engine_id]
            engine_name = engine_obj.name()
            engine_description = engine_obj.description

            # Create engine layout
            engine_layout = QHBoxLayout()
            engine_layout.setSpacing(0)
            engine_layout.setContentsMargins(0, 0, 0, 0)

            # Radio button
            radio = QRadioButton(engine_name)
            radio.setChecked(idx == 0)  # Check first one by default
            radio.toggled.connect(self._on_mode_changed)

            self.engine_radios[engine_id] = radio
            self.mode_button_group.addButton(radio)

            # Radio container with fixed width
            radio_container = QHBoxLayout()
            radio_container.addWidget(radio)
            radio_container.addStretch()
            radio_container.setContentsMargins(0, 0, 0, 0)

            radio_widget = QWidget()
            radio_widget.setLayout(radio_container)
            radio_widget.setFixedWidth(160)
            radio_widget.setStyleSheet(Containers.TRANSPARENT_CONTAINER)
            engine_layout.addWidget(radio_widget)

            # Add spacing to align dropdown with description box
            engine_layout.addSpacing(25)

            # Model dropdown
            dropdown = MultiColumnComboBox()
            dropdown.setStyleSheet(Labels.INFO_SMALL)

            # Populate models
            model_list = models.list_models(engine_id)
            if model_list:
                data = []
                for m in model_list:
                    if isinstance(m, dict):
                        data.append(
                            {"id": m["id"], "data": (m["name"], m["download_date"], m["id"])}
                        )
                    else:
                        raise ValueError("Model list item is not a dict")
                dropdown.set_data(
                    data, ["Name", "Download Date", "ID"], placeholder=self.placeholder
                )
                dropdown.setEnabled(True)
            else:
                dropdown.set_data(
                    [{"id": None, "data": ("No models registered", "", "")}],
                    ["Name", "Download Date", "ID"],
                    placeholder="No models registered",
                )
                dropdown.setEnabled(False)

            dropdown.setFixedWidth(300)

            self.engine_dropdowns[engine_id] = dropdown
            engine_layout.addWidget(dropdown)
            engine_layout.addStretch()

            layout.addLayout(engine_layout)

            # Description in a styled box
            if engine_description:
                desc_container = QWidget()
                desc_container.setStyleSheet(Containers.HELPER_TEXT)
                desc_layout = QHBoxLayout(desc_container)
                desc_layout.setContentsMargins(8, 6, 8, 6)

                info = QLabel(engine_description)
                info.setStyleSheet(Labels.INFO_SMALL)
                info.setWordWrap(True)
                desc_layout.addWidget(info)

                layout.addWidget(desc_container)

            layout.addSpacing(5)

        # Set initial selected engine
        if available_engines:
            self.selected_engine = available_engines[0]

        self.setLayout(layout)

        # Set initial visibility of dropdowns based on selected engine
        self._on_mode_changed()

    def _on_mode_changed(self):
        """Handle engine selection change."""
        # Find which radio button is checked
        for engine_id, radio in self.engine_radios.items():
            if radio.isChecked():
                self.selected_engine = engine_id
                break

        # Show/hide appropriate dropdowns
        for engine_id, dropdown in self.engine_dropdowns.items():
            dropdown.setVisible(engine_id == self.selected_engine)

    def get_selected_engine(self) -> str | None:
        """Get the currently selected engine ID.

        Returns:
            The ID of the currently selected engine, or None if no engine is selected
        """
        return self.selected_engine

    def get_selected_model_id(self) -> str | None:
        """Get the ID of the selected model for the current engine.

        Returns:
            The ID of the selected model, or None if no model is selected
        """

        if self.selected_engine is not None and self.selected_engine in self.engine_dropdowns:
            model_id = self.engine_dropdowns[self.selected_engine].current_id()
            return model_id if isinstance(model_id, str) or model_id is None else None
        return None

    def reload_models(self):
        """Reload models in all engine dropdowns."""
        for engine_id, dropdown in self.engine_dropdowns.items():
            dropdown.clear()
            model_list = models.list_models(engine_id)

            if model_list:
                data = []
                for m in model_list:
                    if isinstance(m, dict):
                        data.append(
                            {"id": m["id"], "data": (m["name"], m["download_date"], m["id"])}
                        )
                    else:
                        raise ValueError("Model list item is not a dict")
                dropdown.set_data(
                    data, ["Name", "Download Date", "ID"], placeholder=self.placeholder
                )
                dropdown.setEnabled(True)
            else:
                dropdown.set_data(
                    [{"id": None, "data": ("No models registered", "", "")}],
                    ["Name", "Download Date", "ID"],
                    placeholder="No models registered",
                )
                dropdown.setEnabled(False)

    def get_dropdown_for_engine(self, engine_id: str) -> MultiColumnComboBox | None:
        """Get the dropdown widget for a specific engine.

        Args:
            engine_id: The engine ID

        Returns:
            The MultiColumnComboBox for the engine, or None if not found
        """
        return self.engine_dropdowns.get(engine_id)
