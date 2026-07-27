"""Viewer Stacker Module.

Pipeline page for browsing alignment results — synchronized view of a
waveform, spectrogram, TextGrid tiers, transcript, and audio playback for any
speaker/file in a registered alignment.

API
---
- **TimeAxisMixin**: Shared time<->pixel mapping so multiple panels
  (waveform, spectrogram, TextGrid tiers) stay pixel-aligned to the same
  playhead.
- **TextGridTimeline**: Custom painted widget rendering TextGrid tiers as a
  time-aligned view with a live playhead and click-to-seek.
- **WaveformPanel**: Custom painted waveform view, time-synced with
  TextGridTimeline via TimeAxisMixin.
- **SpectrogramPanel**: Praat-style grayscale spectrogram view, time-synced
  via TimeAxisMixin; opt-in since it's slower to compute than the waveform.
- **ViewerStacker**: Alignment viewer workflow UI
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

from PyQt6.QtCore import QEvent, QPoint, QRectF, Qt, QTimer, QUrl, pyqtSignal
from PyQt6.QtGui import (
    QColor,
    QFont,
    QImage,
    QPainter,
    QPen,
    QPixmap,
    QPolygon,
)
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QScrollBar,
    QSizePolicy,
    QSlider,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from voxkit.gui.components import MultiColumnComboBox
from voxkit.gui.pages.pipeline.base_stacker import BaseStacker
from voxkit.gui.styles import Buttons, Colors, Containers, Labels
from voxkit.gui.workers.worker_thread import WorkerThread
from voxkit.storage import alignments, datasets
from voxkit.storage.constants import SUPERSET_AUDIO_EXTENSIONS

if TYPE_CHECKING:
    import numpy as np
    from PyQt6.QtMultimedia import QAudioOutput, QMediaPlayer

try:
    from PyQt6.QtMultimedia import QAudioOutput, QMediaPlayer  # noqa: F811

    MULTIMEDIA_AVAILABLE = True
except ImportError:
    MULTIMEDIA_AVAILABLE = False


_AUDIO_EXTENSIONS = SUPERSET_AUDIO_EXTENSIONS
_SILENCE_LABELS = {"", "sp", "sil", "<eps>", "spn"}

# ---------------------------------------------------------------------------
# TextGrid parser
# ---------------------------------------------------------------------------


def parse_textgrid(filepath: str) -> list[dict]:
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
                    tier["intervals"].append({"time": float(time.group(1)), "label": mark.group(1)})

        tiers.append(tier)

    return tiers


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------


def find_textgrid(tg_root: Path, speaker: str, stem: str) -> Path | None:
    """Probe common TextGrid layouts and return the first match."""
    candidates = [
        tg_root / speaker / f"{stem}.TextGrid",
        tg_root / f"{stem}.TextGrid",
        tg_root / "cache" / speaker / f"{stem}.TextGrid",
        tg_root / "cache" / f"{stem}.TextGrid",
    ]
    return next((c for c in candidates if c.exists()), None)


def find_lab(data_root: Path, speaker: str, stem: str) -> Path | None:
    """Return the transcript file (.lab or .txt) for the given audio stem."""
    for ext in (".lab", ".txt"):
        p = data_root / speaker / f"{stem}{ext}"
        if p.exists():
            return p
    return None


# ---------------------------------------------------------------------------
# TimeAxisMixin
# ---------------------------------------------------------------------------

if TYPE_CHECKING:
    # Concrete subclasses always also derive from QWidget (see class docstring)
    # -- this makes mypy aware of update()/width() etc. on `self` without
    # actually making the mixin a QWidget at runtime.
    _TimeAxisBase = QWidget
else:
    _TimeAxisBase = object


class TimeAxisMixin(_TimeAxisBase):
    """Shared time <-> pixel mapping for timeline-synced panels.

    Multiple panels (TextGrid tiers, waveform, spectrogram) must map a given
    time value to the *identical* x-coordinate, or their playheads and
    content visibly drift apart from one another, especially on window
    resize or when zoomed. Centralizing the transform here — rather than
    duplicating the arithmetic per widget — is what guarantees that.

    Also centralizes zoom/pan/selection mouse interaction: subclasses get
    wheel-to-zoom, drag-to-select, and shift/middle-drag-to-pan for free by
    inheriting this mixin, emitting signals a coordinating widget (e.g.
    ViewerStacker) listens to and broadcasts back to every synced panel via
    ``set_view``/``set_selection`` — never mutate this state independently
    per-panel, or panels will disagree on what's visible/selected.

    Classes mixing this in must also derive from QWidget (for ``self.width()``)
    and define ``seek_requested``, ``zoom_requested``, ``pan_requested``, and
    ``selection_changed`` pyqtSignals themselves (signals must be declared on
    a class that inherits QObject, which this mixin alone does not).
    """

    LEFT_MARGIN = 92  # space reserved for row/tier name labels
    RIGHT_MARGIN = 8

    if TYPE_CHECKING:
        # Declared here only for mypy -- concrete subclasses (see docstring
        # above) actually define these as real pyqtSignals, since a Qt signal
        # must live on a QObject-deriving class, which this mixin alone is not.
        seek_requested: pyqtSignal
        pan_requested: pyqtSignal
        selection_changed: pyqtSignal

    _duration: float = 0.0
    _view_start: float = 0.0
    _view_end: float = 0.0
    _sel_start: float | None = None
    _sel_end: float | None = None

    _dragging = False
    _drag_start_x: float | None = None
    _drag_is_pan = False

    # ── shared state setters ────────────────────────────────────────────────

    def set_duration(self, duration: float) -> None:
        """Set the total file duration and reset the visible window/selection
        to the full file — called once per file load, and again whenever
        ViewerStacker corrects an initial TextGrid-derived duration guess to
        the audio player's precise value.

        Routes through ``_on_view_changed()`` (not a plain ``self.update()``)
        so SpectrogramPanel's override also fires here -- otherwise a
        duration correction resets the view but leaves its cached pixmap
        mapped to the stale pre-correction view, and the live zoom/pan
        tracking (`_live_source_rect`) then crops it against the wrong
        window.
        """
        self._duration = duration
        self._reset_view()
        self._on_view_changed()

    def _reset_view(self) -> None:
        self._view_start = 0.0
        self._view_end = self._duration
        self._sel_start = None
        self._sel_end = None

    def set_view(self, start: float, end: float) -> None:
        self._view_start = start
        self._view_end = end
        self._on_view_changed()

    def _on_view_changed(self) -> None:
        """Hook for subclasses that need to react to a changed visible window
        (e.g. SpectrogramPanel restarting its render-debounce timer)."""
        self.update()

    def set_selection(self, start: float | None, end: float | None) -> None:
        self._sel_start = start
        self._sel_end = end
        self.update()

    # ── coordinate conversion (visible-window aware) ────────────────────────

    def _view_span(self) -> float:
        return max(1e-9, self._view_end - self._view_start)

    def _time_to_x(self, t: float) -> int:
        if self._duration <= 0:
            return self.LEFT_MARGIN
        pixel_span = self.width() - self.LEFT_MARGIN - self.RIGHT_MARGIN
        return self.LEFT_MARGIN + int((t - self._view_start) / self._view_span() * pixel_span)

    def _x_to_time(self, x: float) -> float:
        pixel_span = self.width() - self.LEFT_MARGIN - self.RIGHT_MARGIN
        if pixel_span <= 0:
            return self._view_start
        t = self._view_start + (x - self.LEFT_MARGIN) / pixel_span * self._view_span()
        return max(0.0, min(self._duration, t))

    # ── painting helpers ─────────────────────────────────────────────────────

    def _draw_playhead(self, painter: QPainter, current_time: float, height: int) -> None:
        """Draw the shared red playhead marker at ``current_time``."""
        if self._duration <= 0:
            return
        px = self._time_to_x(current_time)
        painter.setPen(QPen(QColor("#e74c3c"), 2))
        painter.drawLine(px, 0, px, height)

        ts = 5
        painter.setBrush(QColor("#e74c3c"))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawPolygon(
            QPolygon([QPoint(px - ts, 0), QPoint(px + ts, 0), QPoint(px, ts * 2)])
        )

    def _draw_selection(self, painter: QPainter, height: int) -> None:
        """Draw the shared translucent time-range selection, if any."""
        if self._sel_start is None or self._sel_end is None or self._duration <= 0:
            return
        x1 = self._time_to_x(min(self._sel_start, self._sel_end))
        x2 = self._time_to_x(max(self._sel_start, self._sel_end))
        painter.fillRect(x1, 0, max(1, x2 - x1), height, QColor(52, 152, 219, 60))

    _preview_time: float | None = None

    def set_preview_time(self, t: float | None) -> None:
        """Set (or clear) a dashed reference line at time ``t``.

        Used while dragging a TextGrid boundary (see
        EditableTextGridTimeline.boundary_dragging) so the waveform/
        spectrogram show exactly where the boundary currently sits, for
        precisely lining it up against a formant transition, burst, etc.
        Deliberately a separate concept from the (solid, red) playhead --
        a moving playhead line would read as a change in playback position.
        """
        self._preview_time = t
        self.update()

    def _draw_preview_line(self, painter: QPainter, height: int) -> None:
        if self._preview_time is None or self._duration <= 0:
            return
        px = self._time_to_x(self._preview_time)
        painter.setPen(QPen(QColor("#8e44ad"), 1.5, Qt.PenStyle.DashLine))
        painter.drawLine(px, 0, px, height)

    # ── mouse / wheel interaction ────────────────────────────────────────────

    # Zooming is deliberately button-only (see the +/- "Zoom In"/"Zoom Out"
    # buttons each stacker wires to _zoom_by) -- wheel/touchpad-to-zoom was
    # too easy to trigger by accident while just trying to scroll the page,
    # so wheelEvent is intentionally NOT overridden here: leaving it
    # unhandled lets the event propagate to the enclosing QScrollArea for
    # normal page scrolling instead.

    def mousePressEvent(self, event) -> None:
        if self._duration <= 0:
            return
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            self._drag_start_x = event.position().x()
            self._drag_is_pan = bool(event.modifiers() & Qt.KeyboardModifier.ShiftModifier)
        elif event.button() == Qt.MouseButton.MiddleButton:
            self._dragging = True
            self._drag_start_x = event.position().x()
            self._drag_is_pan = True

    def mouseMoveEvent(self, event) -> None:
        if not self._dragging or self._drag_start_x is None:
            return
        current_x = event.position().x()
        if self._drag_is_pan:
            dt = self._x_to_time(self._drag_start_x) - self._x_to_time(current_x)
            if abs(dt) > 1e-6:
                self.pan_requested.emit(dt)
                self._drag_start_x = current_x
        else:
            t1 = self._x_to_time(self._drag_start_x)
            t2 = self._x_to_time(current_x)
            self.selection_changed.emit(min(t1, t2), max(t1, t2))

    def mouseReleaseEvent(self, event) -> None:
        if not self._dragging:
            return
        if not self._drag_is_pan and self._drag_start_x is not None:
            moved = abs(event.position().x() - self._drag_start_x) > 3
            if not moved:
                self.seek_requested.emit(self._x_to_time(event.position().x()))
        self._dragging = False
        self._drag_start_x = None


# ---------------------------------------------------------------------------
# TextGridTimeline
# ---------------------------------------------------------------------------


class TextGridTimeline(TimeAxisMixin, QWidget):
    """Custom painted widget showing TextGrid tiers as a synchronized timeline.

    - One row per tier, each with time-scaled labeled interval blocks.
    - A vertical red playhead tracks the current audio position.
    - Clicking anywhere emits ``seek_requested`` with the target time in seconds.
    """

    seek_requested = pyqtSignal(float)  # seconds
    zoom_requested = pyqtSignal(float, float, float)  # anchor_time, anchor_fraction, factor
    pan_requested = pyqtSignal(float)  # delta seconds
    selection_changed = pyqtSignal(float, float)  # start, end seconds

    TIER_HEIGHT = 36
    RULER_HEIGHT = 26

    # Fixed colors for well-known tier names (case-insensitive match)
    _TIER_COLOR_MAP: dict[str, QColor] = {
        "words": QColor("#3498db"),  # blue
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

    def __init__(self, parent: QWidget | None = None) -> None:
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
        self._current_time = 0.0
        self.setFixedHeight(self.RULER_HEIGHT + max(1, len(tiers)) * self.TIER_HEIGHT)
        self.set_duration(duration)

    def set_current_time(self, seconds: float) -> None:
        if abs(seconds - self._current_time) > 0.008:
            self._current_time = seconds
            self.update()

    def clear(self) -> None:
        self._tiers = []
        self._duration = 0.0
        self._current_time = 0.0
        self._reset_view()
        self.setFixedHeight(self.RULER_HEIGHT)
        self.update()

    def _interval_at(self, x: float, y: float) -> tuple[float, float] | None:
        """Return the (start, end) of the interval tier segment under (x, y), if any."""
        row_idx = int((y - self.RULER_HEIGHT) // self.TIER_HEIGHT)
        if row_idx < 0 or row_idx >= len(self._tiers):
            return None
        tier = self._tiers[row_idx]
        if tier["class"] != "IntervalTier":
            return None
        t = self._x_to_time(x)
        for iv in tier.get("intervals", []):
            if iv["start"] <= t < iv["end"]:
                return iv["start"], iv["end"]
        return None

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

            # Ticks are spaced across the *visible* window, not the full file
            # duration, so they stay legible at any zoom level.
            view_span = self._view_span()
            available = w - self.LEFT_MARGIN - self.RIGHT_MARGIN
            approx_ticks = max(2, available // 72)
            raw_step = view_span / approx_ticks
            for nice in (0.001, 0.002, 0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1, 2, 5, 10, 30, 60):
                if raw_step <= nice:
                    step = nice
                    break
            else:
                step = raw_step

            t = self._view_start - (self._view_start % step)
            tick_count = 0
            while t <= self._view_end + step * 0.01 and tick_count < 1000:
                if t >= self._view_start - step * 0.01:
                    x = self._time_to_x(t)
                    painter.drawLine(x, self.RULER_HEIGHT - 5, x, self.RULER_HEIGHT)
                    lbl = (
                        f"{t:.2f}s"
                        if t < 1
                        else (f"{t:.1f}s" if t < 60 else f"{int(t // 60)}:{int(t % 60):02d}")
                    )
                    painter.drawText(
                        x - 26,
                        1,
                        52,
                        self.RULER_HEIGHT - 6,
                        Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter,
                        lbl,
                    )
                t += step
                tick_count += 1

        # Left margin background
        painter.fillRect(
            0,
            self.RULER_HEIGHT,
            self.LEFT_MARGIN,
            h - self.RULER_HEIGHT,
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

        # Resolve each tier's color once, reused by both the clipped
        # (interval content) and unclipped (tier name label) passes below.
        tier_colors = []
        fallback_idx = 0
        for tier in self._tiers:
            tier_key = tier["name"].lower()
            if tier_key in self._TIER_COLOR_MAP:
                tier_colors.append(self._TIER_COLOR_MAP[tier_key])
            else:
                tier_colors.append(self._TIER_COLORS[fallback_idx % len(self._TIER_COLORS)])
                fallback_idx += 1

        # Interval content is clipped to the data area so a scrolled/zoomed
        # interval that starts before the visible window never draws under
        # the (always-visible) tier-name label column to its left.
        painter.save()
        painter.setClipRect(self.LEFT_MARGIN, self.RULER_HEIGHT, w - self.LEFT_MARGIN, h)
        for idx, tier in enumerate(self._tiers):
            y = self.RULER_HEIGHT + idx * self.TIER_HEIGHT
            color = tier_colors[idx]
            is_interval = tier["class"] == "IntervalTier"

            # Alternating row background
            row_bg = QColor("#ffffff") if idx % 2 == 0 else QColor("#f5f6fa")
            painter.fillRect(self.LEFT_MARGIN, y, w - self.LEFT_MARGIN, self.TIER_HEIGHT, row_bg)

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
                    text_color = QColor("white") if active else color.darker(140)
                    painter.setPen(text_color)
                    painter.drawText(
                        x1 + 2,
                        y + pad,
                        bw - 4,
                        self.TIER_HEIGHT - pad * 2,
                        Qt.AlignmentFlag.AlignCenter,
                        iv_label,
                    )

            # Row bottom border
            painter.setPen(QPen(QColor("#dde1e7"), 1))
            painter.drawLine(self.LEFT_MARGIN, y + self.TIER_HEIGHT, w, y + self.TIER_HEIGHT)
        painter.restore()

        # Tier name labels are drawn last, unclipped, so they always stay on
        # top of any interval content scrolled/zoomed underneath them.
        for idx, tier in enumerate(self._tiers):
            y = self.RULER_HEIGHT + idx * self.TIER_HEIGHT
            painter.setFont(name_font)
            painter.setPen(tier_colors[idx].darker(150))
            painter.drawText(
                4,
                y,
                self.LEFT_MARGIN - 6,
                self.TIER_HEIGHT,
                Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                tier["name"],
            )

        # ── Selection + Playhead ─────────────────────────────────────────────
        self._draw_selection(painter, h)
        self._draw_playhead(painter, self._current_time, h)
        self._draw_preview_line(painter, h)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update()

    def mouseReleaseEvent(self, event) -> None:
        # A plain click (no drag) on a tier interval selects that whole
        # interval (blue highlight) instead of the mixin's default seek-only
        # behavior — this also makes "Play Selection" always play whatever
        # was last clicked, rather than a stale prior selection.
        if self._dragging and not self._drag_is_pan and self._drag_start_x is not None:
            moved = abs(event.position().x() - self._drag_start_x) > 3
            if not moved:
                interval = self._interval_at(event.position().x(), event.position().y())
                if interval is not None:
                    self._dragging = False
                    self._drag_start_x = None
                    self.selection_changed.emit(interval[0], interval[1])
                    return
        super().mouseReleaseEvent(event)


# ---------------------------------------------------------------------------
# WaveformPanel
# ---------------------------------------------------------------------------


class WaveformPanel(TimeAxisMixin, QWidget):
    """Custom painted waveform view, time-synced with TextGridTimeline.

    Loading a file's samples and computing its min/max envelope happens once
    per file, on a background thread (large files can take a couple seconds
    with librosa) — ``paintEvent`` only blits the cached envelope and moves
    the playhead, it never recomputes on paint.
    """

    seek_requested = pyqtSignal(float)  # seconds
    zoom_requested = pyqtSignal(float, float, float)  # anchor_time, anchor_fraction, factor
    pan_requested = pyqtSignal(float)  # delta seconds
    selection_changed = pyqtSignal(float, float)  # start, end seconds

    _PEAK_BUCKETS = 2000  # envelope resolution; independent of pixel width

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._duration: float = 0.0
        self._current_time: float = 0.0
        self._peaks: list[tuple[float, float]] | None = None
        self._peak_abs: float = 1.0
        self._samples: np.ndarray | None = None  # raw mono samples, once loaded
        self._sr: int | None = None
        self._loading = False
        self._load_token = 0
        self._worker: WorkerThread | None = None
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setFixedHeight(90)

    def set_current_time(self, seconds: float) -> None:
        if abs(seconds - self._current_time) > 0.008:
            self._current_time = seconds
            self.update()

    def clear(self) -> None:
        self._peaks = None
        self._peak_abs = 1.0
        self._samples = None
        self._sr = None
        self._loading = False
        self._duration = 0.0
        self._current_time = 0.0
        self._reset_view()
        self._load_token += 1  # invalidate any in-flight worker result
        self.update()

    def load_audio(self, audio_path: Path) -> None:
        """Kick off background envelope computation for a new audio file."""
        self._peaks = None
        self._loading = True
        self._load_token += 1
        token = self._load_token
        self.update()

        def _compute() -> str:
            import librosa

            samples, sr = librosa.load(str(audio_path), sr=None, mono=True)
            bucket_size = max(1, len(samples) // self._PEAK_BUCKETS)
            peaks = [
                (float(chunk.min()), float(chunk.max()))
                for i in range(0, len(samples), bucket_size)
                if len(chunk := samples[i : i + bucket_size])
            ]
            self._pending_peaks = peaks
            # Normalize display to this file's own peak amplitude (Audacity/
            # Praat-style) — many recordings peak well under +/-1.0, and
            # without this a quiet file renders as a flat line.
            self._pending_peak_abs = max(
                (max(abs(mn), abs(mx)) for mn, mx in peaks), default=1.0
            ) or 1.0
            self._pending_samples = samples
            self._pending_sr = int(sr)  # librosa types sr as float; sample rates are always whole
            self._pending_token = token
            return "Waveform loaded"

        self._worker = WorkerThread(_compute)
        self._worker.finished.connect(self._on_peaks_ready)
        self._worker.start()

    def _on_peaks_ready(self, success: bool, _message: str) -> None:
        # A later load_audio() call may have started (and finished) while
        # this worker was running; discard results from a stale file.
        if getattr(self, "_pending_token", None) != self._load_token:
            return
        self._loading = False
        if success and hasattr(self, "_pending_peaks"):
            self._peaks = self._pending_peaks
            self._peak_abs = self._pending_peak_abs
            self._samples = self._pending_samples
            self._sr = self._pending_sr
        self.update()

    def get_samples(self):
        """Return (samples, sample_rate) for the loaded file, or None if not ready."""
        if self._samples is None or self._sr is None:
            return None
        return self._samples, self._sr

    def paintEvent(self, _event):
        painter = QPainter(self)
        w, h = self.width(), self.height()
        painter.fillRect(0, 0, w, h, QColor("#f8f9fa"))

        # Left margin (matches TextGridTimeline's tier-name column for alignment)
        painter.fillRect(0, 0, self.LEFT_MARGIN, h, QColor("#ecf0f1"))
        painter.setPen(QPen(QColor("#bdc3c7"), 1))
        painter.drawLine(self.LEFT_MARGIN, 0, self.LEFT_MARGIN, h)

        mid_y = h // 2
        if self._loading:
            painter.setPen(QColor("#7f8c8d"))
            painter.drawText(
                self.LEFT_MARGIN,
                0,
                w - self.LEFT_MARGIN,
                h,
                Qt.AlignmentFlag.AlignCenter,
                "Loading waveform...",
            )
        elif self._peaks:
            # Clipped so a bucket panned/zoomed before the visible window
            # never draws under the (always-visible) left-margin column.
            painter.save()
            painter.setClipRect(self.LEFT_MARGIN, 0, w - self.LEFT_MARGIN, h)
            painter.setPen(QPen(QColor("#3498db"), 1))
            n = len(self._peaks)
            amp_scale = (h / 2 - 4) / self._peak_abs
            for i, (mn, mx) in enumerate(self._peaks):
                t = (i / n) * self._duration if self._duration > 0 else 0.0
                x = self._time_to_x(t)
                y1 = mid_y - int(mx * amp_scale)
                y2 = mid_y - int(mn * amp_scale)
                painter.drawLine(x, y1, x, y2)
            painter.restore()

        self._draw_selection(painter, h)
        self._draw_playhead(painter, self._current_time, h)
        self._draw_preview_line(painter, h)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update()


# ---------------------------------------------------------------------------
# SpectrogramPanel
# ---------------------------------------------------------------------------


class SpectrogramPanel(TimeAxisMixin, QWidget):
    """Praat-style grayscale spectrogram, time-synced with TextGridTimeline.

    Opt-in (via a "Show Spectrogram" toggle) since computing the STFT is
    slower than the waveform envelope, especially for large files. The STFT
    itself is computed once per file on a background thread; only the final
    "render cached data to an image" step runs on the GUI thread, and that
    step is debounced on resize so live window-dragging doesn't trigger a
    re-render on every intermediate frame.

    Matches Praat's default spectrogram analysis settings (Standard and
    Advanced spectrogram settings dialogs), verified against Praat's own
    source (github.com/praat/praat, fon/Sound_and_Spectrogram.cpp and
    fon/Spectrogram.cpp): a 5 ms Gaussian analysis window, using Praat's
    exact formula (a Gaussian truncated to exactly zero at the window
    edges, not a plain untruncated Gaussian), a 0-10000 Hz linear frequency
    range, a 50 dB dynamic range, +6 dB/octave pre-emphasis referenced to
    1000 Hz (0 dB boost *at* 1000 Hz, per ``Spectrogram.cpp``'s
    ``dbPerOctave * log2(freq / 1000 Hz)`` — compensating for the natural
    -6 dB/octave tilt of voiced speech), and an "automatic" time/frequency
    step strategy: never use a step finer than what the window's own
    time-frequency resolution can usefully distinguish (``1/(8*sqrt(pi))``
    of the window length for time, ``sqrt(pi)/8`` of its inverse for
    frequency), but cap the total frame/bin count at 1000 time steps / 250
    frequency steps when the natural step would exceed that budget (see the
    Praat manual's "Sound: To Spectrogram..." page).

    Brightness is autoscaled to the *visible* window's own maximum energy —
    matching Praat's actual default behavior, which the manual notes
    supersedes its nominal fixed "Maximum (dB/Hz)" setting ("autoscaling
    uses the visible spectrogram's maximum instead"). Dynamic compression
    (Praat's setting for boosting weak frames) is left at Praat's own
    default of 0 (off) — nothing to implement there.
    """

    seek_requested = pyqtSignal(float)  # seconds
    zoom_requested = pyqtSignal(float, float, float)  # anchor_time, anchor_fraction, factor
    pan_requested = pyqtSignal(float)  # delta seconds
    selection_changed = pyqtSignal(float, float)  # start, end seconds

    FREQ_MAX_HZ = 10000
    DYNAMIC_RANGE_DB = 50
    WINDOW_SECONDS = 0.005
    TIME_STEPS = 1000
    FREQUENCY_STEPS = 250
    PRE_EMPHASIS_DB_PER_OCTAVE = 6.0

    _RESIZE_DEBOUNCE_MS = 200

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._duration: float = 0.0
        self._current_time: float = 0.0
        self._loaded_path: Path | None = None
        self._freqs: np.ndarray | None = None
        self._times: np.ndarray | None = None
        self._Sxx_db: np.ndarray | None = None
        self._pixmap: QPixmap | None = None
        # The view window + axes placement self._pixmap was actually
        # rendered for -- used to stretch/crop it live during zoom/pan, so
        # the spectrogram visibly tracks the other panels instead of
        # sitting frozen until the debounced re-render catches up.
        self._pixmap_view_start = 0.0
        self._pixmap_view_end = 0.0
        self._pixmap_left_frac = 0.0
        self._pixmap_right_frac = 1.0
        self._loading = False
        self._load_token = 0
        self._worker: WorkerThread | None = None
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setFixedHeight(160)

        self._resize_timer = QTimer(self)
        self._resize_timer.setSingleShot(True)
        self._resize_timer.timeout.connect(self._regenerate_pixmap)

    def _on_view_changed(self) -> None:
        # Re-render (not recompute) the spectrogram at the new zoom/pan
        # window, debounced so a zoom/pan drag doesn't re-run matplotlib on
        # every intermediate event.
        self._resize_timer.start(self._RESIZE_DEBOUNCE_MS)
        self.update()

    def set_current_time(self, seconds: float) -> None:
        if abs(seconds - self._current_time) > 0.008:
            self._current_time = seconds
            self.update()

    def clear(self) -> None:
        self._loaded_path = None
        self._freqs = None
        self._times = None
        self._Sxx_db = None
        self._pixmap = None
        self._pixmap_view_start = 0.0
        self._pixmap_view_end = 0.0
        self._loading = False
        self._duration = 0.0
        self._current_time = 0.0
        self._reset_view()
        self._load_token += 1  # invalidate any in-flight worker result
        self.update()

    def load_audio(self, audio_path: Path) -> None:
        """Kick off background STFT computation for a new file.

        No-op if this exact file is already loaded (cheap to call from a
        toggle handler without worrying about redundant recomputation).
        """
        if self._loaded_path == audio_path and self._Sxx_db is not None:
            return

        self._loaded_path = audio_path
        self._Sxx_db = None
        self._pixmap = None
        self._loading = True
        self._load_token += 1
        token = self._load_token
        self.update()

        def _compute() -> str:
            import librosa
            import numpy as np

            samples, sr = librosa.load(str(audio_path), sr=None, mono=True)
            duration = len(samples) / sr
            win_length = max(32, int(sr * self.WINDOW_SECONDS))

            # Praat's "automatic" time/frequency step strategy: a step never
            # needs to be finer than what the window's own time-frequency
            # resolution can usefully distinguish, but the total frame/bin
            # count is capped at TIME_STEPS/FREQUENCY_STEPS when that natural
            # step would exceed the budget. See the Praat manual's "Sound:
            # To Spectrogram..." page for the exact formulas below.
            dt_natural = self.WINDOW_SECONDS / (8 * np.sqrt(np.pi))
            dt = max(dt_natural, duration / self.TIME_STEPS)
            hop_length = max(1, int(round(dt * sr)))

            df_natural = np.sqrt(np.pi) / (8 * self.WINDOW_SECONDS)
            df = max(df_natural, self.FREQ_MAX_HZ / self.FREQUENCY_STEPS)
            # Not rounded to a power of 2: this is a one-time per-file
            # transform (not real-time), so the FFT-efficiency gain isn't
            # worth trading away exact parity with the Praat-specified
            # frequency step / bin count.
            n_fft = max(win_length, int(round(sr / df)))

            # Gaussian analysis window, matching Praat's exact formula (see
            # Sound_and_Spectrogram.cpp): a Gaussian truncated to exactly
            # zero at the window edges (i.e. subtracting and renormalizing
            # by exp(-12)), rather than a plain untruncated Gaussian.
            i = np.arange(1, win_length + 1, dtype=np.float64)
            imid = 0.5 * (win_length + 1)
            edge = np.exp(-12.0)
            phase = (i - imid) / win_length
            gaussian_window = (np.exp(-48.0 * phase**2) - edge) / (1.0 - edge)

            stft = librosa.stft(
                samples,
                n_fft=n_fft,
                hop_length=hop_length,
                win_length=win_length,
                window=gaussian_window,
            )
            # ref=1.0: an absolute (not per-file-adaptive) reference. Actual
            # display brightness is autoscaled per the *visible* window at
            # render time (_regenerate_pixmap), matching Praat's own default
            # behavior -- so the absolute reference chosen here only needs
            # to be a fixed, consistent baseline, not a calibrated physical
            # unit (see class docstring). Praat itself references power to
            # an absolute 4e-10 Pa^2/Hz, but that choice is invisible in the
            # final render since autoscaling subtracts it right back out.
            magnitude_db = librosa.amplitude_to_db(np.abs(stft), ref=1.0)

            freqs = librosa.fft_frequencies(sr=sr, n_fft=n_fft)
            keep = freqs <= self.FREQ_MAX_HZ
            freqs = freqs[keep]
            magnitude_db = magnitude_db[keep, :]

            # Pre-emphasis: +6 dB/octave applied directly to the spectrum in
            # dB, referenced to 1000 Hz (0 dB boost *at* 1000 Hz) -- per
            # Praat's Spectrogram.cpp: dbPerOctave * log2(freq / 1000 Hz).
            # Compensates for the natural -6 dB/octave spectral tilt of
            # voiced speech so higher formants are equally visible.
            preemphasis_db = self.PRE_EMPHASIS_DB_PER_OCTAVE * np.log2(
                np.maximum(freqs, 0.0) / 1000.0 + 1e-300
            )
            magnitude_db = magnitude_db + preemphasis_db[:, None]

            times = librosa.frames_to_time(
                np.arange(magnitude_db.shape[1]), sr=sr, hop_length=hop_length
            )

            self._pending_freqs = freqs
            self._pending_times = times
            self._pending_Sxx_db = magnitude_db
            self._pending_token = token
            return "Spectrogram computed"

        self._worker = WorkerThread(_compute)
        self._worker.finished.connect(self._on_spectrogram_ready)
        self._worker.start()

    def _on_spectrogram_ready(self, success: bool, _message: str) -> None:
        # A later load_audio() call may have started (and finished) while
        # this worker was running; discard results from a stale file.
        if getattr(self, "_pending_token", None) != self._load_token:
            return
        self._loading = False
        if success and hasattr(self, "_pending_Sxx_db"):
            self._freqs = self._pending_freqs
            self._times = self._pending_times
            self._Sxx_db = self._pending_Sxx_db
            self._regenerate_pixmap()
        self.update()

    def _regenerate_pixmap(self) -> None:
        """Re-render the cached STFT data to a QPixmap sized to the current widget.

        Rendering (not recomputing the STFT) happens here so the plotted
        axes' left margin lines up with TimeAxisMixin.LEFT_MARGIN exactly at
        the widget's *current* size — required for the shared playhead
        (drawn using the fixed-pixel LEFT_MARGIN convention) to land on the
        correct column regardless of window width.
        """
        # _Sxx_db, _times, and _freqs are always set together by
        # _on_spectrogram_ready -- guard all three since a missing one means
        # none of them are ready yet.
        if self._Sxx_db is None or self._times is None or self._freqs is None:
            return

        import numpy as np

        w, h = max(1, self.width()), max(1, self.height())

        from matplotlib.backends.backend_agg import FigureCanvasAgg
        from matplotlib.figure import Figure

        dpi = 100
        # Render at 2x the widget's pixel density and downscale on paint
        # (with a smooth-transform hint) — sharper than rendering 1:1, since
        # it supersamples rather than upscales. Axes are placed by fraction
        # (0-1 of figure size), so this doesn't disturb the LEFT_MARGIN math
        # below regardless of the multiplier.
        supersample = 2
        fig = Figure(figsize=(w / dpi, h / dpi), dpi=dpi * supersample)
        canvas = FigureCanvasAgg(fig)

        left_frac = self.LEFT_MARGIN / w
        right_frac = 1 - (self.RIGHT_MARGIN / w)
        ax = fig.add_axes((left_frac, 0.14, right_frac - left_frac, 0.82))

        duration = self._duration if self._duration > 0 else 1.0
        view_end = self._view_end if self._view_end > self._view_start else duration

        # Autoscale brightness to the currently *visible* window's own
        # maximum energy, matching Praat's actual default behavior (the
        # manual notes this supersedes its nominal fixed "Maximum (dB/Hz)"
        # setting) -- so re-zooming changes the displayed contrast just like
        # it does in Praat, rather than staying fixed to the whole file.
        visible = (self._times >= self._view_start) & (self._times <= view_end)
        visible_cols = self._Sxx_db[:, visible] if visible.any() else self._Sxx_db
        vmax = float(np.max(visible_cols)) if visible_cols.size else 0.0

        ax.imshow(
            self._Sxx_db,
            aspect="auto",
            origin="lower",
            cmap="Greys",
            vmin=vmax - self.DYNAMIC_RANGE_DB,
            vmax=vmax,
            interpolation="nearest",
            extent=(0, duration, self._freqs[0], self._freqs[-1]),
        )
        # Crop to the current zoom/pan window without re-slicing _Sxx_db or
        # re-running the STFT -- matplotlib just displays the portion of the
        # already-plotted image within these x-limits.
        ax.set_xlim(self._view_start, view_end)
        # Always show the full 0-FREQ_MAX_HZ axis range, even if this file's
        # own sample rate can't reach it (e.g. a 16kHz file's Nyquist tops
        # out at 8000 Hz) -- otherwise the y-axis silently auto-scales to
        # whatever this file's data happens to cover, rather than staying
        # fixed like Praat's own frequency-range setting.
        ax.set_ylim(0, self.FREQ_MAX_HZ)
        ax.set_ylabel("Hz", fontsize=7)
        ax.tick_params(labelsize=6)
        fig.patch.set_facecolor("#f8f9fa")

        canvas.draw()
        buf_w, buf_h = canvas.get_width_height()
        buf = canvas.buffer_rgba()
        image = QImage(bytes(buf), buf_w, buf_h, QImage.Format.Format_RGBA8888)
        self._pixmap = QPixmap.fromImage(image.copy())

        # Record exactly what this pixmap represents, so paintEvent can
        # stretch/crop it to approximate a *newer* view live (e.g. mid-pan,
        # before the next debounced re-render lands) instead of freezing.
        self._pixmap_view_start = self._view_start
        self._pixmap_view_end = view_end
        self._pixmap_left_frac = left_frac
        self._pixmap_right_frac = right_frac

        self.update()

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        w, h = self.width(), self.height()
        painter.fillRect(0, 0, w, h, QColor("#f8f9fa"))

        if self._loading:
            painter.setPen(QColor("#7f8c8d"))
            painter.drawText(
                0, 0, w, h, Qt.AlignmentFlag.AlignCenter, "Computing spectrogram..."
            )
        elif self._pixmap:
            painter.drawPixmap(QRectF(self.rect()), self._pixmap, self._live_source_rect())

        self._draw_selection(painter, h)
        self._draw_playhead(painter, self._current_time, h)
        self._draw_preview_line(painter, h)

    def _live_source_rect(self) -> QRectF:
        """Map the *current* (possibly newer than the cached pixmap's) view
        window onto a source rect within that pixmap.

        Why: `_regenerate_pixmap()` is debounced, so a zoom/pan drag can
        leave `self._view_start/_end` ahead of what `self._pixmap` was
        actually rendered for. Rather than freeze the display until the
        debounce fires, stretch/crop the stale pixmap to approximate the
        live window — self-corrects to a sharp render on the next debounce.

        `paintEvent` draws this source rect into the *full* widget rect
        (matching how WaveformPanel/TextGridTimeline fill their own full
        width) — so the source must cover the pixmap's margins too, not
        just its plotted data area, or data gets stretched over where the
        margins should be. Extended outward from the data-area span at the
        same px-per-second scale as that span, so at steady state (current
        view == the pixmap's own rendered view) this exactly reproduces the
        original full-pixmap blit.
        """
        assert self._pixmap is not None  # only called from paintEvent's `elif self._pixmap:` branch
        pw, ph = self._pixmap.width(), self._pixmap.height()
        pixmap_span = max(1e-9, self._pixmap_view_end - self._pixmap_view_start)
        axes_frac = max(1e-9, self._pixmap_right_frac - self._pixmap_left_frac)

        def _time_to_pixmap_x(t: float) -> float:
            frac_in_axes = (t - self._pixmap_view_start) / pixmap_span
            return (self._pixmap_left_frac + frac_in_axes * axes_frac) * pw

        x1 = _time_to_pixmap_x(self._view_start)
        x2 = _time_to_pixmap_x(self._view_end)

        data_px = max(1, self.width() - self.LEFT_MARGIN - self.RIGHT_MARGIN)
        scale = (x2 - x1) / data_px
        x1 -= self.LEFT_MARGIN * scale
        x2 += self.RIGHT_MARGIN * scale

        return QRectF(x1, 0, max(1.0, x2 - x1), ph)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._resize_timer.start(self._RESIZE_DEBOUNCE_MS)
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

    def __init__(self, parent: QWidget | None = None) -> None:
        # Pre-declare all attributes so build_ui() (called by super().__init__)
        # can reference them safely.
        # Widgets set in build_ui() (called by super().__init__)
        self._dataset_dropdown: MultiColumnComboBox
        self._alignment_dropdown: MultiColumnComboBox
        self._speaker_dropdown: QComboBox
        self._file_list: QListWidget
        self._file_search: QLineEdit
        self._all_audio_files: list[str] = []
        self._selection_section: QWidget
        self._viewer_section: QWidget
        self._timeline: TextGridTimeline
        self._waveform: WaveformPanel
        self._spectrogram: SpectrogramPanel
        self._spectrogram_toggle: QCheckBox
        self._show_spectrogram: bool = False
        self._active_label: QLabel
        self._transcript_edit: QTextEdit
        self._audio_path_label: QLabel
        self._current_dataset_meta: datasets.DatasetMetadata | None = None
        self._current_alignment_meta: alignments.AlignmentMetadata | None = None
        self._current_data_path: Path | None = None
        self._current_audio_path: Path | None = None
        self._loaded_tiers: list[dict] = []
        # Multimedia (may remain None if QtMultimedia is unavailable)
        self._player: QMediaPlayer | None = None
        self._audio_output: QAudioOutput | None = None
        self._play_btn: QPushButton | None = None
        self._seek_slider: QSlider | None = None
        self._time_label: QLabel | None = None
        # Zoom/scroll/selection state, shared across all synced panels
        self._synced_panels: list = []
        self._time_scrollbar: QScrollBar
        self._play_selection_btn: QPushButton | None = None
        self._sel_start: float | None = None
        self._sel_end: float | None = None
        self._playing_selection: bool = False
        # Dedicated player for "Play Selection": plays a clip containing only
        # the selected samples to its own natural end-of-media, rather than
        # pausing a longer, already-playing stream at the right instant --
        # QMediaPlayer.position() lags the real audio clock and pause() has
        # its own buffer-drain latency, so no poll rate can stop it exactly
        # on a short phone boundary.
        self._selection_player: QMediaPlayer | None = None
        self._selection_audio_output: QAudioOutput | None = None
        # Pending-deletion queue, oldest first -- see
        # _cleanup_stale_selection_temp_files for why this isn't just one path.
        self._selection_temp_paths: list[Path] = []
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
            [{"id": None, "data": ("Select a dataset first", "", "", "", "")}],
            ["Engine", "Model", "Type", "Date", "Status"],
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

            self._play_selection_btn = QPushButton("▶ Play Selection")
            self._play_selection_btn.setFixedWidth(120)
            self._play_selection_btn.setStyleSheet(Buttons.SECONDARY)
            self._play_selection_btn.setEnabled(False)
            self._play_selection_btn.clicked.connect(self._play_selection)
            audio_row.addWidget(self._play_selection_btn)

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

        # Waveform ────────────────────────────────────────────────────────────
        wf_header = QHBoxLayout()
        wf_header.setContentsMargins(0, 4, 0, 0)
        wf_lbl = QLabel("Waveform")
        wf_lbl.setStyleSheet(Labels.SECTION_LABEL)
        wf_header.addWidget(wf_lbl)
        wf_header.addStretch()
        view_col.addLayout(wf_header)

        self._waveform = WaveformPanel()
        self._waveform.setStyleSheet(f"border: 1px solid {Colors.BORDER}; border-radius: 4px;")
        view_col.addWidget(self._waveform)

        # Spectrogram (opt-in) ────────────────────────────────────────────────
        spec_header = QHBoxLayout()
        spec_header.setContentsMargins(0, 4, 0, 0)
        spec_lbl = QLabel("Spectrogram")
        spec_lbl.setStyleSheet(Labels.SECTION_LABEL)
        spec_header.addWidget(spec_lbl)
        spec_header.addStretch()

        self._spectrogram_toggle = QCheckBox("Show Spectrograms (may be slower for large files)")
        self._spectrogram_toggle.setChecked(self._show_spectrogram)
        self._spectrogram_toggle.toggled.connect(self._on_spectrogram_toggled)
        spec_header.addWidget(self._spectrogram_toggle)
        view_col.addLayout(spec_header)

        self._spectrogram = SpectrogramPanel()
        self._spectrogram.setStyleSheet(f"border: 1px solid {Colors.BORDER}; border-radius: 4px;")
        self._spectrogram.setVisible(self._show_spectrogram)
        view_col.addWidget(self._spectrogram)

        # TextGrid timeline ───────────────────────────────────────────────────
        tg_header = QHBoxLayout()
        tg_header.setContentsMargins(0, 4, 0, 0)
        tg_lbl = QLabel("TextGrid Alignment")
        tg_lbl.setStyleSheet(Labels.SECTION_LABEL)
        tg_header.addWidget(tg_lbl)
        tg_header.addStretch()
        view_col.addLayout(tg_header)

        self._timeline = TextGridTimeline()
        self._timeline.setStyleSheet(f"border: 1px solid {Colors.BORDER}; border-radius: 4px;")
        view_col.addWidget(self._timeline)

        # Shared zoom/scroll row ──────────────────────────────────────────────
        zoom_row = QHBoxLayout()
        zoom_row.setSpacing(6)

        zoom_out_btn = QPushButton("Zoom Out")
        zoom_out_btn.setFixedWidth(84)
        zoom_out_btn.setStyleSheet(Buttons.SECONDARY)
        zoom_out_btn.clicked.connect(lambda: self._zoom_by(1 / 1.5))
        zoom_row.addWidget(zoom_out_btn)

        self._time_scrollbar = QScrollBar(Qt.Orientation.Horizontal)
        self._time_scrollbar.setEnabled(False)
        self._time_scrollbar.valueChanged.connect(self._on_scrollbar_changed)
        zoom_row.addWidget(self._time_scrollbar, stretch=1)

        zoom_in_btn = QPushButton("Zoom In")
        zoom_in_btn.setFixedWidth(84)
        zoom_in_btn.setStyleSheet(Buttons.SECONDARY)
        zoom_in_btn.clicked.connect(lambda: self._zoom_by(1.5))
        zoom_row.addWidget(zoom_in_btn)

        view_col.addLayout(zoom_row)

        # Wire every timeline-synced panel to the same zoom/pan/selection/seek
        # handlers, so none of them can drift out of sync with the others.
        self._synced_panels = [self._timeline, self._waveform, self._spectrogram]
        for panel in self._synced_panels:
            panel.seek_requested.connect(self._seek_to_seconds)
            panel.zoom_requested.connect(self._on_zoom_requested)
            panel.pan_requested.connect(self._on_pan_requested)
            panel.selection_changed.connect(self._set_shared_selection)

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

        # Tab plays the current selection, matching Praat's own convention.
        # A plain QShortcut loses to Qt's built-in Tab-for-focus-navigation
        # handling -- QLineEdit/QComboBox/QListWidget (all present on this
        # page) explicitly claim Tab for themselves, so the shortcut never
        # fires and Tab just jumps focus to the next widget instead. Install
        # an application-wide event filter so this page can intercept Tab
        # before the focused child widget ever sees it.
        QApplication.instance().installEventFilter(self)

        # Initialise multimedia player ────────────────────────────────────────
        if MULTIMEDIA_AVAILABLE:
            self._audio_output = QAudioOutput()
            self._player = QMediaPlayer()
            self._player.setAudioOutput(self._audio_output)
            self._player.playbackStateChanged.connect(self._on_playback_state_changed)
            self._player.positionChanged.connect(self._on_position_changed)
            self._player.durationChanged.connect(self._on_duration_changed)

            # Separate player + output for "Play Selection" clips (see the
            # attribute comment in __init__ for why this isn't just the main
            # player paused at the right moment).
            self._selection_audio_output = QAudioOutput()
            self._selection_player = QMediaPlayer()
            self._selection_player.setAudioOutput(self._selection_audio_output)
            self._selection_player.positionChanged.connect(self._on_selection_position_changed)
            self._selection_player.mediaStatusChanged.connect(
                self._on_selection_media_status_changed
            )

        self.reload_datasets()

    def eventFilter(self, obj, event) -> bool:  # noqa: N802 (Qt override)
        if (
            event.type() == QEvent.Type.KeyPress
            and event.key() == Qt.Key.Key_Tab
            and self.isVisible()
            and self._viewer_section.isVisible()
        ):
            self._play_selection()
            return True
        return super().eventFilter(obj, event)

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
                [{"id": None, "data": ("Select a dataset first", "", "", "", "")}],
                ["Engine", "Model", "Type", "Date", "Status"],
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
                [{"id": None, "data": ("Select a dataset first", "", "", "", "")}],
                ["Engine", "Model", "Type", "Date", "Status"],
                placeholder="Select a dataset first",
            )
            self._alignment_dropdown.setEnabled(False)
            return

        self._current_dataset_meta = datasets.get_dataset_metadata(dataset_id)
        if not self._current_dataset_meta:
            return

        self._current_data_path = datasets.get_dataset_data_path(self._current_dataset_meta)

        al_list = alignments.list_alignments(dataset_id)
        if al_list:
            rows = [
                {
                    "id": a["id"],
                    "data": (
                        a["engine_id"],
                        a["model_metadata"]["name"],
                        alignments.get_alignment_type(a),
                        a["alignment_date"],
                        a["status"],
                    ),
                }
                for a in al_list
            ]
            self._alignment_dropdown.set_data(
                rows,
                ["Engine", "Model", "Type", "Date", "Status"],
                placeholder="Select an alignment",
            )
            self._alignment_dropdown.setEnabled(True)
        else:
            self._alignment_dropdown.set_data(
                [{"id": None, "data": ("No alignments found", "", "", "", "")}],
                ["Engine", "Model", "Type", "Date", "Status"],
                placeholder="No alignments found",
            )
            self._alignment_dropdown.setEnabled(False)

    def _on_alignment_changed(self):
        alignment_id = self._alignment_dropdown.itemData(self._alignment_dropdown.currentIndex())

        self._selection_section.setVisible(False)
        self._viewer_section.setVisible(False)

        if not alignment_id or not self._current_dataset_meta:
            return

        meta = alignments.get_alignment_metadata(self._current_dataset_meta["id"], alignment_id)
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
        matches = (
            [f for f in self._all_audio_files if q in f.lower()] if q else self._all_audio_files
        )
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
        lab_path = find_lab(self._current_data_path, speaker, stem)
        tg_path = find_textgrid(tg_root, speaker, stem)

        self._load_viewer(audio_path, lab_path, tg_path)
        self._viewer_section.setVisible(True)

    def _on_spectrogram_toggled(self, checked: bool) -> None:
        """Handle the "Show Spectrogram" toggle.

        The toggle's state persists across file switches for the rest of the
        session (it's a plain instance attribute on this long-lived widget,
        not reset per file) — only the cached spectrogram data itself is
        cleared/recomputed per file, in ``_load_viewer``.
        """
        self._show_spectrogram = checked
        self._spectrogram.setVisible(checked)
        if checked and self._current_audio_path and self._current_audio_path.exists():
            self._spectrogram.load_audio(self._current_audio_path)

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
            self._waveform.load_audio(audio_path)
            self._spectrogram.clear()
            if self._show_spectrogram:
                self._spectrogram.load_audio(audio_path)
            if MULTIMEDIA_AVAILABLE and self._player:
                if self._player.playbackState() != QMediaPlayer.PlaybackState.StoppedState:
                    self._player.stop()
                self._player.setSource(QUrl.fromLocalFile(str(audio_path)))
                if self._play_btn:
                    self._play_btn.setText("▶  Play")
        else:
            self._audio_path_label.setText(f"Audio not found: {audio_path}")
            self._current_audio_path = None
            self._waveform.clear()
            self._spectrogram.clear()

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
                tiers = parse_textgrid(str(tg_path))
                if tiers:
                    # Derive duration from the last interval's end time
                    duration = 0.0
                    for tier in tiers:
                        if tier["class"] == "IntervalTier" and tier["intervals"]:
                            duration = max(duration, tier["intervals"][-1]["end"])
                    if duration <= 0 and MULTIMEDIA_AVAILABLE and self._player:
                        duration = self._player.duration() / 1000.0

                    self._loaded_tiers = tiers
                    self._set_shared_duration(tiers, duration)
                    self._active_label.setVisible(True)
            except Exception as exc:
                self._audio_path_label.setText(
                    f"{self._audio_path_label.text()}  [TextGrid parse error: {exc}]"
                )
        else:
            assert self._current_alignment_meta is not None
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
        self._stop_selection_playback()
        if self._player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self._player.pause()
        else:
            self._player.play()

    def _stop_playback(self):
        self._stop_selection_playback()
        if self._player:
            self._player.stop()

    def _seek_to_ms(self, ms: int):
        self._stop_selection_playback()
        if self._player:
            self._player.setPosition(ms)

    def _seek_to_seconds(self, seconds: float):
        self._stop_selection_playback()
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

        # Advance every synced panel's playhead together
        secs = position_ms / 1000.0
        for panel in self._synced_panels:
            panel.set_current_time(secs)
        self._update_active_segment_label(secs)

    def _update_active_segment_label(self, secs: float) -> None:
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
        # Correct to the audio player's precise duration whenever it
        # meaningfully differs from the TextGrid-derived one (its last
        # interval's end, used as an initial guess in _load_viewer before
        # the player has actually reported a duration). Even a small
        # (a few percent) mismatch here stretches every panel's data across
        # a slightly-wrong duration, which the waveform/TextGrid tolerate
        # imperceptibly but visibly desyncs the spectrogram's fine detail
        # from precise TextGrid boundaries -- so this used to only correct
        # when the TextGrid duration was >5% shorter, which silently missed
        # exactly this smaller-but-still-real class of mismatch.
        if self._timeline and self._loaded_tiers and duration_ms > 0:
            dur_s = duration_ms / 1000.0
            existing = self._timeline._duration
            if abs(existing - dur_s) > 0.001:
                self._set_shared_duration(self._loaded_tiers, dur_s)

    def _set_shared_duration(self, tiers: list[dict], duration: float) -> None:
        """Push the same duration to every timeline-synced panel.

        Why: keeping this in one place is what guarantees the TextGrid
        timeline, waveform, and spectrogram panels never disagree on their
        time axis (see TimeAxisMixin) — never call
        ``set_data``/``set_duration`` on them individually from elsewhere.
        """
        self._timeline.set_data(tiers, duration)
        for panel in self._synced_panels:
            if panel is not self._timeline:
                panel.set_duration(duration)

        # A new file means any prior zoom/selection no longer applies.
        self._stop_selection_playback()
        self._sel_start = None
        self._sel_end = None
        if self._play_selection_btn:
            self._play_selection_btn.setEnabled(False)
        self._update_scrollbar()

    def _on_zoom_requested(self, anchor_time: float, anchor_fraction: float, factor: float) -> None:
        """Zoom the shared view in/out, keeping ``anchor_time`` under the cursor."""
        duration = self._timeline._duration
        if duration <= 0:
            return
        old_span = self._timeline._view_end - self._timeline._view_start
        new_span = max(0.05, min(duration, old_span / factor))
        new_start = anchor_time - anchor_fraction * new_span
        new_start = max(0.0, min(duration - new_span, new_start))
        self._set_shared_view(new_start, new_start + new_span)

    def _on_pan_requested(self, dtime: float) -> None:
        """Pan the shared view by ``dtime`` seconds, clamped to the file bounds."""
        duration = self._timeline._duration
        if duration <= 0:
            return
        span = self._timeline._view_end - self._timeline._view_start
        new_start = max(0.0, min(duration - span, self._timeline._view_start + dtime))
        self._set_shared_view(new_start, new_start + span)

    def _zoom_by(self, factor: float) -> None:
        """Zoom in/out via the +/- buttons, anchored on the playhead if it's
        within the current view, else the view's midpoint."""
        view_start, view_end = self._timeline._view_start, self._timeline._view_end
        anchor_time = self._timeline._current_time
        if not (view_start <= anchor_time <= view_end):
            anchor_time = (view_start + view_end) / 2
        anchor_fraction = (anchor_time - view_start) / max(1e-9, view_end - view_start)
        self._on_zoom_requested(anchor_time, anchor_fraction, factor)

    def _set_shared_view(self, start: float, end: float) -> None:
        """Push the same visible time window to every synced panel."""
        for panel in self._synced_panels:
            panel.set_view(start, end)
        self._update_scrollbar()

    def _set_shared_selection(self, start: float, end: float) -> None:
        """Push the same time-range selection to every synced panel."""
        self._sel_start, self._sel_end = start, end
        for panel in self._synced_panels:
            panel.set_selection(start, end)
        if self._play_selection_btn:
            self._play_selection_btn.setEnabled(True)

    def _update_scrollbar(self) -> None:
        """Sync the scrollbar's range/position to the current view window.

        Uses a fixed-resolution integer range mapped proportionally onto
        [0, duration], since QScrollBar only works in integers but time is
        continuous.
        """
        duration = self._timeline._duration
        span = self._timeline._view_end - self._timeline._view_start
        if duration <= 0 or span >= duration - 1e-6:
            self._time_scrollbar.setEnabled(False)
            self._time_scrollbar.setRange(0, 0)
            return

        resolution = 10000
        self._time_scrollbar.blockSignals(True)
        self._time_scrollbar.setEnabled(True)
        self._time_scrollbar.setRange(0, resolution)
        self._time_scrollbar.setPageStep(max(1, int(span / duration * resolution)))
        self._time_scrollbar.setValue(int(self._timeline._view_start / duration * resolution))
        self._time_scrollbar.blockSignals(False)

    def _on_scrollbar_changed(self, value: int) -> None:
        duration = self._timeline._duration
        if duration <= 0:
            return
        span = self._timeline._view_end - self._timeline._view_start
        new_start = max(0.0, min(duration - span, value / 10000 * duration))
        self._set_shared_view(new_start, new_start + span)

    def _play_selection(self) -> None:
        """Play only the selected span, sample-accurately.

        Slices the already-loaded raw samples to [sel_start, sel_end),
        writes them to a temp WAV, and plays that clip on a dedicated player
        to its own natural end-of-media -- this is what makes the stop point
        exact, since it never relies on pausing a longer stream at the right
        instant (see the attribute comment on ``_selection_player``).
        """
        if self._sel_start is None or self._sel_end is None or not self._selection_player:
            return
        samples_info = self._waveform.get_samples() if self._waveform else None
        if samples_info is None:
            return
        samples, sr = samples_info

        start_idx = max(0, int(self._sel_start * sr))
        end_idx = min(len(samples), int(self._sel_end * sr))
        if end_idx <= start_idx:
            return

        import soundfile as sf

        # Detach the player from its current source before writing the new
        # clip -- on Windows the media backend keeps the file handle open
        # for as long as it's the loaded source, so an old clip may not be
        # deletable yet even after this (see _cleanup_stale_selection_temp_files).
        self._selection_player.stop()
        self._selection_player.setSource(QUrl())
        self._cleanup_stale_selection_temp_files()

        fd, temp_path_str = tempfile.mkstemp(suffix=".wav", prefix="voxkit_selection_")
        os.close(fd)
        temp_path = Path(temp_path_str)
        sf.write(temp_path, samples[start_idx:end_idx], sr, subtype="PCM_16")
        self._selection_temp_paths.append(temp_path)

        if self._player and self._player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self._player.pause()
        self._playing_selection = True
        self._selection_player.setSource(QUrl.fromLocalFile(str(temp_path)))
        self._selection_player.play()

    def _on_selection_position_changed(self, position_ms: int) -> None:
        if not self._playing_selection or self._sel_start is None:
            return
        secs = self._sel_start + position_ms / 1000.0
        if self._sel_end is not None:
            secs = min(secs, self._sel_end)
        for panel in self._synced_panels:
            panel.set_current_time(secs)
        self._update_active_segment_label(secs)

    def _on_selection_media_status_changed(self, status) -> None:
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            self._stop_selection_playback()
            if self._sel_end is not None:
                for panel in self._synced_panels:
                    panel.set_current_time(self._sel_end)
                self._update_active_segment_label(self._sel_end)

    def _stop_selection_playback(self) -> None:
        self._playing_selection = False
        if (
            self._selection_player
            and self._selection_player.playbackState() != QMediaPlayer.PlaybackState.StoppedState
        ):
            self._selection_player.stop()

    def _cleanup_stale_selection_temp_files(self) -> None:
        """Best-effort delete of previous selection-clip temp files.

        The media backend releases its file handle on the *previous* clip
        asynchronously after setSource(QUrl()) -- a fresh clip's immediate
        predecessor may not be deletable yet. Retrying the whole pending
        list on every call (rather than only the newest one) means nothing
        gets silently leaked for the rest of the session once the backend
        does let go.
        """
        still_pending = []
        for path in self._selection_temp_paths:
            try:
                if path.exists():
                    path.unlink()
            except OSError:
                still_pending.append(path)
        self._selection_temp_paths = still_pending

    def _open_audio_externally(self):
        path = self._current_audio_path
        if not path:
            return
        try:
            if sys.platform == "darwin":
                subprocess.run(["open", str(path)], check=False)  # noqa: S603,S607
            elif sys.platform == "win32":
                os.startfile(str(path))  # noqa: S606
            else:
                subprocess.run(["xdg-open", str(path)], check=False)  # noqa: S603,S607
        except (OSError, subprocess.SubprocessError):
            pass

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


__all__ = [
    "SpectrogramPanel",
    "TextGridTimeline",
    "ViewerStacker",
    "WaveformPanel",
    "find_lab",
    "find_textgrid",
    "parse_textgrid",
]
