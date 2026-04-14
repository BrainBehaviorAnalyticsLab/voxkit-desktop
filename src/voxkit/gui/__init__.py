"""VoxKit GUI Module.

PyQt6-based graphical user interface for the VoxKit desktop application.

API
---
- **AlignmentGUI**: Main application window with toolbar navigation

Submodules
----------
- **components/**: Reusable widgets (dropdowns, dialogs, toggles)
- **frameworks/**: UI pattern frameworks (categorical_table, settings_modal)
- **pages/**: Main application pages (datasets, models, pipeline)
- **styles/**: Centralized styling (Colors, Buttons, Labels, Containers)
- **workers/**: QThread background workers for long operations

Notes
-----
- Uses PyQt6 signals/slots for component communication
- Long operations run in QThread workers to avoid UI blocking
- Styling is centralized in the styles module for consistency
"""

import logging
import webbrowser
from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QMainWindow,
    QStackedWidget,
    QToolBar,
    QToolButton,
    QWidget,
)
from rich import print as rprint

from voxkit.config.app_config import AppConfig, get_app_config
from voxkit.config.pipeline_config import PipelineConfig, get_pipeline_config
from voxkit.gui.components import DNAStrandWidget, LogViewerDialog
from voxkit.gui.pages.datasets import DatasetsPage
from voxkit.gui.pages.models import ManageAlignersWidget
from voxkit.gui.pages.pipeline import PipelineFormStack as PipelineContainer

logger = logging.getLogger(__name__)

GlobalStyleSheet = """
    QMainWindow {
        background-color: transparent;
    }
    QWidget {
        background-color: #f5f5f5;
        color: #333;
        font-size: 13px;
        border: none;
    }
    QGroupBox {
        background-color: white;
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        margin-top: 10px;
        padding: 15px;
    }
    QLabel {
        color: #333;
        background-color: transparent;
    }
    QLineEdit {
        background-color: white;
        border: 1px solid #d0d0d0;
        border-radius: 5px;
        padding: 8px 12px;
        min-height: 20px;
        color: #333;
    }
    QLineEdit:focus {
        border: 2px solid #4a90e2;
    }
    QPushButton#primaryButton {
        background-color: white;
        border: 1px solid #d0d0d0;
        border-radius: 5px;
        padding: 8px 16px;
        min-width: 80px;
        min-height: 20px;
        color: #333;
    }
    QPushButton:hover {
        background-color: #f0f0f0;
        border-color: #b0b0b0;
    }
    QPushButton:pressed {
        background-color: #e0e0e0;
    }
    QRadioButton {
        background-color: white;
        color: #333;
        spacing: 8px;
    }
    QRadioButton::indicator {
        width: 18px;
        height: 18px;
        border-radius: 9px;
    }
    QRadioButton::indicator:unchecked {
        border: 2px solid #d0d0d0;
        background-color: white;
    }
    QRadioButton::indicator:checked {
        border: 2px solid #4a90e2;
        background-color: #4a90e2;
    }
    QRadioButton::indicator:hover {
        border-color: #4a90e2;
    }
    QListWidget {
        background-color: white;
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 5px;
        outline: none;
    }
    QListWidget::item {
        padding: 12px 15px;
        border-radius: 5px;
        color: #333;
    }
    QListWidget::item:selected {
        background-color: #4a90e2;
        color: white;
    }
    QListWidget::item:hover {
        background-color: #b0cef2;
    }
    QWidget#centralWidget {
        background-color: #f5f7fa;
    }

    """

ToolBarStyle = """
    QToolBar#globalToolbar {
        background: #2f3542;
        spacing: 6px;
        padding: 4px;
    }
    QToolBar#globalToolbar QToolButton {
        color: #eceff4;
        background: transparent;
        border: 1px solid transparent;
        padding: 6px 10px;
        border-radius: 6px;
        margin: 2px;
    }
    QToolBar#globalToolbar QToolButton:hover {
        background: #3b4252;
        border-color: #4c566a;
    }
    QToolBar#globalToolbar QToolButton:pressed {
        background: #2b6fa2;
    }
    QToolBar#globalToolbar QToolButton:disabled {
        color: #7f8c8d;
    }
    """


