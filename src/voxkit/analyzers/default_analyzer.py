"""Default Analyzer Module.

Built-in analyzer that extracts speaker and audio file counts from datasets.

Output Columns
--------------
- **speaker_id**: Name of the speaker subdirectory
- **audio_file_count**: Number of audio files in that speaker's directory

Notes
-----
- Expects MFA-style directory structure with speaker subdirectories
- Supported audio formats: .wav, .flac, .mp3, .ogg, .m4a
"""

import os
from pathlib import Path
from typing import Any, Dict, List

from .base import DatasetAnalyzer


class DefaultAnalyzer(DatasetAnalyzer):
    """Default analyzer extracting speaker and audio file counts per speaker."""

    @property
    def name(self) -> str:
        return "Default"

    @property
    def description(self) -> str:
        return "Speaker count and audio files per speaker"

    def analyze(self, dataset_path: str) -> List[Dict[str, Any]]:
        """
        Return a list of rows with speaker id and audio file count.

        Args:
            dataset_path (str): Path to the dataset root directory.

        Returns:
            List[Dict[str, Any]]: Each dict contains ``speaker_id`` and
            ``audio_file_count``.
        """
        results = []
        audio_extensions = {".wav", ".flac", ".mp3", ".ogg", ".m4a"}

        try:
            for entry in os.scandir(dataset_path):
                if entry.is_dir():
                    speaker_name = entry.name
                    audio_files = [
                        f
                        for f in os.scandir(entry.path)
                        if f.is_file() and Path(f.name).suffix.lower() in audio_extensions
                    ]

                    results.append(
                        {"speaker_id": speaker_name, "audio_file_count": len(audio_files)}
                    )
        except Exception as e:
            print(f"Error analyzing dataset: {e}")

        return results

    def visualize(self, data):
        from PyQt6.QtCore import QRectF, Qt
        from PyQt6.QtGui import QColor, QFont, QPainter
        from PyQt6.QtWidgets import QLabel, QScrollArea, QVBoxLayout, QWidget

        entries = []
        for row in data:
            speaker = str(row.get("speaker_id", ""))
            try:
                count = int(row.get("audio_file_count", 0))
            except (TypeError, ValueError):
                count = 0
            entries.append((speaker, count))
        entries.sort(key=lambda x: x[1], reverse=True)

        if not entries:
            empty = QLabel("No data to visualize.")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            return empty

        BAR_HEIGHT = 28
        BAR_SPACING = 6
        LABEL_WIDTH = 140
        PADDING = 16
        COUNT_WIDTH = 55
        max_count = max(c for _, c in entries) or 1
        total_h = PADDING + len(entries) * (BAR_HEIGHT + BAR_SPACING) + PADDING

        class _Canvas(QWidget):
            def __init__(self, parent=None):
                super().__init__(parent)
                self.setMinimumHeight(max(total_h, 100))
                self.setMinimumWidth(400)

            def paintEvent(self, event):
                painter = QPainter(self)
                painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                bar_area = self.width() - LABEL_WIDTH - PADDING * 2 - COUNT_WIDTH
                y = PADDING

                for speaker, count in entries:
                    painter.setPen(QColor("#2c3e50"))
                    label_font = QFont()
                    label_font.setPointSize(10)
                    painter.setFont(label_font)
                    label_rect = QRectF(PADDING, y, LABEL_WIDTH, BAR_HEIGHT)
                    fm = painter.fontMetrics()
                    elided = fm.elidedText(
                        speaker, Qt.TextElideMode.ElideRight, int(LABEL_WIDTH - 8)
                    )
                    painter.drawText(
                        label_rect,
                        Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                        elided,
                    )

                    bar_x = PADDING + LABEL_WIDTH + 10
                    bar_w = max((count / max_count) * bar_area, 2)
                    bar_rect = QRectF(bar_x, y + 3, bar_w, BAR_HEIGHT - 6)

                    color = QColor("#3498db")
                    h, s, lightness, a = color.getHsl()
                    ratio = count / max_count
                    new_l = int(lightness + (220 - lightness) * (1 - ratio))
                    color.setHsl(h, s, min(new_l, 240), a)

                    painter.setBrush(color)
                    painter.setPen(Qt.PenStyle.NoPen)
                    painter.drawRoundedRect(bar_rect, 4, 4)

                    count_font = QFont()
                    count_font.setPointSize(9)
                    count_font.setBold(True)
                    painter.setFont(count_font)
                    painter.setPen(QColor("#2c3e50"))
                    count_rect = QRectF(bar_x + bar_w + 6, y, COUNT_WIDTH, BAR_HEIGHT)
                    painter.drawText(
                        count_rect,
                        Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                        str(count),
                    )

                    y += BAR_HEIGHT + BAR_SPACING

                painter.end()

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        canvas = _Canvas()
        scroll = QScrollArea()
        scroll.setWidget(canvas)
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: white; }")
        layout.addWidget(scroll)

        total_speakers = len(entries)
        total_files = sum(c for _, c in entries)
        avg = total_files / total_speakers if total_speakers else 0
        stats = QLabel(
            f"{total_speakers} speakers  |  {total_files} audio files  |"
            f"  {avg:.1f} avg files/speaker"
        )
        stats.setStyleSheet("color: #7f8c8d; font-size: 12px; font-style: italic; padding: 8px;")
        stats.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(stats)

        return container
