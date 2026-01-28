"""Worker Thread Module.

Generic QThread worker for executing arbitrary operations in a background thread.

API
---
- **WorkerThread**: Execute a callable without blocking the UI

Signals
-------
- ``finished(bool, str)``: Emitted on completion with (success, message)
"""

from PyQt6.QtCore import QThread, pyqtSignal


class WorkerThread(QThread):
    """Generic worker thread for non-blocking operations.

    Attributes:
        finished: Signal emitted on completion with (success, message).
        operation_func: The callable to execute in the background.
    """

    finished = pyqtSignal(bool, str)  # success, message

    def __init__(self, operation_func):
        super().__init__()
        self.operation_func = operation_func

    def run(self):
        try:
            result = self.operation_func()
            self.finished.emit(True, result if result else "Operation completed successfully")
        except Exception as e:
            self.finished.emit(False, str(e))
