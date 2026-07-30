"""Startup Script Module.

First-launch script execution with loading dialog display.

API
---
- **StartupScriptWorker**: QThread worker for non-blocking script execution
- **execute_startup_script**: Execute startup script on first launch
- **execute_mfa_provisioning**: Provision the bundled MFA environment when missing
"""

import logging
from typing import Callable

from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtWidgets import QApplication

from voxkit.gui.components import LoadingDialog
from voxkit.storage.utils import is_first_launch, mark_first_launch_complete

logger = logging.getLogger(__name__)


class StartupScriptWorker(QThread):
    """Worker thread for executing the startup script without blocking the UI.

    Signals:
        finished: Emitted when the script execution is complete
        error: Emitted when an error occurs during script execution
    """

    finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, script: Callable[[], object]):
        super().__init__()
        self.script = script

    def run(self):
        """Execute the startup script."""
        try:
            logger.info("Startup script running")
            self.script()
            logger.info("Startup script finished")
            self.finished.emit()
        except Exception as e:
            logger.exception("Startup script failed")
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
        logger.info("Skipping startup script (not first launch)")
        return

    logger.info("First launch detected, executing startup script")

    # Create and show the loading dialog / first-launch splash screen
    loading_dialog = LoadingDialog(
        "Downloading models and assets…",
        subtitle=(
            "First-time setup — this only happens once. "
            "VoxKit will start automatically when it finishes."
        ),
    )
    loading_dialog.show()

    # Process events multiple times to ensure the dialog is fully rendered
    for _ in range(3):
        app.processEvents()

    # Give the dialog time to render before starting work
    from PyQt6.QtCore import QTimer

    QTimer.singleShot(100, lambda: None)
    app.processEvents()

    # Create and start the worker thread
    worker = StartupScriptWorker(script)

    # Connect signals
    def on_finished():
        mark_first_launch_complete()
        loading_dialog.update_message("Setup complete — starting VoxKit…")
        loading_dialog.update_subtitle("")
        app.processEvents()
        loading_dialog.close_gracefully()

    def on_error(error_msg: str):
        logger.error("Startup script failed: %s", error_msg)
        loading_dialog.update_message(f"Error: {error_msg}")
        app.processEvents()
        # Do NOT mark first launch complete on error — allow retry on next launch
        QTimer.singleShot(2000, loading_dialog.close_gracefully)

    worker.finished.connect(on_finished)
    worker.error.connect(on_error)

    # Start the worker and wait for completion
    worker.start()
    loading_dialog.exec()
    worker.wait()


def execute_mfa_provisioning(app: QApplication) -> None:
    """Provision the bundled MFA environment when it isn't ready yet.

    Unlike :func:`execute_startup_script` this is *not* gated on the
    first-launch flag -- ``is_aligner_env_ready()`` is the gate. Provisioning
    used to run only inside the first-launch routine, so a single failure was
    permanent: the flag got marked complete regardless and the step never ran
    again. Here a failed or interrupted attempt is simply retried next launch.

    No-ops (without showing a dialog) when the platform has no bundled
    lockfile or the environment is already provisioned, which is every launch
    after setup succeeds once.

    Args:
        app: The QApplication instance for event processing
    """
    from voxkit.config.startup_config import ensure_mfa_environment
    from voxkit.services import mfa_provision

    if mfa_provision.lockfile_path() is None or mfa_provision.is_aligner_env_ready():
        return

    logger.info("MFA environment not provisioned; setting it up before showing the main window")

    loading_dialog = LoadingDialog(
        "Setting up the MFA alignment environment…",
        subtitle=(
            "One-time setup, about 1-2 GB. VoxKit will start automatically when it finishes."
        ),
    )
    loading_dialog.show()
    for _ in range(3):
        app.processEvents()

    worker = StartupScriptWorker(ensure_mfa_environment)

    def on_finished():
        # ensure_mfa_environment() reports its own outcome to the log and never
        # raises, so reaching here says nothing about whether setup succeeded.
        loading_dialog.close_gracefully()

    def on_error(error_msg: str):
        logger.error("MFA provisioning worker failed: %s", error_msg)
        loading_dialog.close_gracefully()

    worker.finished.connect(on_finished)
    worker.error.connect(on_error)

    worker.start()
    loading_dialog.exec()
    worker.wait()
