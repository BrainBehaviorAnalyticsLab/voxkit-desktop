"""Clip Duration Statistics Analyzer.

Reads audio metadata (no decode) to compute per-speaker clip duration stats.

Output Columns
--------------
- **speaker_id**: Name of the speaker subdirectory
- **file_count**: Number of audio files scanned
- **total_duration_s**: Total audio duration in seconds
- **avg_duration_s**: Average clip duration in seconds
- **min_duration_s**: Shortest clip in seconds
- **max_duration_s**: Longest clip in seconds
"""

import logging
import os
from pathlib import Path
from typing import Any, Dict, List

from .base import DatasetAnalyzer

logger = logging.getLogger(__name__)


class ClipDurationStatisticsAnalyzer(DatasetAnalyzer):
    """Per-speaker clip duration statistics derived from audio file metadata."""

    @property
    def name(self) -> str:
        return "Clip Duration Statistics"

    @property
    def description(self) -> str:
        return "Total, average, min, and max clip duration per speaker"

    def analyze(self, dataset_path: str) -> List[Dict[str, Any]]:
        import torchaudio

        results = []
        audio_extensions = {".wav", ".flac", ".mp3", ".ogg", ".m4a"}

        try:
            for entry in os.scandir(dataset_path):
                if not entry.is_dir():
                    continue

                durations: List[float] = []
                for f in os.scandir(entry.path):
                    if not f.is_file() or Path(f.name).suffix.lower() not in audio_extensions:
                        continue
                    try:
                        info = torchaudio.info(f.path)
                        if info.num_frames > 0:
                            durations.append(info.num_frames / info.sample_rate)
                        else:
                            # num_frames is unreliable for some formats (MP3, M4A, OGG)
                            waveform, sr = torchaudio.load(f.path)
                            durations.append(waveform.shape[1] / sr)
                    except Exception as e:
                        logger.warning("Skipping %s: %s", f.path, e)

                if durations:
                    total = sum(durations)
                    results.append(
                        {
                            "speaker_id": entry.name,
                            "file_count": len(durations),
                            "total_duration_s": round(total, 2),
                            "avg_duration_s": round(total / len(durations), 2),
                            "min_duration_s": round(min(durations), 2),
                            "max_duration_s": round(max(durations), 2),
                        }
                    )
        except Exception as e:
            print(f"Error analyzing dataset: {e}")

        return results

    def visualize(self, data: List[Dict[str, Any]]):
        from PyQt6.QtCore import QRectF, Qt
        from PyQt6.QtGui import QColor, QFont, QPainter
        from PyQt6.QtWidgets import QLabel, QScrollArea, QVBoxLayout, QWidget

        entries = []
        for row in data:
            speaker = str(row.get("speaker_id", ""))
            try:
                total = float(row.get("total_duration_s", 0))
                avg = float(row.get("avg_duration_s", 0))
                file_count = int(row.get("file_count", 0))
            except (TypeError, ValueError):
                total, avg, file_count = 0.0, 0.0, 0
            entries.append((speaker, total, avg, file_count))
        entries.sort(key=lambda x: x[1], reverse=True)

        if not entries:
            empty = QLabel("No data to visualize.")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            return empty

        BAR_HEIGHT = 28
        BAR_SPACING = 6
        LABEL_WIDTH = 140
        PADDING = 16
        max_total = max(e[1] for e in entries) or 1
        VALUE_WIDTH = 120
        total_h = PADDING + len(entries) * (BAR_HEIGHT + BAR_SPACING) + PADDING

        class _Canvas(QWidget):
            def __init__(self, parent=None):
                super().__init__(parent)
                self.setMinimumHeight(max(total_h, 100))
                self.setMinimumWidth(400)

            def paintEvent(self, event):
                painter = QPainter(self)
                painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                bar_area = self.width() - LABEL_WIDTH - PADDING * 2 - VALUE_WIDTH
                y = PADDING

                for speaker, total, avg, file_count in entries:
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
                    bar_w = max((total / max_total) * bar_area, 2)
                    bar_rect = QRectF(bar_x, y + 3, bar_w, BAR_HEIGHT - 6)

                    color = QColor("#27ae60")
                    h, s, lightness, a = color.getHsl()
                    assert h is not None and s is not None and lightness is not None
                    ratio = total / max_total
                    new_l = int(lightness + (220 - lightness) * (1 - ratio))
                    color.setHsl(h, s, min(new_l, 240), a)

                    painter.setBrush(color)
                    painter.setPen(Qt.PenStyle.NoPen)
                    painter.drawRoundedRect(bar_rect, 4, 4)

                    val_font = QFont()
                    val_font.setPointSize(9)
                    val_font.setBold(True)
                    painter.setFont(val_font)
                    painter.setPen(QColor("#2c3e50"))
                    minutes, seconds = divmod(total, 60)
                    label = f"{int(minutes)}m {seconds:.0f}s  ({file_count} files)"
                    val_rect = QRectF(bar_x + bar_w + 6, y, VALUE_WIDTH, BAR_HEIGHT)
                    painter.drawText(
                        val_rect,
                        Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                        label,
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

        grand_total = sum(e[1] for e in entries)
        total_files = sum(e[3] for e in entries)
        n_speakers = len(entries)
        overall_avg = grand_total / n_speakers if n_speakers else 0
        gt_min, gt_sec = divmod(grand_total, 60)
        stats = QLabel(
            f"{n_speakers} speakers  |  "
            f"{total_files} files  |  "
            f"Total: {int(gt_min)}m {gt_sec:.0f}s  |  "
            f"Avg per speaker: {overall_avg:.1f}s"
        )
        stats.setStyleSheet("color: #7f8c8d; font-size: 12px; font-style: italic; padding: 8px;")
        stats.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(stats)

        return container
