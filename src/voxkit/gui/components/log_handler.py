"""Bridges stdlib :mod:`logging` into Qt's signal/slot system so dialogs and
widgets can subscribe to live log output without polling the log file."""

import logging

from PyQt6.QtCore import QObject, pyqtSignal


class QObjectLogHandler(logging.Handler, QObject):
    """Logging handler that re-emits formatted records via a Qt signal."""

    record_emitted = pyqtSignal(str)

    def __init__(self, level: int = logging.INFO) -> None:
        logging.Handler.__init__(self, level=level)
        QObject.__init__(self)
        self.setFormatter(
            logging.Formatter(
                "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )

    def emit(self, record: logging.LogRecord) -> None:
        try:
            message = self.format(record)
        except Exception:
            self.handleError(record)
            return
        self.record_emitted.emit(message)


_global_handler: QObjectLogHandler | None = None


def get_gui_log_handler() -> QObjectLogHandler:
    """Return the process-wide GUI log handler, attaching it on first call."""
    global _global_handler
    if _global_handler is None:
        _global_handler = QObjectLogHandler()
        logging.getLogger().addHandler(_global_handler)
    return _global_handler