class AlignmentGUI(QMainWindow):
    def __init__(
        self,
        app_config: Optional[AppConfig] = None,
        pipeline_config: Optional[PipelineConfig] = None,
    ):
        """Initialize the AlignmentGUI.

        Args:
            app_config: Application configuration. If None, loads default from config files.
            pipeline_config: Pipeline configuration. If None, loads default from config files.
        """
        super().__init__()

        # Load configurations (use provided or load defaults)
        self.app_config = app_config or get_app_config()
        self.pipeline_config = pipeline_config or get_pipeline_config()

        logger.info(
            "AlignmentGUI initialized: app=%s version=%s",
            self.app_config.app_name,
            self.app_config.version,
        )

        # DEBUG
        rprint("[bold green]App Configuration:[/bold green]")
        rprint(self.app_config)
        rprint("\n[bold green]Pipeline Configuration:[/bold green]")
        rprint(self.pipeline_config)

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
        logger.info("Navigate: Datasets page")
        # Remember current pipeline page
        self.last_pipeline_page = self.pipeline_container.get_current_page_index()
        self.pipeline_container.menu_list.setVisible(False)
        self.content_stack.setCurrentIndex(1)  # Show datasets page
        # Refresh the selected dataset to show any new alignments
        self.datasets_page.refresh_selected_dataset()
        # Update active tab styling
        self.update_active_tab_style("datasets")

    def open_models_dashboard(self):
        """Switch to Pipeline view with menu and stacked pages"""
        logger.info("Navigate: Pipeline page")
        self.pipeline_container.reload()  # Ensure models are reloaded
        self.pipeline_container.menu_list.setVisible(True)
        self.content_stack.setCurrentIndex(0)  # Show pipeline stack
        # Restore last selected pipeline page
        self.pipeline_container.set_current_page_index(self.last_pipeline_page)
        # Update active tab styling
        self.update_active_tab_style("pipeline")

    def open_preferences(self):
        """Switch to Manage view with CategoricalListWidget"""
        logger.info("Navigate: Models page")
        self.pipeline_container.reload()  # Ensure models are reloaded
        # Remember current pipeline page
        self.last_pipeline_page = self.pipeline_container.get_current_page_index()
        self.pipeline_container.menu_list.setVisible(False)
        self.content_stack.setCurrentIndex(2)  # Show manage widget
        # Update active tab styling
        self.update_active_tab_style("manage")

    def open_help(self):
        logger.info("Opening help URL: %s", self.app_config.help_url)
        webbrowser.open(self.app_config.help_url)

    def init_ui(self):
        self.setWindowTitle(self.app_config.app_name)
        self.setMinimumSize(1200, 800)

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
        self.pipeline_container = PipelineContainer(self, config=self.pipeline_config)
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

        # Subtle status-bar entry point for the log viewer
        self._init_log_status_entry()

    def _init_log_status_entry(self) -> None:
        """Attach a low-visibility log viewer button floating in the bottom-right."""
        central = self.centralWidget()
        if central is None:
            return

        self._log_button = QToolButton(central)
        self._log_button.setText("\u2630")  # trigram glyph — subtle, monochrome
        self._log_button.setToolTip("View application log")
        self._log_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._log_button.setStyleSheet(
            "QToolButton {"
            " background: transparent;"
            " color: #9aa0a6;"
            " border: none;"
            " padding: 0 4px;"
            " font-size: 12px;"
            "}"
            "QToolButton:hover { color: #5f6368; }"
        )
        self._log_button.clicked.connect(self._open_log_viewer)
        self._log_button.adjustSize()
        self._log_button.raise_()
        self._log_viewer: Optional[LogViewerDialog] = None

        central.installEventFilter(self)
        self._reposition_log_button()

    def _reposition_log_button(self) -> None:
        central = self.centralWidget()
        if central is None or not hasattr(self, "_log_button"):
            return
        btn = self._log_button
        btn.adjustSize()
        # Bottom-right, aligned to the existing 20px content margin.
        x = central.width() - btn.width() - 4
        y = central.height() - btn.height() - 4
        btn.move(max(0, x), max(0, y))

    def eventFilter(self, obj, event):  # noqa: N802 (Qt API)
        from PyQt6.QtCore import QEvent

        if obj is self.centralWidget() and event.type() in (
            QEvent.Type.Resize,
            QEvent.Type.Show,
        ):
            self._reposition_log_button()
        return super().eventFilter(obj, event)

    def _open_log_viewer(self) -> None:
        logger.info("Opening log viewer")
        if self._log_viewer is None or not self._log_viewer.isVisible():
            self._log_viewer = LogViewerDialog(self)
            self._log_viewer.show()
        else:
            self._log_viewer.raise_()
            self._log_viewer.activateWindow()


__all__ = ["AlignmentGUI"]
