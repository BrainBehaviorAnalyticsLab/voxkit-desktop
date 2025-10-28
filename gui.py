from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout,
    QStackedWidget, QListWidget
)
from pages.predicting import PredictingPage
from pages.evaluating import EvaluatingPage
from pages.training import TrainingPage
from styles import GlobalStyleSheet
from config import AppName, Dimensions, Defaults


class AlignmentGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.selected_mode = Defaults["mode"]
        self.init_ui()
    
    def change_page(self, index):
        """Change the displayed page based on menu selection"""
        self.stacked_widget.setCurrentIndex(index)

    def init_ui(self):
        self.setWindowTitle(AppName)
        self.setMinimumSize(Dimensions['min_width'], Dimensions['min_height'])
        
        # Set application-wide stylesheet
        self.setStyleSheet(GlobalStyleSheet)
        
        # Central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # Left side - Navigation menu
        self.menu_list = QListWidget()
        self.menu_list.setMaximumWidth(Dimensions['max_width'])
        self.menu_list.addItem("Ⓐ  Train Aligner")
        self.menu_list.addItem("Ⓑ  Predict Alignments")
        self.menu_list.addItem("Ⓒ  Extract PLLR Scores")
        main_layout.addWidget(self.menu_list)
        
        # Right side - Stacked widget for different pages
        self.stacked_widget = QStackedWidget()
        main_layout.addWidget(self.stacked_widget, stretch=1)
        
        # Add pages
        self.stacked_widget.addWidget(TrainingPage(self))
        self.stacked_widget.addWidget(PredictingPage(self))
        self.stacked_widget.addWidget(EvaluatingPage(self))
        
        # Connect signal AFTER stacked_widget is created and populated
        self.menu_list.currentRowChanged.connect(self.change_page)
        self.menu_list.setCurrentRow(0)

    