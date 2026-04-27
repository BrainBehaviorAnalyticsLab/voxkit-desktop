"""Reusable PyQt6 widgets taiored functionally and stylistically for the VoxKit application.

API
---
- **AnimatedStackedWidget**: QStackedWidget with slide transition animations
- **CSVViewerDialog**: Modal dialog for displaying CSV data in a formatted table
- **DNAStrandWidget**: Decorative audio waveform visualization for the toolbar
- **GripSplitter**: QSplitter with visible grip handle for intuitive resizing
- **HuggingFaceButton**: Branded button with HuggingFace logo
- **LoadingDialog**: Splash screen / loading dialog with animated spinner
- **LogViewerDialog**: Dialog for viewing live application logs
- **QObjectLogHandler**: Qt-aware logging handler that emits records as Qt signals
- **get_gui_log_handler**: Accessor for the singleton GUI log handler
- **ModelSelectionPanel**: Combined engine and model selection panel
- **MultiColumnComboBox**: QComboBox with multi-column dropdown table display
- **OverlayWidget**: Semi-transparent overlay for modal blur effects
- **ToggleSwitch**: Animated iOS-style toggle switch widget

Notes
-----
- Components are designed for reuse across pages and dialogs
- Most components follow PyQt6 signal/slot patterns
- Styling is applied via the centralized styles module
"""

from .animate_stack import AnimatedStackedWidget
from .column_dropdown import MultiColumnComboBox
from .csv_viewer_dialog import CSVViewerDialog
from .dna_strand import DNAStrandWidget
from .grip_splitter import GripSplitter
from .huggingface_button import HuggingFaceButton
from .loading_dialog import LoadingDialog
from .log_handler import QObjectLogHandler, get_gui_log_handler
from .log_viewer_dialog import LogViewerDialog
from .model_selection_panel import ModelSelectionPanel
from .overlay_effects import OverlayWidget
from .toggle_switch import ToggleSwitch

__all__ = [
    "AnimatedStackedWidget",
    "CSVViewerDialog",
    "DNAStrandWidget",
    "GripSplitter",
    "HuggingFaceButton",
    "LoadingDialog",
    "LogViewerDialog",
    "ModelSelectionPanel",
    "MultiColumnComboBox",
    "OverlayWidget",
    "QObjectLogHandler",
    "ToggleSwitch",
    "get_gui_log_handler",
]
