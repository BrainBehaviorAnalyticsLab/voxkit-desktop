# TODO : Add module docstring

from PyQt6.QtWidgets import QWidget, QHBoxLayout, QListWidget, QLabel
from ui.widgets import AnimatedStackedWidget
from .training import TrainingPage
from .predicting import PredictingPage
from .evaluating import EvaluatingPage
from config import Dimensions


class PipelineFormStack(QWidget):
    """Container widget that manages the pipeline navigation menu and pages"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.init_ui()
    
    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Left side - Navigation menu
        self.menu_list = QListWidget()
        self.menu_list.setMaximumWidth(Dimensions['max_width'])
        self.menu_list.addItem("Ⓐ  Train Aligner")
        self.menu_list.addItem("Ⓑ  Evaluate Aligner")
        self.menu_list.addItem("Ⓒ  Predict Alignments")
        self.menu_list.addItem("ⓩ  Extract PLLR Scores")
        layout.addWidget(self.menu_list)
        
        # Right side - Stacked widget for different pipeline pages
        self.stacked_widget = AnimatedStackedWidget()
        self.stacked_widget.addWidget(TrainingPage(self.parent_window))
        
        # Placeholder for Evaluate page
        placeholder_widget = QWidget()
        placeholder_widget.setObjectName("placeholderPage")
        placeholder_layout = QHBoxLayout(placeholder_widget)
        placeholder_label = QLabel("Placeholder Page - Coming Soon")
        placeholder_label.setStyleSheet("font-size:18px; color:#666;")
        placeholder_layout.addWidget(placeholder_label)
        self.stacked_widget.addWidget(placeholder_widget)
        
        self.stacked_widget.addWidget(PredictingPage(self.parent_window))
        self.stacked_widget.addWidget(EvaluatingPage(self.parent_window))
        layout.addWidget(self.stacked_widget, stretch=1)
        
        # Connect navigation
        self.menu_list.currentRowChanged.connect(self.change_page)
        self.menu_list.setCurrentRow(0)
    
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

__all__ = ['PipelineFormStack']