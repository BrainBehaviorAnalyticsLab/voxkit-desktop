"""Pipeline Module.

Pipeline page management with dynamically configurable stackers.

API
---
- **PipelineFormStack**: Container widget with sidebar navigation and stacked pages
- **BaseStacker**: Abstract base class for pipeline pages
- **STACKER_REGISTRY**: Mapping of stacker names to classes

Adding New Stackers
-------------------
1. Create a new file (e.g., ``my_stacker.py``)
2. Inherit from ``BaseStacker`` and implement required methods::

       from .base_stacker import BaseStacker

       class MyStacker(BaseStacker):
           def build_ui(self):
               # Build UI using self.content_layout
               pass

           def get_title(self) -> str:
               return "My Stacker Title"

           def has_settings(self) -> bool:
               return True  # if you have settings

           def on_settings(self):
               # Handle settings button click
               pass

3. Register it in ``STACKER_REGISTRY`` below
4. Add it to your pipeline config YAML file

Notes
-----
- Stackers automatically get standard layout, header, and status label
- Override ``reload_models()`` and ``reload_datasets()`` for data refresh hooks
- See ``base_stacker.py`` for all available methods to override
"""

from typing import TYPE_CHECKING, Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from voxkit.gui.components import AnimatedStackedWidget
from voxkit.gui.styles import Buttons, Containers, Labels

if TYPE_CHECKING:
    from voxkit.config.pipeline_config import PipelineConfig

from .base_stacker import BaseStacker
from .markdown_stacker import MarkdownStacker
from .pllr_stacker import PLLRStacker
from .prediction_stacker import PredictionStacker
from .training_stacker import TrainingStacker
from .transcription_stacker import TranscriptionStacker

# Mapping of stacker class names to actual classes
STACKER_REGISTRY = {
    "TrainingStacker": TrainingStacker,
    "PredictionStacker": PredictionStacker,
    "PLLRStacker": PLLRStacker,
    "MarkdownStacker": MarkdownStacker,
    "TranscriptionStacker": TranscriptionStacker,
}


