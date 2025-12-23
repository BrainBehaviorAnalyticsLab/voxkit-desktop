import webbrowser

from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtWidgets import QHBoxLayout, QMainWindow, QStackedWidget, QToolBar, QWidget
from styles import GlobalStyleSheet, ToolBarStyle

from voxkit.config import HELP_URL, AppName, Dimensions
from voxkit.gui.components import DNAStrandWidget
from voxkit.gui.pages.datasets import DatasetsPage
from voxkit.gui.pages.models import ManageAlignersWidget
from voxkit.gui.pages.pipeline import PipelineFormStack as PipelineContainer


class AlignmentGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        # Create the toolbar
        toolbar = QToolBar("Global Toolbar")
        toolbar.setMovable(False)
        toolbar.setFloatable(False)
        self.addToolBar(toolbar)
        # Add actions (buttons)
        self.add_global_actions(toolbar)
        self.init_ui()

    def add_global_actions(self, toolbar):
        # Give the toolbar an object name so stylesheet rules can target it
        toolbar.setObjectName("globalToolbar")
        toolbar.setMovable(False)
        # Apply stylesheet for toolbar and its tool buttons
        toolbar.setStyleSheet(ToolBarStyle)

        # Helper to add an action and apply some per-button properties
        def _add_button(text, callback, tooltip=None, icon=QIcon()):
            action = QAction(icon, text, self)
            if tooltip:
                action.setToolTip(tooltip)
            action.triggered.connect(callback)
            toolbar.addAction(action)
            # style the concrete tool button widget if available
            widget = toolbar.widgetForAction(action)

            if widget is not None:
                widget.setCursor(widget.cursor())  # ensure widget exists; can set more props here
            return action

        # Store actions for Pipeline, Datasets, Manage so we can update their styles
        self.pipeline_action = _add_button(
            "Pipeline", self.open_models_dashboard, tooltip="Main Pipeline Dashboard"
        )
        self.datasets_action = _add_button(
            "Datasets", self.open_datasets, tooltip="Manage Datasets"
        )
        self.manage_action = _add_button(
            "Models", self.open_preferences, tooltip="Manage Aligner Models"
        )
        # Help button
        _add_button("Help", self.open_help, tooltip="Get Help")

        # Store toolbar reference for updating button styles
        self.toolbar = toolbar

        # Add spacer to push DNA widget to fill remaining space
        spacer = QWidget()
        spacer.setSizePolicy(
            spacer.sizePolicy().horizontalPolicy(), spacer.sizePolicy().verticalPolicy()
        )
        toolbar.addWidget(spacer)

        # Add decorative DNA strand widget
        self.dna_widget = DNAStrandWidget()
        toolbar.addWidget(self.dna_widget)

    def update_active_tab_style(self, active_button):
        """Update the styling to show which tab is active"""
        # Style for active tab - gradient blending from toolbar to content background
        active_style = """
            background: qlineargradient(
                x1:0, y1:0, x2:0, y2:1,
                stop:0 #2f3542,
                stop:1 #f5f7fa
            );
            border: 1px solid transparent;
            border-bottom: none;
            border-radius: 6px 6px 0px 0px;
            padding: 6px 10px;
            margin: 2px;
            margin-bottom: 0px;
            color: #25282F; /* Dark text for active tab */
        """

        # Style for inactive tabs
        inactive_style = """
            color: #eceff4;
            background: transparent;
            border: 1px solid transparent;
            padding: 6px 10px;
            border-radius: 6px;
            margin: 2px;
        """

        # Get the actual button widgets
        datasets_widget = self.toolbar.widgetForAction(self.datasets_action)
        pipeline_widget = self.toolbar.widgetForAction(self.pipeline_action)
        manage_widget = self.toolbar.widgetForAction(self.manage_action)

        # Apply styles based on which button is active
        if active_button == "datasets":
            if datasets_widget:
                datasets_widget.setStyleSheet(active_style)
            if pipeline_widget:
                pipeline_widget.setStyleSheet(inactive_style)
            if manage_widget:
                manage_widget.setStyleSheet(inactive_style)
        elif active_button == "pipeline":
            if datasets_widget:
                datasets_widget.setStyleSheet(inactive_style)
            if pipeline_widget:
                pipeline_widget.setStyleSheet(active_style)
            if manage_widget:
                manage_widget.setStyleSheet(inactive_style)
        elif active_button == "manage":
            if datasets_widget:
                datasets_widget.setStyleSheet(inactive_style)
            if pipeline_widget:
                pipeline_widget.setStyleSheet(inactive_style)
            if manage_widget:
                manage_widget.setStyleSheet(active_style)

    def open_datasets(self):
        """Switch to Datasets view"""
        print("Open Datasets...")
        # Remember current pipeline page
        self.last_pipeline_page = self.pipeline_container.get_current_page_index()
        self.pipeline_container.menu_list.setVisible(False)
        self.content_stack.setCurrentIndex(1)  # Show datasets page
        # Update active tab styling
        self.update_active_tab_style("datasets")

    def open_models_dashboard(self):
        """Switch to Pipeline view with menu and stacked pages"""
        print("Open Models Dashboard...")
        self.pipeline_container.reload()  # Ensure models are reloaded
        self.pipeline_container.menu_list.setVisible(True)
        self.content_stack.setCurrentIndex(0)  # Show pipeline stack
        # Restore last selected pipeline page
        self.pipeline_container.set_current_page_index(self.last_pipeline_page)
        # Update active tab styling
        self.update_active_tab_style("pipeline")

    def open_preferences(self):
        """Switch to Manage view with CategoricalListWidget"""
        print("Open Preferences...")
        self.pipeline_container.reload()  # Ensure models are reloaded
        # Remember current pipeline page
        self.last_pipeline_page = self.pipeline_container.get_current_page_index()
        self.pipeline_container.menu_list.setVisible(False)
        self.content_stack.setCurrentIndex(2)  # Show manage widget
        # Update active tab styling
        self.update_active_tab_style("manage")

    def open_help(self):
        webbrowser.open(HELP_URL)
        print("Open Help...")

    def init_ui(self):
        self.setWindowTitle(AppName)
        self.setMinimumSize(Dimensions["min_width"], Dimensions["min_height"])

        # Set application-wide stylesheet
        self.setStyleSheet(GlobalStyleSheet)

        # Track last pipeline page
        self.last_pipeline_page = 0

        # Central widget and main layout
        central_widget = QWidget()
        central_widget.setObjectName("centralWidget")
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # Master stacked widget to switch between Pipeline, Datasets and Manage views
        self.content_stack = QStackedWidget()
        main_layout.addWidget(self.content_stack, stretch=1)

        # Pipeline view: container with menu and animated stacked widget
        self.pipeline_container = PipelineContainer(self)
        self.content_stack.addWidget(self.pipeline_container)

        # Datasets view: dataset management page
        self.datasets_page = DatasetsPage(self)
        self.content_stack.addWidget(self.datasets_page)

        # Manage view: categorical list widget
        self.manage_widget = ManageAlignersWidget(self)
        self.content_stack.addWidget(self.manage_widget)

        # Start with Pipeline view
        self.content_stack.setCurrentIndex(0)

        # Set initial active tab style
        self.update_active_tab_style("pipeline")


if __name__ == "__main__":
    from voxkit.services.hf import download_and_copy_huggingface_model
    from voxkit.storage.utils import create_train_destination

    data_path, model_path, train_path, eval_path = create_train_destination("prads model", "W2TG")

    print(data_path)
    download_and_copy_huggingface_model(model_path="pkadambi/Wav2TextGrid", destination=model_path)
