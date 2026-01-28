"""Workers Module.

QThread-based workers for executing long-running operations without blocking the UI.

API
---
- **WorkerThread**: Generic worker for executing arbitrary operations
- **DatasetRegistrationWorker**: Dataset validation, registration, and CSV analysis
- **ModelRegistrationWorker**: Model metadata creation and file copying

Notes
-----
- Workers emit ``finished(success, message)`` signals on completion
- Workers emit ``progress(message)`` signals for status updates
- All workers should be connected to handlers before calling ``start()``
"""

from .datasets_thread import DatasetRegistrationWorker
from .models_thread import ModelRegistrationWorker
from .worker_thread import WorkerThread

__all__ = ["WorkerThread", "DatasetRegistrationWorker", "ModelRegistrationWorker"]