class PipelineFormStack(QWidget):
    """Container widget that manages the pipeline navigation menu and pages.

    This widget dynamically creates menu items and stacker widgets based on
    the provided pipeline configuration.
    """

    def __init__(self, parent=None, config: Optional["PipelineConfig"] = None):
        """Initialize the pipeline form stack.

        Args:
            parent: Parent widget
            config: Pipeline configuration. If None, uses default configuration.
        """
        super().__init__(parent)
        self.parent_window = parent
        self.config = config

        # If no config provided, load default
        if self.config is None:
            from voxkit.config.pipeline_config import get_pipeline_config

            self.config = get_pipeline_config()

        self.init_ui()

    def init_ui(self):
        """Initialize the UI based on the pipeline configuration."""
        # Main vertical layout: top content + footer at the bottom
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(10)

        # Top area: horizontal layout with navigation and pages
        content_layout = QHBoxLayout()
        content_layout.setSpacing(self.config.ui_config.content_spacing)
        content_layout.setContentsMargins(0, 0, 0, 0)

        # Left side - Navigation menu (dynamically populated from config)
        self.menu_list = QListWidget()
        self.menu_list.setMaximumWidth(self.config.ui_config.menu_max_width)

        # Store mapping of menu index to stacker for reload
        self.stacker_instances = []

        # Right side - Stacked widget for different pipeline pages
        self.stacked_widget = AnimatedStackedWidget()

        # Dynamically create menu items and stackers from configuration
        for step in self.config.enabled_steps:
            # Add menu item
            self.menu_list.addItem(step.label)

            # Get the stacker class from registry
            stacker_class = STACKER_REGISTRY.get(step.stacker_class)

            if stacker_class is None:
                raise ValueError(
                    f"Unknown stacker class '{step.stacker_class}' for step '{step.id}'. "
                    f"Available stackers: {list(STACKER_REGISTRY.keys())}"
                )

            # Create the stacker widget
            # Pass markdown_content if this is a MarkdownStacker
            if step.stacker_class == "MarkdownStacker" and step.markdown_content:
                stacker_widget = stacker_class(
                    self.parent_window, markdown_content=step.markdown_content
                )
            else:
                stacker_widget = stacker_class(self.parent_window)

            # Wrap stacker in a container with collapsible sections at the top
            stacker_container = QWidget()
            container_layout = QVBoxLayout(stacker_container)
            container_layout.setContentsMargins(0, 0, 0, 0)
            container_layout.setSpacing(0)

            # Create collapsible sections from the dictionary
            if step.collapsible_sections:
                for header, content in step.collapsible_sections.items():
                    # Create widget for this section
                    section_widget = QWidget()
                    section_layout = QVBoxLayout(section_widget)
                    section_layout.setContentsMargins(0, 0, 0, 0)
                    section_layout.setSpacing(0)

                    # Toggle button for collapsing/expanding
                    toggle_button = QPushButton(f"▶  {header}")
                    toggle_button.setObjectName(f"sectionToggle_{header}")
                    toggle_button.setCheckable(True)
                    toggle_button.setChecked(False)  # Collapsed by default
                    toggle_button.setCursor(Qt.CursorShape.PointingHandCursor)
                    toggle_button.setStyleSheet(Buttons.TOGGLE)

                    # Content label
                    content_label = QLabel(content)
                    content_label.setObjectName(f"sectionContent_{header}")
                    content_label.setWordWrap(True)
                    content_label.setAlignment(
                        Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop
                    )
                    content_label.setVisible(False)  # Hidden by default
                    content_label.setStyleSheet(Labels.CONTENT_SECTION)

                    # Connect toggle functionality
                    def make_toggle_func(btn, lbl, hdr):
                        def toggle():
                            is_expanded = btn.isChecked()
                            lbl.setVisible(is_expanded)
                            btn.setText(f"▼  {hdr}" if is_expanded else f"▶  {hdr}")

                        return toggle

                    toggle_button.toggled.connect(
                        make_toggle_func(toggle_button, content_label, header)
                    )

                    section_layout.addWidget(toggle_button)
                    section_layout.addWidget(content_label)

                    container_layout.addWidget(section_widget)

            # Add the actual stacker widget
            container_layout.addWidget(stacker_widget, stretch=1)

            # Wrap stacker_container in a scroll area for proper overflow handling
            scroll_area = QScrollArea()
            scroll_area.setWidgetResizable(True)
            scroll_area.setFrameShape(QScrollArea.Shape.NoFrame)
            scroll_area.setStyleSheet(Containers.SCROLL_AREA)
            scroll_area.setWidget(stacker_container)

            self.stacker_instances.append((step.id, step.stacker_class, stacker_widget))
            self.stacked_widget.addWidget(scroll_area)

        content_layout.addWidget(self.menu_list)
        content_layout.addWidget(self.stacked_widget, stretch=1)

        # Make top content expand to take available space
        main_layout.addLayout(content_layout, stretch=1)

        # Connect navigation
        self.menu_list.currentRowChanged.connect(self.change_page)
        self.menu_list.setCurrentRow(0)

    def reload(self):
        """Reload models and datasets in the pipeline pages.

        This method dynamically reloads data based on the stacker type.
        """
        for step_id, stacker_class, stacker_widget in self.stacker_instances:
            # Reload based on stacker type
            if stacker_class == "TrainingStacker":
                if hasattr(stacker_widget, "reload_models"):
                    stacker_widget.reload_models()
                if hasattr(stacker_widget, "reload_datasets"):
                    stacker_widget.reload_datasets()

            elif stacker_class == "PredictionStacker":
                if hasattr(stacker_widget, "reload_models"):
                    stacker_widget.reload_models()
                if hasattr(stacker_widget, "reload_datasets"):
                    stacker_widget.reload_datasets()

            elif stacker_class == "PLLRStacker":
                if hasattr(stacker_widget, "reload_datasets"):
                    stacker_widget.reload_datasets()

            elif stacker_class == "TranscriptionStacker":
                if hasattr(stacker_widget, "reload_datasets"):
                    stacker_widget.reload_datasets()

    def change_page(self, index):
        """Change the displayed page based on menu selection with animation"""
        if index >= 0:  # Valid index
            self.stacked_widget.slideToIndex(index)

    def get_current_page_index(self):
        """Get the current page index"""
        return self.stacked_widget.currentIndex()

    def set_current_page_index(self, index):
        """Set the current page index"""
        self.stacked_widget.setCurrentIndex(index)
        self.menu_list.setCurrentRow(index)


__all__ = ["PipelineFormStack", "BaseStacker"]
