"""Read-only dialog that shows the tail of the rolling log file and appends
new records live via :class:`QObjectLogHandler`. Designed to be reusable
from other surfaces (Dataset page, per-process views) by swapping the
source file."""

from collections import deque
from pathlib import Path
from typing import Optional

from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
)

from voxkit.config.logging_config import LOG_FILE
from voxkit.gui.components.log_handler import get_gui_log_handler

_TAIL_LINES = 500


class LogViewerDialog(QDialog):
    """Dialog showing recent log output with live updates."""

    def __init__(
        self,
        parent=None,
        log_path: Optional[Path] = None,
    ) -> None:
        super().__init__(parent)
        self.log_path = log_path or LOG_FILE
        self.setWindowTitle("Application Log")
        self.setModal(False)
        self.resize(900, 500)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        self.text = QPlainTextEdit(self)
        self.text.setReadOnly(True)
        self.text.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        mono = QFont("Menlo")
        mono.setStyleHint(QFont.StyleHint.Monospace)
        mono.setPointSize(11)
        self.text.setFont(mono)
        layout.addWidget(self.text, stretch=1)

        button_row = QHBoxLayout()
        button_row.addStretch(1)
        self.close_button = QPushButton("Close", self)
        self.close_button.clicked.connect(self.accept)
        button_row.addWidget(self.close_button)
        layout.addLayout(button_row)

        self._load_tail()

        self._handler = get_gui_log_handler()
        self._handler.record_emitted.connect(self._append_line)

    def _load_tail(self) -> None:
        if not self.log_path.exists():
            self.text.setPlainText("(no log file yet)")
            return
        try:
            with open(self.log_path, "r", encoding="utf-8", errors="replace") as f:
                tail = deque(f, maxlen=_TAIL_LINES)
        except OSError as exc:
            self.text.setPlainText(f"(failed to read log file: {exc})")
            return
        self.text.setPlainText("".join(tail).rstrip("\n"))
        self._scroll_to_end()

    def _append_line(self, line: str) -> None:
        self.text.appendPlainText(line)
        self._scroll_to_end()

    def _scroll_to_end(self) -> None:
        bar = self.text.verticalScrollBar()
        if bar is not None:
            bar.setValue(bar.maximum())

    def closeEvent(self, event) -> None:  # noqa: N802 (Qt API)
        try:
            self._handler.record_emitted.disconnect(self._append_line)
        except TypeError:
            pass
        super().closeEvent(event)
