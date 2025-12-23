# TODO : Add module docstring

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QListWidget, QSizePolicy, QVBoxLayout, QWidget

from voxkit.config import Dimensions
from voxkit.gui.components import AnimatedStackedWidget

from .pllr_stacker import PLLRStacker
from .prediction_stacker import PredictionStacker
from .training_stacker import TrainingStacker


class PipelineFormStack(QWidget):
    """Container widget that manages the pipeline navigation menu and pages"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.init_ui()

    def init_ui(self):
        # Main vertical layout: top content + footer at the bottom
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(10)

        # Top area: horizontal layout with navigation and pages
        content_layout = QHBoxLayout()
        content_layout.setSpacing(20)
        content_layout.setContentsMargins(0, 0, 0, 0)

        # Left side - Navigation menu
        self.menu_list = QListWidget()
        self.menu_list.setMaximumWidth(Dimensions["max_width"])
        self.menu_list.addItem("Ⓐ  Train Aligners")
        # self.menu_list.addItem("Ⓑ  Evaluate Aligner")
        self.menu_list.addItem("Ⓑ  Predict Alignments")
        self.menu_list.addItem("Ⓒ  Extract GOP Scoring")
        content_layout.addWidget(self.menu_list)

        # Right side - Stacked widget for different pipeline pages
        self.stacked_widget = AnimatedStackedWidget()
        self.stacked_widget.addWidget(TrainingStacker(self.parent_window))
        # self.stacked_widget.addWidget(EvaluationStacker(self.parent_window))
        self.stacked_widget.addWidget(PredictionStacker(self.parent_window))
        self.stacked_widget.addWidget(PLLRStacker(self.parent_window))
        content_layout.addWidget(self.stacked_widget, stretch=1)

        # Make top content expand to take available space
        main_layout.addLayout(content_layout, stretch=1)

        # Connect navigation
        self.menu_list.currentRowChanged.connect(self.change_page)
        self.menu_list.setCurrentRow(0)

    def reload(self):
        """Reload models in the training page and predicting page"""
        training_page = self.stacked_widget.widget(0)
        if isinstance(training_page, TrainingStacker):
            training_page.reload_models()
            training_page.reload_datasets()

        predicting_page = self.stacked_widget.widget(1)
        if isinstance(predicting_page, PredictionStacker):
            predicting_page.reload_models()
            predicting_page.reload_datasets()

        pllr_page = self.stacked_widget.widget(2)
        if isinstance(pllr_page, PLLRStacker):
            pllr_page.reload_datasets()

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


__all__ = ["PipelineFormStack"]
