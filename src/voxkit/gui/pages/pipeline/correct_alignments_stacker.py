"""Correct Alignments Stacker Module.

Pipeline page for hand-correcting an existing alignment's interval boundaries
by dragging them on a TextGrid timeline, then saving the corrections as a new,
fully-owned alignment (the source alignment is never modified).

API
---
- **EditableTextGridTimeline**: Drag-to-edit variant of TextGridTimeline
- **CorrectAlignmentsStacker**: Correct Alignments workflow UI
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

from PyQt6.QtCore import QEvent, Qt, QUrl, pyqtSignal
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
from voxkit.gui.pages.pipeline.viewer_stacker import (
    MULTIMEDIA_AVAILABLE,
    SpectrogramPanel,
    TextGridTimeline,
    WaveformPanel,
    find_lab,
    find_textgrid,
)
from voxkit.gui.styles import Buttons, Colors, Containers, Labels
from voxkit.storage import alignments, datasets
from voxkit.storage.constants import SUPERSET_AUDIO_EXTENSIONS

if TYPE_CHECKING:
    from PyQt6.QtMultimedia import QAudioOutput, QMediaPlayer

if MULTIMEDIA_AVAILABLE:
    from PyQt6.QtMultimedia import QAudioOutput, QMediaPlayer  # noqa: F811

_AUDIO_EXTENSIONS = SUPERSET_AUDIO_EXTENSIONS
_SILENCE_LABELS = {"", "sp", "sil", "<eps>", "spn"}


# ---------------------------------------------------------------------------
# TextGrid read/write via praatio
# ---------------------------------------------------------------------------


def load_textgrid_as_tiers(path: Path) -> tuple[list[dict], float, float]:
    """Read a TextGrid via praatio into the tier-dict shape TextGridTimeline expects.

    Returns (tiers, min_timestamp, max_timestamp). praatio's own tier-type
    strings ("IntervalTier"/"TextTier") already match the "class" values this
    dict shape has always used, so no translation is needed there.
    """
    from praatio import textgrid as praatio_textgrid

    tg = praatio_textgrid.openTextgrid(str(path), includeEmptyIntervals=True)

    tiers = []
    for tier in tg.tiers:
        if tier.tierType == "IntervalTier":
            intervals = [{"start": e.start, "end": e.end, "label": e.label} for e in tier.entries]
        else:
            intervals = [{"time": e.time, "label": e.label} for e in tier.entries]
        tiers.append({"name": tier.name, "class": tier.tierType, "intervals": intervals})

    return tiers, tg.minTimestamp, tg.maxTimestamp


def save_tiers_to_textgrid(path: Path, tiers: list[dict], min_t: float, max_t: float) -> None:
    """Write tier-dicts back out to a TextGrid file via praatio, atomically.

    Scoped to this feature only -- a hand-rolled writer risks getting
    label-escaping/precision wrong, unacceptable for a research/clinical tool.
    """
    from praatio.data_classes.interval_tier import IntervalTier
    from praatio.data_classes.point_tier import PointTier
    from praatio.data_classes.textgrid import Textgrid
    from praatio.utilities.constants import Interval, Point

    tg = Textgrid(minTimestamp=min_t, maxTimestamp=max_t)
    for tier in tiers:
        if tier["class"] == "IntervalTier":
            entries = [Interval(iv["start"], iv["end"], iv["label"]) for iv in tier["intervals"]]
            tg.addTier(IntervalTier(tier["name"], entries, min_t, max_t))
        else:
            entries = [Point(iv["time"], iv["label"]) for iv in tier["intervals"]]
            tg.addTier(PointTier(tier["name"], entries, min_t, max_t))

    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(path.name + ".tmp")
    tg.save(str(tmp_path), format="long_textgrid", includeBlankSpaces=True)
    os.replace(tmp_path, path)


# ---------------------------------------------------------------------------
# EditableTextGridTimeline
# ---------------------------------------------------------------------------


class EditableTextGridTimeline(TextGridTimeline):
    """Drag-to-edit variant of TextGridTimeline.

    Kept as a subclass rather than adding editing to the shared
    TextGridTimeline itself -- ViewerStacker and ComparisonStacker both
    depend on that class staying read-only/stable, so all drag/edit logic
    lives here alone. No paintEvent override is needed: it already reads
    interval start/end directly from ``self._tiers`` on every repaint, so a
    live drag is reflected for free by mutating that same data and calling
    ``self.update()``.

    Boundary drags follow the confirmed v1 design: a phone-tier boundary that
    coincides with a word-tier boundary (same timestamp) moves both together
    (lockstep), boundaries are clamped so intervals can't invert or cross
    neighbors, and there is no undo/redo -- reloading the file is the only
    way to discard an in-progress edit.
    """

    boundary_edited = pyqtSignal()  # fired once per completed drag-release edit
    boundary_dragging = pyqtSignal(float)  # fired on every move step during a drag, with the time

    BOUNDARY_HIT_PX = 4
    _EPSILON = 1e-6

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._boundary_drag: dict | None = None
        self.setMouseTracking(True)

    def get_tiers(self) -> list[dict]:
        """Return the current (possibly edited) tier data."""
        return self._tiers

    # ── boundary hit-testing ─────────────────────────────────────────────────

    def _iter_interior_boundaries(self):
        """Yield (tier_idx, interval_idx, time) for every draggable boundary.

        Only INTERIOR boundaries (the shared edge between intervals[i] and
        intervals[i+1] within a tier) are draggable -- the file's absolute
        start/end aren't boundaries to correct, they're the recording's own
        extent.
        """
        for tier_idx, tier in enumerate(self._tiers):
            if tier["class"] != "IntervalTier":
                continue
            intervals = tier["intervals"]
            for i in range(len(intervals) - 1):
                yield tier_idx, i, intervals[i]["end"]

    def _hit_test_boundary(self, x: float) -> float | None:
        best_time = None
        best_dist = self.BOUNDARY_HIT_PX + 1
        for _, _, t in self._iter_interior_boundaries():
            dist = abs(self._time_to_x(t) - x)
            if dist < best_dist:
                best_dist = dist
                best_time = t
        return best_time if best_dist <= self.BOUNDARY_HIT_PX else None

    def _boundaries_at_time(self, t: float) -> list[tuple[int, int]]:
        """Every (tier_idx, interval_idx) boundary coincident with time t.

        This is what implements the lockstep move: a phone-tier boundary
        and a word-tier boundary that share the same timestamp both show up
        here and get dragged together.
        """
        return [
            (tier_idx, i)
            for tier_idx, i, bt in self._iter_interior_boundaries()
            if abs(bt - t) < self._EPSILON
        ]

    # ── mouse interaction ────────────────────────────────────────────────────

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton and not (
            event.modifiers() & Qt.KeyboardModifier.ShiftModifier
        ):
            boundary_time = self._hit_test_boundary(event.position().x())
            if boundary_time is not None:
                affected = self._boundaries_at_time(boundary_time)
                clamp_lo = max(
                    self._tiers[t_idx]["intervals"][i]["start"] for t_idx, i in affected
                )
                clamp_hi = min(
                    self._tiers[t_idx]["intervals"][i + 1]["end"] for t_idx, i in affected
                )
                self._boundary_drag = {
                    "affected": affected,
                    "clamp_lo": clamp_lo + self._EPSILON,
                    "clamp_hi": clamp_hi - self._EPSILON,
                }
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._boundary_drag is not None:
            new_t = self._x_to_time(event.position().x())
            new_t = max(
                self._boundary_drag["clamp_lo"], min(self._boundary_drag["clamp_hi"], new_t)
            )
            for tier_idx, i in self._boundary_drag["affected"]:
                intervals = self._tiers[tier_idx]["intervals"]
                intervals[i]["end"] = new_t
                intervals[i + 1]["start"] = new_t
            self.update()
            self.boundary_dragging.emit(new_t)
            return

        # Not dragging -- just hint that a boundary is grabbable nearby.
        near_boundary = self._hit_test_boundary(event.position().x()) is not None
        self.setCursor(
            Qt.CursorShape.SizeHorCursor if near_boundary else Qt.CursorShape.PointingHandCursor
        )
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if self._boundary_drag is not None:
            self._boundary_drag = None
            self.boundary_edited.emit()
            return
        super().mouseReleaseEvent(event)


# ---------------------------------------------------------------------------
# CorrectAlignmentsStacker
# ---------------------------------------------------------------------------


class CorrectAlignmentsStacker(BaseStacker):
    """Correct Alignments pipeline page.

    Walk through: dataset -> source alignment -> speaker -> audio file, then
    drag phone/word interval boundaries on the TextGrid timeline and save the
    corrections. Saving always creates (on first save) or reuses (on
    subsequent saves in the same session) a new, fully-owned alignment --
    the source alignment's own TextGrids are never modified. v1 scope is
    boundaries only (no label-text editing) with no undo/redo; reload the
    file to discard an in-progress, unsaved correction.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        self._dataset_dropdown: MultiColumnComboBox
        self._alignment_dropdown: MultiColumnComboBox
        self._speaker_dropdown: QComboBox
        self._file_list: QListWidget
        self._file_search: QLineEdit
        self._all_audio_files: list[str] = []
        self._selection_section: QWidget
        self._viewer_section: QWidget
        self._timeline: EditableTextGridTimeline
        self._waveform: WaveformPanel
        self._spectrogram: SpectrogramPanel
        self._spectrogram_toggle: QCheckBox
        self._show_spectrogram: bool = False
        self._transcript_edit: QTextEdit
        self._audio_path_label: QLabel
        self._dirty_label: QLabel
        self._save_btn: QPushButton
        self._corrected_name_input: QLineEdit
        self._corrected_path_label: QLabel

        self._current_dataset_meta: datasets.DatasetMetadata | None = None
        self._current_alignment_meta: alignments.AlignmentMetadata | None = None
        self._current_data_path: Path | None = None
        self._current_audio_path: Path | None = None
        self._current_speaker: str | None = None
        self._current_stem: str | None = None
        self._current_tg_min: float = 0.0
        self._current_tg_max: float = 0.0
        self._loaded_tiers: list[dict] = []
        self._dirty: bool = False
        # The corrected alignment created on this file's/session's first
        # save; reused for subsequent saves until the source alignment or
        # dataset selection changes (a new source starts a new session).
        self._corrected_alignment_meta: alignments.AlignmentMetadata | None = None

        # Zoom/scroll/selection state, shared across all synced panels
        self._synced_panels: list = []
        self._time_scrollbar: QScrollBar
        self._sel_start: float | None = None
        self._sel_end: float | None = None
        self._playing_selection: bool = False

        # Multimedia (may remain None if QtMultimedia is unavailable)
        self._player: QMediaPlayer | None = None
        self._audio_output: QAudioOutput | None = None
        self._play_btn: QPushButton | None = None
        self._seek_slider: QSlider | None = None
        self._time_label: QLabel | None = None
        self._play_selection_btn: QPushButton | None = None
        # Dedicated player for "Play Selection" -- see ViewerStacker's
        # identical mechanism: QMediaPlayer.pause() has its own audio-buffer
        # drain latency, so it can't stop exactly on a short phone boundary.
        self._selection_player: QMediaPlayer | None = None
        self._selection_audio_output: QAudioOutput | None = None
        self._selection_temp_paths: list[Path] = []

        super().__init__(parent)

    # ── BaseStacker overrides ────────────────────────────────────────────────

    def get_title(self) -> str:
        return "Correct Alignments"

    def has_status_label(self) -> bool:
        return True

    def build_ui(self):
        # ── ① Dataset ────────────────────────────────────────────────────────
        self.content_layout.addWidget(self._make_section_label("① Choose a Dataset"))

        self._dataset_dropdown = MultiColumnComboBox()
        self._dataset_dropdown.setStyleSheet(Containers.COMBOBOX_STANDARD)
        self._dataset_dropdown.currentIndexChanged.connect(self._on_dataset_changed)
        self.content_layout.addWidget(self._dataset_dropdown)

        # ── ② Source alignment ───────────────────────────────────────────────
        self.content_layout.addWidget(self._make_section_label("② Choose a Source Alignment"))

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

        lbl_row = QHBoxLayout()
        lbl_row.setContentsMargins(0, 0, 0, 0)
        lbl_row.setSpacing(12)
        lbl_row.addWidget(self._make_section_label("③ Speaker"), stretch=1)
        lbl_row.addWidget(self._make_section_label("④ Audio File"), stretch=2)
        sel_col.addLayout(lbl_row)

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
        view_col.addLayout(audio_row)

        if MULTIMEDIA_AVAILABLE:
            self._seek_slider = QSlider(Qt.Orientation.Horizontal)
            self._seek_slider.setRange(0, 0)
            self._seek_slider.sliderMoved.connect(self._seek_to_ms)
            view_col.addWidget(self._seek_slider)

        wf_lbl = QLabel("Waveform")
        wf_lbl.setStyleSheet(Labels.SECTION_LABEL)
        view_col.addWidget(wf_lbl)
        self._waveform = WaveformPanel()
        self._waveform.setStyleSheet(f"border: 1px solid {Colors.BORDER}; border-radius: 4px;")
        view_col.addWidget(self._waveform)

        spec_header = QHBoxLayout()
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

        tg_header = QHBoxLayout()
        tg_lbl = QLabel("TextGrid Alignment  (drag a boundary to correct it)")
        tg_lbl.setStyleSheet(Labels.SECTION_LABEL)
        tg_header.addWidget(tg_lbl)
        tg_header.addStretch()
        self._dirty_label = QLabel("")
        self._dirty_label.setStyleSheet(
            f"QLabel {{ font-size: 12px; font-weight: bold; color: {Colors.WARNING}; }}"
        )
        tg_header.addWidget(self._dirty_label)
        view_col.addLayout(tg_header)

        self._timeline = EditableTextGridTimeline()
        self._timeline.setStyleSheet(f"border: 1px solid {Colors.BORDER}; border-radius: 4px;")
        self._timeline.boundary_edited.connect(self._on_boundary_edited)
        self._timeline.boundary_dragging.connect(self._on_boundary_dragging)
        view_col.addWidget(self._timeline)

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

        self._synced_panels = [self._timeline, self._waveform, self._spectrogram]
        for panel in self._synced_panels:
            panel.seek_requested.connect(self._seek_to_seconds)
            panel.zoom_requested.connect(self._on_zoom_requested)
            panel.pan_requested.connect(self._on_pan_requested)
            panel.selection_changed.connect(self._set_shared_selection)

        # Transcript ──────────────────────────────────────────────────────────
        tr_lbl = QLabel("Transcript")
        tr_lbl.setStyleSheet(Labels.SECTION_LABEL)
        view_col.addWidget(tr_lbl)
        self._transcript_edit = QTextEdit()
        self._transcript_edit.setReadOnly(True)
        self._transcript_edit.setFixedHeight(60)
        self._transcript_edit.setPlaceholderText("No transcript (.lab) found for this file")
        self._transcript_edit.setStyleSheet(
            f"QTextEdit {{ border: 1px solid {Colors.BORDER}; border-radius: 4px; "
            f"padding: 6px; font-size: 13px; background: white; }}"
        )
        view_col.addWidget(self._transcript_edit)

        # Save row ────────────────────────────────────────────────────────────
        save_row = QHBoxLayout()
        save_row.setSpacing(8)
        name_lbl = QLabel("Corrected Alignment Name:")
        name_lbl.setStyleSheet(Labels.INFO_SMALL)
        save_row.addWidget(name_lbl)
        self._corrected_name_input = QLineEdit()
        self._corrected_name_input.setPlaceholderText(
            "optional -- e.g. \"Nina's pass 1\" (helps find/resume it later)"
        )
        self._corrected_name_input.setStyleSheet(
            f"QLineEdit {{ border: 1px solid {Colors.BORDER}; border-radius: 4px; "
            f"padding: 4px 6px; font-size: 12px; background: white; }}"
            f"QLineEdit:focus {{ border-color: {Colors.PRIMARY}; }}"
            f"QLineEdit:disabled {{ background: #ecf0f1; color: {Colors.TEXT_SECONDARY}; }}"
        )
        save_row.addWidget(self._corrected_name_input, stretch=1)
        self._save_btn = QPushButton("Save Corrections")
        self._save_btn.setStyleSheet(Buttons.PRIMARY)
        self._save_btn.setEnabled(False)
        self._save_btn.clicked.connect(self._save_corrections)
        save_row.addWidget(self._save_btn)
        view_col.addLayout(save_row)

        self._corrected_path_label = QLabel("")
        self._corrected_path_label.setStyleSheet(Labels.INFO_SMALL)
        self._corrected_path_label.setWordWrap(True)
        view_col.addWidget(self._corrected_path_label)

        self._viewer_section.setVisible(False)
        self.content_layout.addWidget(self._viewer_section)

        # Tab plays the current selection -- see ViewerStacker's identical
        # event filter for why a plain QShortcut doesn't work here (the
        # dropdowns/search box/file list all claim Tab for focus navigation
        # before a shortcut ever gets a chance).
        QApplication.instance().installEventFilter(self)

        if MULTIMEDIA_AVAILABLE:
            self._audio_output = QAudioOutput()
            self._player = QMediaPlayer()
            self._player.setAudioOutput(self._audio_output)
            self._player.playbackStateChanged.connect(self._on_playback_state_changed)
            self._player.positionChanged.connect(self._on_position_changed)
            self._player.durationChanged.connect(self._on_duration_changed)

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
        self._corrected_alignment_meta = None
        self._corrected_name_input.clear()
        self._corrected_name_input.setEnabled(True)
        self._corrected_path_label.setText("")

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
        # A different source alignment means any in-progress correction
        # session belongs to the old source -- start fresh.
        self._corrected_alignment_meta = None
        self._corrected_name_input.clear()
        self._corrected_name_input.setEnabled(True)
        self._corrected_path_label.setText("")

        if not alignment_id or not self._current_dataset_meta:
            return

        meta = alignments.get_alignment_metadata(self._current_dataset_meta["id"], alignment_id)
        if not meta:
            return

        self._current_alignment_meta = meta
        self._populate_speakers()
        self._selection_section.setVisible(True)
        self.set_status("Select a speaker and audio file to correct", "ready")

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
        self._file_list.clear()
        q = query.strip().lower()
        matches = (
            [f for f in self._all_audio_files if q in f.lower()] if q else self._all_audio_files
        )
        self._file_list.addItems(matches)
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

        self._current_speaker = speaker
        self._current_stem = stem
        self._load_corrector(audio_path, lab_path, tg_path)
        self._viewer_section.setVisible(True)

    def _on_spectrogram_toggled(self, checked: bool) -> None:
        self._show_spectrogram = checked
        self._spectrogram.setVisible(checked)
        if checked and self._current_audio_path and self._current_audio_path.exists():
            self._spectrogram.load_audio(self._current_audio_path)

    # ── Loading ──────────────────────────────────────────────────────────────

    def _load_corrector(self, audio_path: Path, lab_path: Path | None, tg_path: Path | None):
        self._current_audio_path = audio_path
        self._audio_path_label.setText(str(audio_path))
        self._dirty = False
        self._update_dirty_indicator()

        if MULTIMEDIA_AVAILABLE and self._player:
            self._stop_selection_playback()
            self._player.stop()
            self._player.setSource(QUrl.fromLocalFile(str(audio_path)))

        if audio_path.exists():
            self._waveform.load_audio(audio_path)
            if self._show_spectrogram:
                self._spectrogram.load_audio(audio_path)
        else:
            self._waveform.clear()
            self._spectrogram.clear()

        if lab_path and lab_path.exists():
            try:
                self._transcript_edit.setPlainText(lab_path.read_text(encoding="utf-8"))
            except Exception:
                self._transcript_edit.setPlainText(lab_path.read_text(encoding="latin-1"))
        else:
            self._transcript_edit.setPlainText("")
            self._transcript_edit.setPlaceholderText(
                f"No .lab/.txt transcript found for {audio_path.stem}"
            )

        self._timeline.clear()
        self._loaded_tiers = []

        if tg_path and tg_path.exists():
            try:
                tiers, min_t, max_t = load_textgrid_as_tiers(tg_path)
                self._current_tg_min = min_t
                self._current_tg_max = max_t
                duration = max_t
                if duration <= 0 and MULTIMEDIA_AVAILABLE and self._player:
                    duration = self._player.duration() / 1000.0
                self._loaded_tiers = tiers
                self._set_shared_duration(tiers, duration)
            except Exception as exc:
                self.set_status(f"Failed to load TextGrid: {exc}", "error")
                return
        else:
            self.set_status("No TextGrid found for this file -- nothing to correct", "error")
            return

        self.set_status("Drag a phone/word boundary to correct it", "ready")

    # ── Audio player ─────────────────────────────────────────────────────────

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
        if self._seek_slider:
            self._seek_slider.blockSignals(True)
            self._seek_slider.setValue(position_ms)
            self._seek_slider.blockSignals(False)

        if self._time_label and self._player:
            self._time_label.setText(
                f"{self._fmt_ms(position_ms)} / {self._fmt_ms(self._player.duration())}"
            )

        secs = position_ms / 1000.0
        for panel in self._synced_panels:
            panel.set_current_time(secs)

    def _on_duration_changed(self, duration_ms: int):
        if self._seek_slider:
            self._seek_slider.setRange(0, duration_ms)
        if self._timeline and self._loaded_tiers and duration_ms > 0:
            dur_s = duration_ms / 1000.0
            existing = self._timeline._duration
            if abs(existing - dur_s) > 0.001:
                self._set_shared_duration(self._loaded_tiers, dur_s)

    @staticmethod
    def _fmt_ms(ms: int) -> str:
        total_seconds = max(0, ms) // 1000
        return f"{total_seconds // 60}:{total_seconds % 60:02d}"

    def _set_shared_duration(self, tiers: list[dict], duration: float) -> None:
        self._timeline.set_data(tiers, duration)
        for panel in self._synced_panels:
            if panel is not self._timeline:
                panel.set_duration(duration)

        self._stop_selection_playback()
        self._sel_start = None
        self._sel_end = None
        if self._play_selection_btn:
            self._play_selection_btn.setEnabled(False)
        self._update_scrollbar()

    # ── Zoom / scroll / selection ────────────────────────────────────────────

    def _on_zoom_requested(self, anchor_time: float, anchor_fraction: float, factor: float) -> None:
        duration = self._timeline._duration
        if duration <= 0:
            return
        old_span = self._timeline._view_end - self._timeline._view_start
        new_span = max(0.05, min(duration, old_span / factor))
        new_start = anchor_time - anchor_fraction * new_span
        new_start = max(0.0, min(duration - new_span, new_start))
        self._set_shared_view(new_start, new_start + new_span)

    def _on_pan_requested(self, dtime: float) -> None:
        duration = self._timeline._duration
        if duration <= 0:
            return
        span = self._timeline._view_end - self._timeline._view_start
        new_start = max(0.0, min(duration - span, self._timeline._view_start + dtime))
        self._set_shared_view(new_start, new_start + span)

    def _zoom_by(self, factor: float) -> None:
        view_start, view_end = self._timeline._view_start, self._timeline._view_end
        anchor_time = self._timeline._current_time
        if not (view_start <= anchor_time <= view_end):
            anchor_time = (view_start + view_end) / 2
        anchor_fraction = (anchor_time - view_start) / max(1e-9, view_end - view_start)
        self._on_zoom_requested(anchor_time, anchor_fraction, factor)

    def _set_shared_view(self, start: float, end: float) -> None:
        for panel in self._synced_panels:
            panel.set_view(start, end)
        self._update_scrollbar()

    def _set_shared_selection(self, start: float, end: float) -> None:
        self._sel_start, self._sel_end = start, end
        for panel in self._synced_panels:
            panel.set_selection(start, end)
        if self._play_selection_btn:
            self._play_selection_btn.setEnabled(True)

    def _update_scrollbar(self) -> None:
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

    # ── Play Selection (sample-accurate) ─────────────────────────────────────

    def _play_selection(self) -> None:
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

    def _on_selection_media_status_changed(self, status) -> None:
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            self._stop_selection_playback()
            if self._sel_end is not None:
                for panel in self._synced_panels:
                    panel.set_current_time(self._sel_end)

    def _stop_selection_playback(self) -> None:
        self._playing_selection = False
        if (
            self._selection_player
            and self._selection_player.playbackState() != QMediaPlayer.PlaybackState.StoppedState
        ):
            self._selection_player.stop()

    def _cleanup_stale_selection_temp_files(self) -> None:
        still_pending = []
        for path in self._selection_temp_paths:
            try:
                if path.exists():
                    path.unlink()
            except OSError:
                still_pending.append(path)
        self._selection_temp_paths = still_pending

    # ── Boundary editing / saving ────────────────────────────────────────────

    def _on_boundary_edited(self) -> None:
        self._dirty = True
        self._update_dirty_indicator()
        # Drag released -- clear the reference line now that the boundary
        # has settled at its final position.
        self._waveform.set_preview_time(None)
        self._spectrogram.set_preview_time(None)

    def _on_boundary_dragging(self, t: float) -> None:
        """Mirror the boundary being dragged as a dashed reference line in
        the waveform/spectrogram, so the exact position can be lined up
        against spectral/amplitude detail while dragging."""
        self._waveform.set_preview_time(t)
        self._spectrogram.set_preview_time(t)

    def _update_dirty_indicator(self) -> None:
        self._dirty_label.setText("● Unsaved changes" if self._dirty else "")
        self._save_btn.setEnabled(self._dirty)

    def _save_corrections(self) -> None:
        if not self._dirty:
            return
        if (
            not self._current_dataset_meta
            or not self._current_alignment_meta
            or not self._current_speaker
            or not self._current_stem
        ):
            return

        if self._corrected_alignment_meta is None:
            custom_name = self._corrected_name_input.text().strip() or None
            success, result = alignments.create_corrected_alignment(
                self._current_dataset_meta["id"],
                self._current_alignment_meta["id"],
                custom_name=custom_name,
            )
            if not success:
                self.set_status(f"Failed to create corrected alignment: {result}", "error")
                return
            self._corrected_alignment_meta = result
            # Lock the name in for the rest of this session (a session is one
            # dataset+source-alignment combo) and show what it resolved to,
            # so re-opening this same corrected alignment later is
            # recognizable rather than just another timestamped entry.
            self._corrected_name_input.setText(result["model_metadata"]["name"])
            self._corrected_name_input.setEnabled(False)
            self._corrected_path_label.setText(
                f"Corrected alignment stored at: {result['tg_path']}"
            )

        corrected_tg_root = Path(self._corrected_alignment_meta["tg_path"])
        target_path = find_textgrid(corrected_tg_root, self._current_speaker, self._current_stem)
        if target_path is None:
            # Baseline copy should already contain this file; fall back to
            # the source's own relative layout if it somehow doesn't.
            target_path = (
                corrected_tg_root / self._current_speaker / f"{self._current_stem}.TextGrid"
            )

        try:
            save_tiers_to_textgrid(
                target_path,
                self._timeline.get_tiers(),
                self._current_tg_min,
                self._current_tg_max,
            )
        except Exception as exc:
            self.set_status(f"Failed to save corrections: {exc}", "error")
            return

        self._dirty = False
        self._update_dirty_indicator()
        self.set_status(
            f"Saved corrections for {self._current_stem} "
            f"(corrected alignment: {self._corrected_alignment_meta['id']})",
            "success",
        )

    # ── Helpers ──────────────────────────────────────────────────────────────

    @staticmethod
    def _make_section_label(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(Labels.SECTION_LABEL)
        return lbl


__all__ = [
    "CorrectAlignmentsStacker",
    "EditableTextGridTimeline",
    "load_textgrid_as_tiers",
    "save_tiers_to_textgrid",
]
