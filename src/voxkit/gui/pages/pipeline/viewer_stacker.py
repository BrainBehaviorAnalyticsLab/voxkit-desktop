"""Viewer Stacker Module.

Pipeline page for browsing alignment results — synchronized view of TextGrid
tiers, transcript, and audio playback for any speaker/file in a registered
alignment.

API
---
- **TextGridTimeline**: Custom painted widget rendering TextGrid tiers as a
  time-aligned view with a live playhead and click-to-seek.
- **ViewerStacker**: Alignment viewer workflow UI
"""

import re
import subprocess
import sys
from pathlib import Path

from PyQt6.QtCore import Qt, QPoint, QUrl, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPainter, QPen, QPolygon
from PyQt6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QSizePolicy,
    QSlider,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from voxkit.gui.components import MultiColumnComboBox
from voxkit.gui.pages.pipeline.base_stacker import BaseStacker
from voxkit.gui.styles import Buttons, Colors, Containers, Labels
from voxkit.storage import alignments, datasets
from voxkit.storage.datasets import _get_dataset_root

try:
    from PyQt6.QtMultimedia import QAudioOutput, QMediaPlayer

    MULTIMEDIA_AVAILABLE = True
except ImportError:
    MULTIMEDIA_AVAILABLE = False


_AUDIO_EXTENSIONS = {".wav", ".flac", ".mp3", ".ogg", ".m4a"}
_SILENCE_LABELS = {"", "sp", "sil", "<eps>", "spn"}

# ---------------------------------------------------------------------------
# TextGrid parser
# ---------------------------------------------------------------------------


def _parse_textgrid(filepath: str) -> list[dict]:
    """Parse a Praat TextGrid file into a list of tier dicts.

    Each tier dict has keys: ``name``, ``class``, ``intervals`` (list of dicts
    with ``start``/``end``/``label`` for IntervalTier, or ``time``/``label``
    for TextTier).
    """
    try:
        with open(filepath, "r", encoding="utf-8-sig") as f:
            content = f.read()
    except UnicodeDecodeError:
        with open(filepath, "r", encoding="latin-1") as f:
            content = f.read()

    tiers: list[dict] = []
    tier_blocks = re.split(r"item\s*\[\d+\]:", content)[1:]

    for block in tier_blocks:
        name_m = re.search(r'name\s*=\s*"([^"]*)"', block)
        class_m = re.search(r'class\s*=\s*"([^"]*)"', block)

        tier: dict = {
            "name": name_m.group(1) if name_m else "unknown",
            "class": class_m.group(1) if class_m else "unknown",
            "intervals": [],
        }

        if "IntervalTier" in tier["class"]:
            for ib in re.split(r"intervals\s*\[\d+\]:", block)[1:]:
                xmin = re.search(r"xmin\s*=\s*([0-9.e+\-]+)", ib)
                xmax = re.search(r"xmax\s*=\s*([0-9.e+\-]+)", ib)
                text = re.search(r'text\s*=\s*"([^"]*)"', ib)
                if xmin and xmax and text:
                    tier["intervals"].append(
                        {
                            "start": float(xmin.group(1)),
                            "end": float(xmax.group(1)),
                            "label": text.group(1),
                        }
                    )
        elif "TextTier" in tier["class"]:
            for pb in re.split(r"points\s*\[\d+\]:", block)[1:]:
                time = re.search(r"time\s*=\s*([0-9.e+\-]+)", pb)
                mark = re.search(r'mark\s*=\s*"([^"]*)"', pb)
                if time and mark:
                    tier["intervals"].append(
                        {"time": float(time.group(1)), "label": mark.group(1)}
                    )

        tiers.append(tier)

    return tiers


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------


def _dataset_data_path(meta: dict) -> Path:
    """Return the directory containing speaker subdirs (audio + .lab files)."""
    if meta.get("cached"):
        root = _get_dataset_root(meta["id"])
        if root:
            return root / "cache"
    return Path(meta["original_path"])


def _find_textgrid(tg_root: Path, speaker: str, stem: str) -> Path | None:
    """Probe common TextGrid layouts and return the first match."""
    candidates = [
        tg_root / speaker / f"{stem}.TextGrid",
        tg_root / f"{stem}.TextGrid",
        tg_root / "cache" / speaker / f"{stem}.TextGrid",
        tg_root / "cache" / f"{stem}.TextGrid",
    ]
    return next((c for c in candidates if c.exists()), None)


