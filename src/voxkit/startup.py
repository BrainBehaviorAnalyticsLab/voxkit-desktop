"""Startup Script Module.

This module handles the execution of startup scripts that run on the first
launch of the application. It provides a mechanism to execute a Python
function before the GUI is fully initialized.

API
---
- **execute_startup_script**: Execute the configured startup script if applicable
"""

from typing import Callable

from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtWidgets import QApplication

from voxkit.gui.components import LoadingDialog
from voxkit.storage.utils import is_first_launch, mark_first_launch_complete


class StartupScriptWorker(QThread):
    """Worker thread for executing the startup script without blocking the UI.

    Signals:
        finished: Emitted when the script execution is complete
        error: Emitted when an error occurs during script execution
    """

    finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, script: Callable[[], None]):
        super().__init__()
        self.script = script

    def run(self):
        """Execute the startup script."""
        try:
            self.script()
            self.finished.emit()
        except Exception as e:
            self.error.emit(str(e))


def execute_startup_script(script: Callable[[], None] | None, app: QApplication) -> None:
    """Execute the startup script if this is the first launch.

    This function checks if this is the first launch of the application. If it is,
    it executes the provided startup script while displaying a loading dialog.
    After successful execution, it marks the first launch as complete.

    Args:
        script: The startup script function to execute, or None to skip
        app: The QApplication instance for event processing

    Note:
        This function blocks until the script execution is complete.
    """
    if script is None:
        return

    if not is_first_launch():
        return

    # Create and show the loading dialog
    loading_dialog = LoadingDialog("Retrieving assets...")
    loading_dialog.show()

    # Process events to ensure the dialog is displayed
    app.processEvents()

    # Create and start the worker thread
    worker = StartupScriptWorker(script)

    # Connect signals
    def on_finished():
        mark_first_launch_complete()
        loading_dialog.accept()

    def on_error(error_msg: str):
        print(f"[ERROR] Startup script failed: {error_msg}")
        loading_dialog.update_message(f"Error: {error_msg}")
        # Still mark as complete to avoid running again
        mark_first_launch_complete()
        loading_dialog.accept()

    worker.finished.connect(on_finished)
    worker.error.connect(on_error)

    # Start the worker and wait for completion
    worker.start()
    loading_dialog.exec()
    worker.wait()
