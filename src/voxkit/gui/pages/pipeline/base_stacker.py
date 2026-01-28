"""Base Stacker Module.

Abstract base class capturing common patterns for pipeline page stackers.

API
---
- **BaseStacker**: Base class with standard layout, header, and status management
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from voxkit.gui.styles import Buttons, Labels


class BaseStacker(QWidget):
    """Base class for pipeline stacker widgets.
    
    This class provides common functionality for all stackers including:
    - Standard layout and margins
    - Header with title and optional settings button
    - Status label management
    - Reload methods for datasets and models
    
    Subclasses should implement:
    - build_ui(): Create the main content of the stacker
    - get_title(): Return the stacker title (optional)
    - has_settings(): Whether to show settings button (optional)
    - on_settings(): Handle settings button click (optional)
    - reload_models(): Reload model data (optional)
    - reload_datasets(): Reload dataset data (optional)
    """
    
    def __init__(self, parent=None):
        """Initialize the base stacker.
        
        Args:
            parent: Parent widget, typically the main window
        """
        super().__init__(parent)
        self.parent = parent
        self.status_label = None
        self.main_layout = None
        self.content_layout = None
        self.init_ui()
    
    def init_ui(self):
        """Initialize the standard UI structure."""
        self.setMinimumWidth(600)
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setSpacing(15)
        self.main_layout.setContentsMargins(30, 30, 30, 30)
        
        # Create header if title is provided
        if self.get_title():
            self._create_header()
            self.main_layout.addSpacing(20)
        
        # Create content layout for subclass to populate
        self.content_layout = QVBoxLayout()
        self.content_layout.setSpacing(10)
        self.main_layout.addLayout(self.content_layout)
        
        # Call subclass to build their specific UI
        self.build_ui()
        
        # Add status label at the bottom if stacker wants it
        if self.has_status_label():
            self._create_status_label()
        
        # Add stretch at the end
        self.main_layout.addStretch()
    
    def _create_header(self):
        """Create the standard header with title and optional settings button."""
        header_layout = QHBoxLayout()
        
        # Title
        title = QLabel(self.get_title())
        title.setStyleSheet(Labels.PAGE_TITLE)
        header_layout.addWidget(title)
        header_layout.addStretch()
        
        # Settings button (if needed)
        if self.has_settings():
            settings_btn = QPushButton("⚙️")
            settings_btn.setFixedSize(65, 40)
            settings_btn.setStyleSheet(Buttons.ICON)
            settings_btn.clicked.connect(self.on_settings)
            header_layout.addWidget(settings_btn)
        
        self.main_layout.addLayout(header_layout)
    
    def _create_status_label(self):
        """Create the standard status label."""
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet(Labels.STATUS_READY)
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.main_layout.addWidget(self.status_label)
    
    def set_status(self, message: str, status_type: str = "ready"):
        """Set the status label text and styling.
        
        Args:
            message: Status message to display
            status_type: One of "ready", "working", "success", "error"
        """
        if not self.status_label:
            return
        
        status_styles = {
            "ready": Labels.STATUS_READY,
            "working": Labels.STATUS_WORKING,
            "success": Labels.STATUS_SUCCESS,
            "error": Labels.STATUS_ERROR,
        }
        
        self.status_label.setText(message)
        self.status_label.setStyleSheet(status_styles.get(status_type, Labels.STATUS_READY))
    
    # Methods for subclasses to override
    
    def build_ui(self):
        """Build the stacker-specific UI components.
        
        This method is called during init_ui() and should populate
        self.content_layout with the stacker's specific widgets.
        
        Subclasses MUST override this method.
        """
        raise NotImplementedError("Subclasses must implement build_ui()")
    
    def get_title(self) -> str:
        """Return the stacker's title for the header.
        
        Returns:
            Title string, or empty string for no header
        """
        return ""
    
    def has_settings(self) -> bool:
        """Whether this stacker has a settings button.
        
        Returns:
            True if settings button should be shown
        """
        return False
    
    def has_status_label(self) -> bool:
        """Whether this stacker has a status label.
        
        Returns:
            True if status label should be shown
        """
        return True
    
    def on_settings(self):
        """Handle settings button click.
        
        Override this method if has_settings() returns True.
        """
        pass
    
    def reload_models(self):
        """Reload model data in the stacker.
        
        Override this method if the stacker displays models.
        """
        pass
    
    def reload_datasets(self):
        """Reload dataset data in the stacker.
        
        Override this method if the stacker displays datasets.
        """
        pass
    
    def reload(self):
        """Reload all data in the stacker.
        
        This is called by the parent when data needs to be refreshed.
        Default implementation calls reload_models() and reload_datasets().
        """
        self.reload_models()
        self.reload_datasets()


__all__ = ["BaseStacker"]