def _find_lab(data_root: Path, speaker: str, stem: str) -> Path | None:
    """Return the transcript file (.lab or .txt) for the given audio stem."""
    for ext in (".lab", ".txt"):
        p = data_root / speaker / f"{stem}{ext}"
        if p.exists():
            return p
    return None


# ---------------------------------------------------------------------------
# TextGridTimeline
# ---------------------------------------------------------------------------


class TextGridTimeline(QWidget):
    """Custom painted widget showing TextGrid tiers as a synchronized timeline.

    - One row per tier, each with time-scaled labeled interval blocks.
    - A vertical red playhead tracks the current audio position.
    - Clicking anywhere emits ``seek_requested`` with the target time in seconds.
    """

    seek_requested = pyqtSignal(float)  # seconds

    TIER_HEIGHT = 36
    RULER_HEIGHT = 26
    LEFT_MARGIN = 92   # space reserved for tier name labels
    RIGHT_MARGIN = 8

    # Fixed colors for well-known tier names (case-insensitive match)
    _TIER_COLOR_MAP: dict[str, QColor] = {
        "words": QColor("#3498db"),   # blue
        "phones": QColor("#27ae60"),  # green
    }

    # Fallback palette for unknown tiers (indexed by position after known tiers)
    _TIER_COLORS = [
        QColor("#e67e22"),  # orange
        QColor("#9b59b6"),  # purple
        QColor("#16a085"),  # teal
        QColor("#c0392b"),  # red
        QColor("#2980b9"),  # dark blue
        QColor("#8e44ad"),  # dark purple
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._tiers: list[dict] = []
        self._duration: float = 0.0
        self._current_time: float = 0.0
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setFixedHeight(self.RULER_HEIGHT)

    _TIER_ORDER = {"phones": 0, "words": 1}

    def set_data(self, tiers: list[dict], duration: float) -> None:
        self._tiers = sorted(
            tiers,
            key=lambda t: self._TIER_ORDER.get(t["name"].lower(), 2),
        )
        self._duration = duration
        self._current_time = 0.0
        self.setFixedHeight(self.RULER_HEIGHT + max(1, len(tiers)) * self.TIER_HEIGHT)
        self.update()

    def set_current_time(self, seconds: float) -> None:
        if abs(seconds - self._current_time) > 0.008:
            self._current_time = seconds
            self.update()

    def clear(self) -> None:
        self._tiers = []
        self._duration = 0.0
        self._current_time = 0.0
        self.setFixedHeight(self.RULER_HEIGHT)
        self.update()

    # ── coordinate conversion ─────────────────────────────────────────────────

    def _time_to_x(self, t: float) -> int:
        if self._duration <= 0:
            return self.LEFT_MARGIN
        span = self.width() - self.LEFT_MARGIN - self.RIGHT_MARGIN
        return self.LEFT_MARGIN + int(t / self._duration * span)

    def _x_to_time(self, x: float) -> float:
        span = self.width() - self.LEFT_MARGIN - self.RIGHT_MARGIN
        if span <= 0:
            return 0.0
        return max(0.0, min(self._duration, (x - self.LEFT_MARGIN) / span * self._duration))

    # ── painting ──────────────────────────────────────────────────────────────

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        w, h = self.width(), self.height()

        # Overall background
        painter.fillRect(0, 0, w, h, QColor("#f8f9fa"))

        # ── Ruler ─────────────────────────────────────────────────────────────
        painter.fillRect(0, 0, w, self.RULER_HEIGHT, QColor("#2c3e50"))

        if self._duration > 0:
            ruler_font = QFont()
            ruler_font.setPointSize(8)
            ruler_font.setFamily("Courier")
            painter.setFont(ruler_font)
            painter.setPen(QColor("#ecf0f1"))

            available = w - self.LEFT_MARGIN - self.RIGHT_MARGIN
            approx_ticks = max(2, available // 72)
            raw_step = self._duration / approx_ticks
            for nice in (0.05, 0.1, 0.2, 0.5, 1, 2, 5, 10, 30, 60):
                if raw_step <= nice:
                    step = nice
                    break
            else:
                step = raw_step

            t = 0.0
            while t <= self._duration + step * 0.01:
                x = self._time_to_x(t)
                painter.drawLine(x, self.RULER_HEIGHT - 5, x, self.RULER_HEIGHT)
                lbl = f"{t:.2f}s" if t < 1 else (
                    f"{t:.1f}s" if t < 60 else f"{int(t // 60)}:{int(t % 60):02d}"
                )
                painter.drawText(
                    x - 26, 1, 52, self.RULER_HEIGHT - 6,
                    Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter,
                    lbl,
                )
                t += step
                if t > self._duration * 20:
                    break

        # Left margin background
        painter.fillRect(
            0, self.RULER_HEIGHT,
            self.LEFT_MARGIN, h - self.RULER_HEIGHT,
            QColor("#ecf0f1"),
        )
        painter.setPen(QPen(QColor("#bdc3c7"), 1))
        painter.drawLine(self.LEFT_MARGIN, self.RULER_HEIGHT, self.LEFT_MARGIN, h)

        # ── Tiers ─────────────────────────────────────────────────────────────
        name_font = QFont()
        name_font.setPointSize(8)
        name_font.setBold(True)
        iv_font = QFont()
        iv_font.setPointSize(8)

        fallback_idx = 0
        for idx, tier in enumerate(self._tiers):
            y = self.RULER_HEIGHT + idx * self.TIER_HEIGHT
            tier_key = tier["name"].lower()
            if tier_key in self._TIER_COLOR_MAP:
                color = self._TIER_COLOR_MAP[tier_key]
            else:
                color = self._TIER_COLORS[fallback_idx % len(self._TIER_COLORS)]
                fallback_idx += 1
            is_interval = tier["class"] == "IntervalTier"

            # Alternating row background
            row_bg = QColor("#ffffff") if idx % 2 == 0 else QColor("#f5f6fa")
            painter.fillRect(self.LEFT_MARGIN, y, w - self.LEFT_MARGIN, self.TIER_HEIGHT, row_bg)

            # Tier name
            painter.setFont(name_font)
            painter.setPen(color.darker(150))
            painter.drawText(
                4, y, self.LEFT_MARGIN - 6, self.TIER_HEIGHT,
                Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                tier["name"],
            )

            # Intervals
            painter.setFont(iv_font)
            pad = 2
            for iv in tier.get("intervals", []):
                if is_interval:
                    t_start, t_end = iv["start"], iv["end"]
                    iv_label = iv["label"]
                else:
                    t_start = t_end = iv["time"]
                    iv_label = iv["label"]

                x1 = self._time_to_x(t_start)
                x2 = self._time_to_x(t_end) if is_interval else x1 + 3
                bw = max(1, x2 - x1)

                active = is_interval and t_start <= self._current_time < t_end
                silent = iv_label in _SILENCE_LABELS

                if active:
                    fill = color
                elif silent:
                    fill = color.lighter(195)
                else:
                    fill = color.lighter(155)

                painter.fillRect(x1, y + pad, bw, self.TIER_HEIGHT - pad * 2, fill)

                # Block border
                painter.setPen(QPen(color.darker(115) if active else color.lighter(120), 0.5))
                painter.drawRect(x1, y + pad, bw, self.TIER_HEIGHT - pad * 2)

                # Label inside block
                if bw > 10 and iv_label:
                    text_color = (
                        QColor("white") if (active or not silent)
                        else color.darker(140)
                    )
                    painter.setPen(text_color)
                    painter.drawText(
                        x1 + 2, y + pad, bw - 4, self.TIER_HEIGHT - pad * 2,
                        Qt.AlignmentFlag.AlignCenter,
                        iv_label,
                    )

            # Row bottom border
            painter.setPen(QPen(QColor("#dde1e7"), 1))
            painter.drawLine(self.LEFT_MARGIN, y + self.TIER_HEIGHT, w, y + self.TIER_HEIGHT)

        # ── Playhead ──────────────────────────────────────────────────────────
        if self._duration > 0:
            px = self._time_to_x(self._current_time)
            painter.setPen(QPen(QColor("#e74c3c"), 2))
            painter.drawLine(px, 0, px, h)

            # Small downward triangle at ruler
            ts = 5
            painter.setBrush(QColor("#e74c3c"))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawPolygon(
                QPolygon([QPoint(px - ts, 0), QPoint(px + ts, 0), QPoint(px, ts * 2)])
            )

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self._duration > 0:
            self.seek_requested.emit(self._x_to_time(event.position().x()))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update()


# ---------------------------------------------------------------------------
# ViewerStacker
# ---------------------------------------------------------------------------


class ViewerStacker(BaseStacker):
    """Alignment viewer pipeline page.

    Walk through: dataset → alignment → speaker → audio file, then display a
    synchronized view of the TextGrid tiers (as a time-scaled interactive
    timeline), the full transcript, and audio playback controls — all visible
    at once.
    """

    def __init__(self, parent=None):
        # Pre-declare all attributes so build_ui() (called by super().__init__)
        # can reference them safely.
        self._dataset_dropdown: MultiColumnComboBox | None = None
        self._alignment_dropdown: MultiColumnComboBox | None = None
        self._speaker_dropdown: QComboBox | None = None
        self._file_list: QListWidget | None = None
        self._file_search = None          # QLineEdit, set in build_ui
        self._all_audio_files: list[str] = []
        self._selection_section: QWidget | None = None
        self._viewer_section: QWidget | None = None
        self._timeline: TextGridTimeline | None = None
        self._active_label: QLabel | None = None
        self._transcript_edit: QTextEdit | None = None
        self._audio_path_label: QLabel | None = None
        self._current_dataset_meta: dict | None = None
        self._current_alignment_meta: dict | None = None
        self._current_data_path: Path | None = None
        self._current_audio_path: Path | None = None
        self._loaded_tiers: list[dict] = []
        # Multimedia (may remain None if QtMultimedia is unavailable)
        self._player = None
        self._audio_output = None
        self._play_btn: QPushButton | None = None
        self._seek_slider: QSlider | None = None
        self._time_label: QLabel | None = None
        super().__init__(parent)

    # ── BaseStacker overrides ────────────────────────────────────────────────

    def get_title(self) -> str:
        return "Alignment Viewer"

    def has_status_label(self) -> bool:
        return True

    def build_ui(self):
        # ── ① Dataset ────────────────────────────────────────────────────────
        self.content_layout.addWidget(self._make_section_label("① Choose a Dataset"))

        self._dataset_dropdown = MultiColumnComboBox()
        self._dataset_dropdown.setStyleSheet(Containers.COMBOBOX_STANDARD)
        self._dataset_dropdown.currentIndexChanged.connect(self._on_dataset_changed)
        self.content_layout.addWidget(self._dataset_dropdown)

        # ── ② Alignment ──────────────────────────────────────────────────────
        self.content_layout.addWidget(self._make_section_label("② Choose an Alignment"))

        self._alignment_dropdown = MultiColumnComboBox()
        self._alignment_dropdown.setStyleSheet(Containers.COMBOBOX_STANDARD)
        self._alignment_dropdown.set_data(
            [{"id": None, "data": ("Select a dataset first", "", "", "")}],
            ["Engine", "Model", "Date", "Status"],
            placeholder="Select a dataset first",
        )
        self._alignment_dropdown.setEnabled(False)
        self._alignment_dropdown.currentIndexChanged.connect(self._on_alignment_changed)
        self.content_layout.addWidget(self._alignment_dropdown)

        # ── ③/④ Speaker + File (hidden until alignment selected) ─────────────
        self._selection_section = QWidget()
        sel_col = QVBoxLayout(self._selection_section)
        sel_col.setContentsMargins(0, 4, 0, 0)
        sel_col.setSpacing(4)

        # Labels row — same stretch ratios as the controls row below so the
        # ③ and ④ numbers land at the same x-positions as ① and ②.
        lbl_row = QHBoxLayout()
        lbl_row.setContentsMargins(0, 0, 0, 0)
        lbl_row.setSpacing(12)
        lbl_row.addWidget(self._make_section_label("③ Speaker"), stretch=1)
        lbl_row.addWidget(self._make_section_label("④ Audio File"), stretch=2)
        sel_col.addLayout(lbl_row)

        # Controls row
        ctrl_row = QHBoxLayout()
        ctrl_row.setContentsMargins(0, 0, 0, 0)
        ctrl_row.setSpacing(12)

        self._speaker_dropdown = QComboBox()
        self._speaker_dropdown.setStyleSheet(Containers.COMBOBOX_STANDARD)
        self._speaker_dropdown.currentTextChanged.connect(self._on_speaker_changed)

        spk_wrapper = QVBoxLayout()
        spk_wrapper.setContentsMargins(0, 0, 0, 0)
        spk_wrapper.setSpacing(0)
        spk_wrapper.addWidget(self._speaker_dropdown)
        spk_wrapper.addStretch()
        ctrl_row.addLayout(spk_wrapper, stretch=1)

        file_controls = QVBoxLayout()
        file_controls.setContentsMargins(0, 0, 0, 0)
        file_controls.setSpacing(4)

        self._file_search = QLineEdit()
        self._file_search.setPlaceholderText("Search files...")
        self._file_search.setClearButtonEnabled(True)
        self._file_search.setStyleSheet(
            f"QLineEdit {{ border: 1px solid {Colors.BORDER}; border-radius: 4px; "
            f"padding: 4px 6px; font-size: 12px; background: white; }}"
            f"QLineEdit:focus {{ border-color: {Colors.PRIMARY}; }}"
        )
        self._file_search.textChanged.connect(self._filter_file_list)
        file_controls.addWidget(self._file_search)

        self._file_list = QListWidget()
        self._file_list.setFixedHeight(96)
        self._file_list.setStyleSheet(Containers.TABLE_WIDGET)
        self._file_list.currentItemChanged.connect(self._on_file_selected)
        file_controls.addWidget(self._file_list)

        ctrl_row.addLayout(file_controls, stretch=2)
        sel_col.addLayout(ctrl_row)

        self._selection_section.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum
        )
        self._selection_section.setVisible(False)
        self.content_layout.addWidget(self._selection_section)

        # ── Viewer (hidden until file selected) ──────────────────────────────
        self._viewer_section = QWidget()
        view_col = QVBoxLayout(self._viewer_section)
        view_col.setContentsMargins(0, 6, 0, 0)
        view_col.setSpacing(4)

        # Audio controls row ──────────────────────────────────────────────────
        audio_row = QHBoxLayout()
        audio_row.setSpacing(8)

        self._audio_path_label = QLabel("No file selected")
        self._audio_path_label.setStyleSheet(Labels.INFO_SMALL)
        self._audio_path_label.setWordWrap(True)
        audio_row.addWidget(self._audio_path_label, stretch=1)

        if MULTIMEDIA_AVAILABLE:
            self._play_btn = QPushButton("▶  Play")
            self._play_btn.setFixedWidth(82)
            self._play_btn.setStyleSheet(Buttons.PRIMARY)
            self._play_btn.clicked.connect(self._toggle_playback)
            audio_row.addWidget(self._play_btn)

            stop_btn = QPushButton("■  Stop")
            stop_btn.setFixedWidth(72)
            stop_btn.setStyleSheet(Buttons.SECONDARY)
            stop_btn.clicked.connect(self._stop_playback)
            audio_row.addWidget(stop_btn)

            self._time_label = QLabel("0:00 / 0:00")
            self._time_label.setStyleSheet(Labels.INFO_SMALL)
            self._time_label.setFixedWidth(92)
            audio_row.addWidget(self._time_label)
        else:
            open_btn = QPushButton("Open Audio")
            open_btn.setFixedWidth(100)
            open_btn.setStyleSheet(Buttons.SECONDARY)
            open_btn.clicked.connect(self._open_audio_externally)
            audio_row.addWidget(open_btn)

        view_col.addLayout(audio_row)

        if MULTIMEDIA_AVAILABLE:
            self._seek_slider = QSlider(Qt.Orientation.Horizontal)
            self._seek_slider.setRange(0, 0)
            self._seek_slider.sliderMoved.connect(self._seek_to_ms)
            view_col.addWidget(self._seek_slider)

        # TextGrid timeline ───────────────────────────────────────────────────
        tg_header = QHBoxLayout()
        tg_header.setContentsMargins(0, 4, 0, 0)
        tg_lbl = QLabel("TextGrid Alignment")
        tg_lbl.setStyleSheet(Labels.SECTION_LABEL)
        tg_header.addWidget(tg_lbl)
        tg_header.addStretch()
        view_col.addLayout(tg_header)

        self._timeline = TextGridTimeline()
        self._timeline.seek_requested.connect(self._seek_to_seconds)
        self._timeline.setStyleSheet(
            f"border: 1px solid {Colors.BORDER}; border-radius: 4px;"
        )
        view_col.addWidget(self._timeline)

        # Active-segment indicator ────────────────────────────────────────────
        self._active_label = QLabel("")
        self._active_label.setStyleSheet(
            f"QLabel {{ font-size: 12px; font-weight: bold; color: {Colors.PRIMARY}; "
            f"background-color: #ebf5fb; border-left: 3px solid {Colors.PRIMARY}; "
            f"border-radius: 3px; padding: 3px 8px; }}"
        )
        self._active_label.setWordWrap(True)
        self._active_label.setVisible(False)
        view_col.addWidget(self._active_label)

        # Transcript ──────────────────────────────────────────────────────────
        tr_lbl = QLabel("Transcript")
        tr_lbl.setStyleSheet(Labels.SECTION_LABEL)
        view_col.addWidget(tr_lbl)

        self._transcript_edit = QTextEdit()
        self._transcript_edit.setReadOnly(True)
        self._transcript_edit.setFixedHeight(72)
        self._transcript_edit.setPlaceholderText("No transcript (.lab) found for this file")
        self._transcript_edit.setStyleSheet(
            f"QTextEdit {{ border: 1px solid {Colors.BORDER}; border-radius: 4px; "
            f"padding: 6px; font-size: 13px; background: white; }}"
        )
        view_col.addWidget(self._transcript_edit)

        self._viewer_section.setVisible(False)
        self.content_layout.addWidget(self._viewer_section)

        # Initialise multimedia player ────────────────────────────────────────
        if MULTIMEDIA_AVAILABLE:
            self._audio_output = QAudioOutput()
            self._player = QMediaPlayer()
            self._player.setAudioOutput(self._audio_output)
            self._player.playbackStateChanged.connect(self._on_playback_state_changed)
            self._player.positionChanged.connect(self._on_position_changed)
            self._player.durationChanged.connect(self._on_duration_changed)

        self.reload_datasets()

    # ── Reload hooks ─────────────────────────────────────────────────────────

    def reload_datasets(self):
        """Refresh the dataset dropdown from storage."""
        if self._dataset_dropdown is None:
            return

        self._dataset_dropdown.clear()
        metas = datasets.list_datasets_metadata()
        if metas:
            rows = [
                {"id": m["id"], "data": (m["name"], m["registration_date"], m["description"])}
                for m in metas
            ]
            self._dataset_dropdown.set_data(
                rows, ["Name", "Date", "Description"], placeholder="Select a dataset"
            )
            self._dataset_dropdown.setEnabled(True)
        else:
            self._dataset_dropdown.set_data(
                [{"id": None, "data": ("No datasets registered", "", "")}],
                ["Name", "Date", "Description"],
                placeholder="No datasets registered",
            )
            self._dataset_dropdown.setEnabled(False)

        if self._alignment_dropdown:
            self._alignment_dropdown.set_data(
                [{"id": None, "data": ("Select a dataset first", "", "", "")}],
                ["Engine", "Model", "Date", "Status"],
                placeholder="Select a dataset first",
            )
            self._alignment_dropdown.setEnabled(False)

        if self._selection_section:
            self._selection_section.setVisible(False)
        if self._viewer_section:
            self._viewer_section.setVisible(False)

    # ── Selection handlers ───────────────────────────────────────────────────

    def _on_dataset_changed(self):
        dataset_id = self._dataset_dropdown.itemData(self._dataset_dropdown.currentIndex())

        self._selection_section.setVisible(False)
        self._viewer_section.setVisible(False)
        self._alignment_dropdown.clear()

        if not dataset_id:
            self._alignment_dropdown.set_data(
                [{"id": None, "data": ("Select a dataset first", "", "", "")}],
                ["Engine", "Model", "Date", "Status"],
                placeholder="Select a dataset first",
            )
            self._alignment_dropdown.setEnabled(False)
            return

        self._current_dataset_meta = datasets.get_dataset_metadata(dataset_id)
        if not self._current_dataset_meta:
            return

        self._current_data_path = _dataset_data_path(self._current_dataset_meta)

        al_list = alignments.list_alignments(dataset_id)
        if al_list:
            rows = [
                {
                    "id": a["id"],
                    "data": (
                        a["engine_id"],
                        a["model_metadata"]["name"],
                        a["alignment_date"],
                        a["status"],
                    ),
                }
                for a in al_list
            ]
            self._alignment_dropdown.set_data(
                rows, ["Engine", "Model", "Date", "Status"], placeholder="Select an alignment"
            )
            self._alignment_dropdown.setEnabled(True)
        else:
            self._alignment_dropdown.set_data(
                [{"id": None, "data": ("No alignments found", "", "", "")}],
                ["Engine", "Model", "Date", "Status"],
                placeholder="No alignments found",
            )
            self._alignment_dropdown.setEnabled(False)

    def _on_alignment_changed(self):
        alignment_id = self._alignment_dropdown.itemData(self._alignment_dropdown.currentIndex())

        self._selection_section.setVisible(False)
        self._viewer_section.setVisible(False)

        if not alignment_id or not self._current_dataset_meta:
            return

        meta = alignments.get_alignment_metadata(
            self._current_dataset_meta["id"], alignment_id
        )
        if not meta:
            return

        self._current_alignment_meta = meta
        self._populate_speakers()
        self._selection_section.setVisible(True)
        self.set_status("Select a speaker and audio file to view alignment", "ready")

    def _populate_speakers(self):
        self._speaker_dropdown.clear()
        if not self._current_data_path or not self._current_data_path.exists():
            return
        speakers = sorted(
            d.name
            for d in self._current_data_path.iterdir()
            if d.is_dir() and not d.name.startswith(".")
        )
        self._speaker_dropdown.addItems(speakers)

    def _on_speaker_changed(self, speaker: str):
        self._file_list.clear()
        self._all_audio_files = []
        self._viewer_section.setVisible(False)
        if self._file_search:
            self._file_search.blockSignals(True)
            self._file_search.clear()
            self._file_search.blockSignals(False)

        if not speaker or not self._current_data_path:
            return

        spk_path = self._current_data_path / speaker
        if not spk_path.exists():
            return

        self._all_audio_files = sorted(
            f.name for f in spk_path.iterdir() if f.suffix.lower() in _AUDIO_EXTENSIONS
        )
        self._file_list.addItems(self._all_audio_files)

    def _filter_file_list(self, query: str):
        """Show only files whose names contain the search query (case-insensitive)."""
        self._file_list.clear()
        q = query.strip().lower()
        matches = [f for f in self._all_audio_files if q in f.lower()] if q else self._all_audio_files
        self._file_list.addItems(matches)
        # Hide viewer if the previously selected file is no longer visible
        if self._viewer_section and self._viewer_section.isVisible():
            self._viewer_section.setVisible(False)

    def _on_file_selected(self, item, _prev=None):
        if not item:
            self._viewer_section.setVisible(False)
            return

        speaker = self._speaker_dropdown.currentText()
        filename = item.text()
        stem = Path(filename).stem

        if not self._current_data_path or not self._current_alignment_meta:
            return

        audio_path = self._current_data_path / speaker / filename
        tg_root = Path(self._current_alignment_meta["tg_path"])
        lab_path = _find_lab(self._current_data_path, speaker, stem)
        tg_path = _find_textgrid(tg_root, speaker, stem)

        self._load_viewer(audio_path, lab_path, tg_path)
        self._viewer_section.setVisible(True)

    # ── Viewer loading ────────────────────────────────────────────────────────

    def _load_viewer(
        self,
        audio_path: Path,
        lab_path: Path | None,
        tg_path: Path | None,
    ):
        """Populate audio player, timeline, active-segment label, and transcript."""
        # ── Audio ─────────────────────────────────────────────────────────────
        if audio_path.exists():
            self._audio_path_label.setText(str(audio_path))
            self._current_audio_path = audio_path
            if MULTIMEDIA_AVAILABLE and self._player:
                if self._player.playbackState() != QMediaPlayer.PlaybackState.StoppedState:
                    self._player.stop()
                self._player.setSource(QUrl.fromLocalFile(str(audio_path)))
                if self._play_btn:
                    self._play_btn.setText("▶  Play")
        else:
            self._audio_path_label.setText(f"Audio not found: {audio_path}")
            self._current_audio_path = None

        # ── Transcript ────────────────────────────────────────────────────────
        if lab_path and lab_path.exists():
            self._transcript_edit.setPlainText(lab_path.read_text(encoding="utf-8").strip())
        else:
            self._transcript_edit.setPlainText("")
            self._transcript_edit.setPlaceholderText(
                f"No .lab/.txt transcript found for {audio_path.stem}"
            )

        # ── TextGrid timeline ─────────────────────────────────────────────────
        self._loaded_tiers = []
        self._timeline.clear()
        self._active_label.setVisible(False)

        if tg_path and tg_path.exists():
            try:
                tiers = _parse_textgrid(str(tg_path))
                if tiers:
                    # Derive duration from the last interval's end time
                    duration = 0.0
                    for tier in tiers:
                        if tier["class"] == "IntervalTier" and tier["intervals"]:
                            duration = max(duration, tier["intervals"][-1]["end"])
                    if duration <= 0 and MULTIMEDIA_AVAILABLE and self._player:
                        duration = self._player.duration() / 1000.0

                    self._loaded_tiers = tiers
                    self._timeline.set_data(tiers, duration)
                    self._active_label.setVisible(True)
            except Exception as exc:
                self._audio_path_label.setText(
                    f"{self._audio_path_label.text()}  [TextGrid parse error: {exc}]"
                )
        else:
            self._audio_path_label.setText(
                self._audio_path_label.text()
                + f"  [TextGrid not found in {Path(self._current_alignment_meta['tg_path'])}]"
            )

        # ── Status ────────────────────────────────────────────────────────────
        parts = []
        if audio_path.exists():
            parts.append("audio ready")
        if lab_path and lab_path.exists():
            parts.append("transcript loaded")
        if self._loaded_tiers:
            parts.append(f"TextGrid loaded ({len(self._loaded_tiers)} tiers)")
        self.set_status(" · ".join(parts) if parts else "File loaded", "success")

    # ── Audio player ──────────────────────────────────────────────────────────

    def _toggle_playback(self):
        if not self._player:
            return
        if self._player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self._player.pause()
        else:
            self._player.play()

    def _stop_playback(self):
        if self._player:
            self._player.stop()

    def _seek_to_ms(self, ms: int):
        if self._player:
            self._player.setPosition(ms)

    def _seek_to_seconds(self, seconds: float):
        if self._player:
            self._player.setPosition(int(seconds * 1000))

    def _on_playback_state_changed(self, state):
        if self._play_btn is None:
            return
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self._play_btn.setText("⏸  Pause")
        else:
            self._play_btn.setText("▶  Play")

    def _on_position_changed(self, position_ms: int):
        # Update seek slider
        if self._seek_slider:
            self._seek_slider.blockSignals(True)
            self._seek_slider.setValue(position_ms)
            self._seek_slider.blockSignals(False)

        # Update time label
        if self._time_label and self._player:
            self._time_label.setText(
                f"{self._fmt_ms(position_ms)} / {self._fmt_ms(self._player.duration())}"
            )

        # Advance timeline playhead
        secs = position_ms / 1000.0
        if self._timeline:
            self._timeline.set_current_time(secs)

        # Update active-segment label
        if self._active_label and self._active_label.isVisible() and self._loaded_tiers:
            parts = []
            for tier in self._loaded_tiers:
                if tier["class"] == "IntervalTier":
                    for iv in tier["intervals"]:
                        if iv["start"] <= secs < iv["end"] and iv["label"] not in _SILENCE_LABELS:
                            parts.append(f"{tier['name']}: {iv['label']}")
                            break
            self._active_label.setText("  |  ".join(parts))

    def _on_duration_changed(self, duration_ms: int):
        if self._seek_slider:
            self._seek_slider.setRange(0, duration_ms)
        # Update timeline duration if tiers didn't provide a reliable value
        if self._timeline and self._loaded_tiers and duration_ms > 0:
            dur_s = duration_ms / 1000.0
            # Only override if timeline duration seems shorter than the audio
            existing = self._timeline._duration
            if existing < dur_s * 0.95:
                self._timeline.set_data(self._loaded_tiers, dur_s)

    def _open_audio_externally(self):
        path = self._current_audio_path
        if not path:
            return
        if sys.platform == "darwin":
            subprocess.Popen(["open", str(path)])
        elif sys.platform == "win32":
            subprocess.Popen(["start", "", str(path)], shell=True)
        else:
            subprocess.Popen(["xdg-open", str(path)])

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _fmt_ms(ms: int) -> str:
        s = ms // 1000
        return f"{s // 60}:{s % 60:02d}"

    @staticmethod
    def _make_section_label(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(Labels.SECTION_LABEL)
        return lbl


__all__ = ["TextGridTimeline", "ViewerStacker"]
