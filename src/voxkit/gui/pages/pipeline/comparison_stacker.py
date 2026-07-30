"""Comparison Stacker Module.

Pipeline page for comparing two forced-alignment outputs from the same dataset
using four phoneme-level visualizations from the alignment-comparison-plots library:
counts, mean IoU overlap, overlap rate, and phoneme-pair substitution scatter.

API
---
- **ComparisonStacker**: Alignment comparison workflow UI
"""

from __future__ import annotations

import glob
import os
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

from PyQt6.QtCore import QEvent, Qt, QUrl
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QScrollArea,
    QScrollBar,
    QSizePolicy,
    QSlider,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from voxkit.gui.components import MultiColumnComboBox
from voxkit.gui.pages.pipeline.base_stacker import BaseStacker
from voxkit.gui.pages.pipeline.viewer_stacker import (
    SpectrogramPanel,
    TextGridTimeline,
    WaveformPanel,
    find_textgrid,
    parse_textgrid,
)
from voxkit.gui.styles import Buttons, Colors, Containers, Labels
from voxkit.gui.workers.worker_thread import WorkerThread
from voxkit.storage import alignments, datasets
from voxkit.storage.alignments import AlignmentMetadata
from voxkit.storage.constants import SUPERSET_AUDIO_EXTENSIONS
from voxkit.storage.datasets import DatasetMetadata

if TYPE_CHECKING:
    from PyQt6.QtMultimedia import QAudioOutput, QMediaPlayer

try:
    from PyQt6.QtMultimedia import QAudioOutput, QMediaPlayer  # noqa: F811

    MULTIMEDIA_AVAILABLE = True
except ImportError:
    MULTIMEDIA_AVAILABLE = False

_AUDIO_EXTENSIONS = SUPERSET_AUDIO_EXTENSIONS


def _get_tg_paths(alignment_meta: AlignmentMetadata) -> list[str]:
    """Glob all TextGrid files under an alignment's tg_path directory."""
    tg_root = Path(alignment_meta["tg_path"])
    return glob.glob(str(tg_root / "**" / "*.TextGrid"), recursive=True)


def _make_scrollable(widget: QWidget) -> QScrollArea:
    """Wrap a widget in a scroll area that fills the tab uniformly.

    Setting Expanding size policy lets setWidgetResizable grow the chart to
    fill the full tab area; minimum size is still honoured so scrollbars
    appear only when the chart is genuinely wider/taller than the viewport.
    """
    widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
    scroll = QScrollArea()
    scroll.setWidget(widget)
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QScrollArea.Shape.NoFrame)
    scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
    return scroll


class ComparisonStacker(BaseStacker):
    """Alignment comparison pipeline page.

    Select a dataset, then pick two of its alignments (A and B). Click Compare
    to view four phoneme-level plots in a tab widget. Export any subset of plots
    as PNGs to a folder you choose.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        # Widgets set in build_ui() (called by super().__init__)
        self._dataset_dropdown: MultiColumnComboBox
        self._dataset_meta: DatasetMetadata | None = None

        # A-side alignment state
        self._a_alignment_dropdown: MultiColumnComboBox
        self._a_alignment_meta: AlignmentMetadata | None = None

        # B-side alignment state
        self._b_alignment_dropdown: MultiColumnComboBox
        self._b_alignment_meta: AlignmentMetadata | None = None

        # Options
        self._tier_input: QLineEdit
        self._aggregate_cb: QCheckBox
        self._threshold_spin: QDoubleSpinBox
        self._compare_btn: QPushButton
        self._comparison_worker: WorkerThread | None = None
        self._pending_comparison_meta: dict | None = None
        self._pending_comparison_data: dict | None = None

        # Results
        self._results_widget: QWidget
        self._tab_widget: QTabWidget

        # Download
        self._dl_folder: str = ""
        self._dl_folder_label: QLabel
        self._dl_counts_cb: QCheckBox
        self._dl_overlap_cb: QCheckBox
        self._dl_rate_cb: QCheckBox
        self._dl_scatter_cb: QCheckBox
        self._download_btn: QPushButton

        # Last comparison parameters (populated on successful compare)
        self._last_comparison: dict | None = None

        # ── File Inspector: waveform/spectrogram + both alignments' tiers ────
        self._inspector_section: QWidget
        self._inspector_display: QWidget
        self._label_a_widget: QLabel
        self._label_b_widget: QLabel
        self._speaker_dropdown: QComboBox
        self._file_list: QListWidget
        self._file_search: QLineEdit
        self._all_audio_files: list[str] = []
        self._audio_path_label: QLabel
        self._timeline_a: TextGridTimeline
        self._timeline_b: TextGridTimeline
        self._waveform: WaveformPanel
        self._spectrogram: SpectrogramPanel
        self._spectrogram_toggle: QCheckBox
        self._show_spectrogram: bool = False
        self._synced_panels: list = []
        self._time_scrollbar: QScrollBar
        self._current_audio_path: Path | None = None
        self._loaded_tiers_a: list[dict] = []
        self._loaded_tiers_b: list[dict] = []
        # Multimedia (may remain None if QtMultimedia is unavailable)
        self._player: QMediaPlayer | None = None
        self._audio_output: QAudioOutput | None = None
        self._play_btn: QPushButton | None = None
        self._seek_slider: QSlider | None = None
        self._time_label: QLabel | None = None
        self._play_selection_btn: QPushButton | None = None
        self._sel_start: float | None = None
        self._sel_end: float | None = None
        self._playing_selection: bool = False
        # Dedicated player for "Play Selection" -- see ViewerStacker's
        # identical mechanism for why this can't just be the main player
        # paused at the right moment (QMediaPlayer.pause() has its own
        # audio-buffer drain latency, so it can't stop exactly on a short
        # phone boundary).
        self._selection_player: QMediaPlayer | None = None
        self._selection_audio_output: QAudioOutput | None = None
        self._selection_temp_paths: list[Path] = []

        super().__init__(parent)

    # ── BaseStacker overrides ────────────────────────────────────────────────

    def get_title(self) -> str:
        return "Alignment Comparison"

    def has_status_label(self) -> bool:
        return True

    def build_ui(self):
        # ── ① Dataset ────────────────────────────────────────────────────────
        self.content_layout.addWidget(self._make_section_label("① Choose a Dataset"))

        self._dataset_dropdown = MultiColumnComboBox()
        self._dataset_dropdown.setStyleSheet(Containers.COMBOBOX_STANDARD)
        self._dataset_dropdown.currentIndexChanged.connect(self._on_dataset_changed)
        self.content_layout.addWidget(self._dataset_dropdown)

        # ── ② Alignment selectors (side by side) ─────────────────────────────
        self.content_layout.addWidget(
            self._make_section_label("② Choose Two Alignments to Compare")
        )

        al_row = QHBoxLayout()
        al_row.setSpacing(16)
        al_row.addWidget(self._make_alignment_box("A", is_a=True), stretch=1)
        al_row.addWidget(self._make_alignment_box("B", is_a=False), stretch=1)
        self.content_layout.addLayout(al_row)

        # ── ③ File Inspector (hidden until both alignments selected) ─────────
        self.content_layout.addWidget(
            self._make_section_label("③ Inspect a File — Compare Tiers Side-by-Side")
        )
        self._build_inspector_section()
        self.content_layout.addWidget(self._inspector_section)

        # ── Options + Compare row ─────────────────────────────────────────────
        opts = QHBoxLayout()
        opts.setSpacing(12)

        tier_lbl = QLabel("Tier:")
        tier_lbl.setStyleSheet(Labels.SECTION_LABEL)
        opts.addWidget(tier_lbl)

        self._tier_input = QLineEdit("phones")
        self._tier_input.setFixedWidth(90)
        self._tier_input.setStyleSheet(
            f"QLineEdit {{ border: 1px solid {Colors.BORDER}; border-radius: 4px; "
            f"padding: 4px 6px; font-size: 12px; background: white; }}"
            f"QLineEdit:focus {{ border-color: {Colors.PRIMARY}; }}"
        )
        opts.addWidget(self._tier_input)

        self._aggregate_cb = QCheckBox("Aggregate stress  (AH1 → AH)")
        self._aggregate_cb.setStyleSheet(
            "QCheckBox { spacing: 6px; font-size: 12px; color: #2c3e50; }"
        )
        self._aggregate_cb.setChecked(True)
        opts.addWidget(self._aggregate_cb)

        opts.addStretch()

        threshold_lbl = QLabel("IoU threshold:")
        threshold_lbl.setStyleSheet(Labels.SECTION_LABEL)
        opts.addWidget(threshold_lbl)

        self._threshold_spin = QDoubleSpinBox()
        self._threshold_spin.setRange(0.0, 1.0)
        self._threshold_spin.setSingleStep(0.05)
        self._threshold_spin.setValue(0.5)
        self._threshold_spin.setDecimals(2)
        self._threshold_spin.setFixedWidth(70)
        self._threshold_spin.setStyleSheet(
            "QDoubleSpinBox { border: 1px solid #d0d0d0; border-radius: 4px; "
            "padding: 4px; font-size: 12px; color: black; background: white; "
            "selection-color: black; selection-background-color: #cce5ff; }"
        )
        opts.addWidget(self._threshold_spin)

        self._compare_btn = QPushButton("Compare")
        self._compare_btn.setStyleSheet(Buttons.PRIMARY)
        self._compare_btn.setFixedWidth(100)
        self._compare_btn.setEnabled(False)
        self._compare_btn.clicked.connect(self._run_comparison)
        opts.addWidget(self._compare_btn)

        self.content_layout.addLayout(opts)

        # ── Results section (hidden until comparison runs) ────────────────────
        self._results_widget = QWidget()
        results_col = QVBoxLayout(self._results_widget)
        results_col.setContentsMargins(0, 8, 0, 0)
        results_col.setSpacing(10)

        self._tab_widget = QTabWidget()
        self._tab_widget.setFixedHeight(520)
        self._tab_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        results_col.addWidget(self._tab_widget)

        # Download group ──────────────────────────────────────────────────────
        dl_group = QGroupBox("Download Plots")
        dl_group.setStyleSheet(Containers.GROUP_BOX)
        dl_layout = QVBoxLayout(dl_group)
        dl_layout.setSpacing(8)

        checks_row = QHBoxLayout()
        self._dl_counts_cb = QCheckBox("Phoneme Counts")
        self._dl_overlap_cb = QCheckBox("Overlap (IoU)")
        self._dl_rate_cb = QCheckBox("Overlap Rate")
        self._dl_scatter_cb = QCheckBox("Substitutions")
        for cb in (self._dl_counts_cb, self._dl_overlap_cb, self._dl_rate_cb, self._dl_scatter_cb):
            cb.setChecked(True)
            cb.setStyleSheet("QCheckBox { spacing: 6px; font-size: 12px; color: #2c3e50; }")
            checks_row.addWidget(cb)
        checks_row.addStretch()
        dl_layout.addLayout(checks_row)

        folder_row = QHBoxLayout()
        folder_row.setSpacing(8)

        self._dl_folder_label = QLabel("No folder selected")
        self._dl_folder_label.setStyleSheet(Labels.INFO_SMALL)
        self._dl_folder_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        folder_row.addWidget(self._dl_folder_label, stretch=1)

        browse_btn = QPushButton("Select Folder…")
        browse_btn.setStyleSheet(Buttons.BROWSE)
        browse_btn.setFixedWidth(130)
        browse_btn.clicked.connect(self._browse_output_folder)
        folder_row.addWidget(browse_btn)

        self._download_btn = QPushButton("Download")
        self._download_btn.setStyleSheet(Buttons.SUCCESS_SMALL)
        self._download_btn.setFixedWidth(100)
        self._download_btn.setEnabled(False)
        self._download_btn.clicked.connect(self._download_plots)
        folder_row.addWidget(self._download_btn)

        dl_layout.addLayout(folder_row)
        results_col.addWidget(dl_group)

        self._results_widget.setVisible(False)
        self.content_layout.addWidget(self._results_widget)

        # Tab plays the current selection, matching ViewerStacker/Praat's own
        # convention -- see its identical event filter for why a plain
        # QShortcut doesn't work (QComboBox/QLineEdit/QListWidget all claim
        # Tab for their own focus navigation first).
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
            and self._inspector_display.isVisible()
        ):
            self._play_selection()
            return True
        return super().eventFilter(obj, event)

    # ── File Inspector: build ────────────────────────────────────────────────

    def _build_inspector_section(self) -> None:
        """Build the "compare both alignments' tiers on one file" section.

        Reuses ``WaveformPanel``/``SpectrogramPanel``/``TextGridTimeline``
        from viewer_stacker.py verbatim (rather than a new shared composite
        widget) -- one waveform/spectrogram/player shared across two labeled
        ``TextGridTimeline`` instances, one per alignment.
        """
        self._inspector_section = QWidget()
        insp_col = QVBoxLayout(self._inspector_section)
        insp_col.setContentsMargins(0, 4, 0, 0)
        insp_col.setSpacing(4)

        # Speaker + file selection row
        sel_row = QHBoxLayout()
        sel_row.setSpacing(12)

        spk_col = QVBoxLayout()
        spk_lbl = QLabel("Speaker")
        spk_lbl.setStyleSheet(Labels.SECTION_LABEL)
        spk_col.addWidget(spk_lbl)
        self._speaker_dropdown = QComboBox()
        self._speaker_dropdown.setStyleSheet(Containers.COMBOBOX_STANDARD)
        self._speaker_dropdown.currentTextChanged.connect(self._on_speaker_changed)
        spk_col.addWidget(self._speaker_dropdown)
        spk_col.addStretch()
        sel_row.addLayout(spk_col, stretch=1)

        file_col = QVBoxLayout()
        file_lbl = QLabel("Audio File")
        file_lbl.setStyleSheet(Labels.SECTION_LABEL)
        file_col.addWidget(file_lbl)
        self._file_search = QLineEdit()
        self._file_search.setPlaceholderText("Search files...")
        self._file_search.setClearButtonEnabled(True)
        self._file_search.setStyleSheet(
            f"QLineEdit {{ border: 1px solid {Colors.BORDER}; border-radius: 4px; "
            f"padding: 4px 6px; font-size: 12px; background: white; }}"
            f"QLineEdit:focus {{ border-color: {Colors.PRIMARY}; }}"
        )
        self._file_search.textChanged.connect(self._filter_file_list)
        file_col.addWidget(self._file_search)
        self._file_list = QListWidget()
        self._file_list.setFixedHeight(96)
        self._file_list.setStyleSheet(Containers.TABLE_WIDGET)
        self._file_list.currentItemChanged.connect(self._on_file_selected)
        file_col.addWidget(self._file_list)
        sel_row.addLayout(file_col, stretch=2)

        insp_col.addLayout(sel_row)

        # Display (hidden until a file is selected)
        self._inspector_display = QWidget()
        disp_col = QVBoxLayout(self._inspector_display)
        disp_col.setContentsMargins(0, 6, 0, 0)
        disp_col.setSpacing(4)

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
        disp_col.addLayout(audio_row)

        if MULTIMEDIA_AVAILABLE:
            self._seek_slider = QSlider(Qt.Orientation.Horizontal)
            self._seek_slider.setRange(0, 0)
            self._seek_slider.sliderMoved.connect(self._seek_to_ms)
            disp_col.addWidget(self._seek_slider)

        wf_lbl = QLabel("Waveform")
        wf_lbl.setStyleSheet(Labels.SECTION_LABEL)
        disp_col.addWidget(wf_lbl)
        self._waveform = WaveformPanel()
        self._waveform.setStyleSheet(f"border: 1px solid {Colors.BORDER}; border-radius: 4px;")
        disp_col.addWidget(self._waveform)

        spec_header = QHBoxLayout()
        spec_lbl = QLabel("Spectrogram")
        spec_lbl.setStyleSheet(Labels.SECTION_LABEL)
        spec_header.addWidget(spec_lbl)
        spec_header.addStretch()
        self._spectrogram_toggle = QCheckBox("Show Spectrograms (may be slower for large files)")
        self._spectrogram_toggle.setChecked(self._show_spectrogram)
        self._spectrogram_toggle.toggled.connect(self._on_spectrogram_toggled)
        spec_header.addWidget(self._spectrogram_toggle)
        disp_col.addLayout(spec_header)
        self._spectrogram = SpectrogramPanel()
        self._spectrogram.setStyleSheet(f"border: 1px solid {Colors.BORDER}; border-radius: 4px;")
        self._spectrogram.setVisible(self._show_spectrogram)
        disp_col.addWidget(self._spectrogram)

        self._label_a_widget = QLabel("Alignment A")
        self._label_a_widget.setStyleSheet(Labels.SECTION_LABEL)
        disp_col.addWidget(self._label_a_widget)
        self._timeline_a = TextGridTimeline()
        self._timeline_a.setStyleSheet(f"border: 1px solid {Colors.BORDER}; border-radius: 4px;")
        disp_col.addWidget(self._timeline_a)

        self._label_b_widget = QLabel("Alignment B")
        self._label_b_widget.setStyleSheet(Labels.SECTION_LABEL)
        disp_col.addWidget(self._label_b_widget)
        self._timeline_b = TextGridTimeline()
        self._timeline_b.setStyleSheet(f"border: 1px solid {Colors.BORDER}; border-radius: 4px;")
        disp_col.addWidget(self._timeline_b)

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
        disp_col.addLayout(zoom_row)

        self._synced_panels = [
            self._timeline_a,
            self._timeline_b,
            self._waveform,
            self._spectrogram,
        ]
        for panel in self._synced_panels:
            panel.seek_requested.connect(self._seek_to_seconds)
            panel.zoom_requested.connect(self._on_zoom_requested)
            panel.pan_requested.connect(self._on_pan_requested)
            panel.selection_changed.connect(self._set_shared_selection)

        self._inspector_display.setVisible(False)
        insp_col.addWidget(self._inspector_display)

        self._inspector_section.setVisible(False)

    # ── Alignment box builder ────────────────────────────────────────────────

    def _make_alignment_box(self, side: str, *, is_a: bool) -> QGroupBox:
        """Build a labeled group box with a single alignment dropdown."""
        box = QGroupBox(f"Alignment {side}")
        box.setStyleSheet(Containers.GROUP_BOX)
        layout = QVBoxLayout(box)
        layout.setSpacing(6)

        al_dd = MultiColumnComboBox()
        al_dd.setStyleSheet(Containers.COMBOBOX_STANDARD)
        al_dd.set_data(
            [{"id": None, "data": ("Select a dataset first", "", "", "", "")}],
            ["Engine", "Model", "Type", "Date", "Status"],
            placeholder="Select a dataset first",
        )
        al_dd.setEnabled(False)

        if is_a:
            self._a_alignment_dropdown = al_dd
            al_dd.currentIndexChanged.connect(self._on_a_alignment_changed)
        else:
            self._b_alignment_dropdown = al_dd
            al_dd.currentIndexChanged.connect(self._on_b_alignment_changed)

        layout.addWidget(al_dd)
        return box

    # ── Reload hook ──────────────────────────────────────────────────────────

    def reload_datasets(self) -> None:
        """Refresh the dataset dropdown from storage."""
        self._dataset_meta = None
        self._current_data_path = None
        self._a_alignment_meta = None
        self._b_alignment_meta = None

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

        for al_dd in (self._a_alignment_dropdown, self._b_alignment_dropdown):
            al_dd.set_data(
                [{"id": None, "data": ("Select a dataset first", "", "", "", "")}],
                ["Engine", "Model", "Type", "Date", "Status"],
                placeholder="Select a dataset first",
            )
            al_dd.setEnabled(False)

        self._update_compare_btn()

    # ── Selection handlers ───────────────────────────────────────────────────

    def _on_dataset_changed(self):
        dataset_id = self._dataset_dropdown.itemData(self._dataset_dropdown.currentIndex())
        self._dataset_meta = None
        self._current_data_path = None
        self._a_alignment_meta = None
        self._b_alignment_meta = None

        if not dataset_id:
            for al_dd in (self._a_alignment_dropdown, self._b_alignment_dropdown):
                al_dd.set_data(
                    [{"id": None, "data": ("Select a dataset first", "", "", "", "")}],
                    ["Engine", "Model", "Type", "Date", "Status"],
                    placeholder="Select a dataset first",
                )
                al_dd.setEnabled(False)
            self._update_compare_btn()
            return

        self._dataset_meta = datasets.get_dataset_metadata(dataset_id)
        self._current_data_path = (
            datasets.get_dataset_data_path(self._dataset_meta) if self._dataset_meta else None
        )
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
            for al_dd in (self._a_alignment_dropdown, self._b_alignment_dropdown):
                al_dd.set_data(
                    rows,
                    ["Engine", "Model", "Type", "Date", "Status"],
                    placeholder="Select an alignment",
                )
                al_dd.setEnabled(True)
        else:
            for al_dd in (self._a_alignment_dropdown, self._b_alignment_dropdown):
                al_dd.set_data(
                    [{"id": None, "data": ("No alignments found", "", "", "", "")}],
                    ["Engine", "Model", "Type", "Date", "Status"],
                    placeholder="No alignments found",
                )
                al_dd.setEnabled(False)

        self._update_compare_btn()

    def _on_a_alignment_changed(self):
        al_id = self._a_alignment_dropdown.itemData(self._a_alignment_dropdown.currentIndex())
        self._a_alignment_meta = None
        if al_id and self._dataset_meta:
            self._a_alignment_meta = alignments.get_alignment_metadata(
                self._dataset_meta["id"], al_id
            )
        self._update_compare_btn()

    def _on_b_alignment_changed(self):
        al_id = self._b_alignment_dropdown.itemData(self._b_alignment_dropdown.currentIndex())
        self._b_alignment_meta = None
        if al_id and self._dataset_meta:
            self._b_alignment_meta = alignments.get_alignment_metadata(
                self._dataset_meta["id"], al_id
            )
        self._update_compare_btn()

    def _update_compare_btn(self) -> None:
        if self._compare_btn:
            self._compare_btn.setEnabled(bool(self._a_alignment_meta and self._b_alignment_meta))
        self._refresh_inspector_availability()

    def _refresh_inspector_availability(self) -> None:
        both_selected = bool(self._a_alignment_meta and self._b_alignment_meta)
        self._inspector_section.setVisible(both_selected)
        self._speaker_dropdown.clear()
        self._file_list.clear()
        self._all_audio_files = []
        self._inspector_display.setVisible(False)
        if both_selected:
            self._populate_speakers()

    def _populate_speakers(self) -> None:
        if not self._current_data_path or not self._current_data_path.exists():
            return
        speakers = sorted(
            d.name
            for d in self._current_data_path.iterdir()
            if d.is_dir() and not d.name.startswith(".")
        )
        self._speaker_dropdown.addItems(speakers)

    # ── Comparison ───────────────────────────────────────────────────────────

    def _run_comparison(self) -> None:
        if not self._a_alignment_meta or not self._b_alignment_meta:
            return

        paths_a = _get_tg_paths(self._a_alignment_meta)
        paths_b = _get_tg_paths(self._b_alignment_meta)

        if not paths_a:
            self.set_status("No TextGrid files found for Alignment A.", "error")
            return
        if not paths_b:
            self.set_status("No TextGrid files found for Alignment B.", "error")
            return

        tier = self._tier_input.text().strip() or "phones"
        aggregate = self._aggregate_cb.isChecked()
        threshold = self._threshold_spin.value()

        label_a = self._alignment_label(self._a_alignment_meta)
        label_b = self._alignment_label(self._b_alignment_meta)

        try:
            from alignment_comparison_plots.phoneme_counts import BarChartWidget, count_phonemes
            from alignment_comparison_plots.phoneme_overlap import (
                OverlapChartWidget,
                OverlapRateWidget,
                PairScatterWidget,
                compute_phoneme_overlap,
                compute_phoneme_overlap_rate,
                compute_phoneme_pair_overlap,
            )
        except ImportError:
            self.set_status(
                "alignment-comparison-plots not installed. Run: uv add alignment-comparison-plots",
                "error",
            )
            return

        self._pending_comparison_meta = {
            "paths_a": paths_a,
            "paths_b": paths_b,
            "label_a": label_a,
            "label_b": label_b,
            "tier": tier,
            "aggregate": aggregate,
            "threshold": threshold,
            "widget_classes": (
                BarChartWidget,
                OverlapChartWidget,
                OverlapRateWidget,
                PairScatterWidget,
            ),
        }

        def _compute() -> str:
            counts_a = count_phonemes(paths_a, tier_name=tier, normalize=aggregate)
            counts_b = count_phonemes(paths_b, tier_name=tier, normalize=aggregate)
            overlap = compute_phoneme_overlap(paths_a, paths_b, tier_name=tier, normalize=aggregate)
            rates = compute_phoneme_overlap_rate(
                paths_a, paths_b, tier_name=tier, normalize=aggregate, threshold=threshold
            )
            pairs = compute_phoneme_pair_overlap(
                paths_a, paths_b, tier_name=tier, normalize=aggregate
            )
            self._pending_comparison_data = {
                "counts_a": counts_a,
                "counts_b": counts_b,
                "overlap": overlap,
                "rates": rates,
                "pairs": pairs,
            }
            return "Comparison computed"

        # Computing all four comparisons runs synchronously inside this call
        # -- doing it directly on the UI thread would freeze the window and
        # never even paint the "Running comparison…" status before blocking,
        # since Qt defers repaints until the event loop turns over. Running
        # it on a WorkerThread keeps the UI (and BaseStacker's progress bar,
        # which set_status(..., "working") shows automatically) responsive.
        self._compare_btn.setEnabled(False)
        self.set_status("Running comparison…", "working")

        self._comparison_worker = WorkerThread(_compute)
        self._comparison_worker.finished.connect(self._on_comparison_ready)
        self._comparison_worker.start()

    def _on_comparison_ready(self, success: bool, message: str) -> None:
        self._update_compare_btn()

        meta = self._pending_comparison_meta
        self._pending_comparison_meta = None
        if not success or meta is None:
            self.set_status(f"Comparison failed: {message}", "error")
            return

        data = self._pending_comparison_data
        self._pending_comparison_data = None
        assert data is not None  # set by _compute() whenever success is True, same as meta
        bar_chart_cls, overlap_chart_cls, overlap_rate_cls, pair_scatter_cls = meta[
            "widget_classes"
        ]
        label_a, label_b, threshold = meta["label_a"], meta["label_b"], meta["threshold"]

        # Cache parameters for download
        self._last_comparison = {
            "paths_a": meta["paths_a"],
            "paths_b": meta["paths_b"],
            "label_a": label_a,
            "label_b": label_b,
            "tier": meta["tier"],
            "aggregate": meta["aggregate"],
            "threshold": threshold,
        }

        # Rebuild tab widget — each chart is wrapped in a scroll area so it
        # can expand horizontally/vertically without being clipped.
        self._tab_widget.clear()
        self._tab_widget.addTab(
            _make_scrollable(bar_chart_cls(data["counts_a"], data["counts_b"], label_a, label_b)),
            "Phoneme Counts",
        )
        self._tab_widget.addTab(
            _make_scrollable(overlap_chart_cls(data["overlap"])),
            "Overlap (IoU)",
        )
        self._tab_widget.addTab(
            _make_scrollable(overlap_rate_cls(data["rates"], threshold)),
            f"Overlap Rate  ≥{threshold:.2f}",
        )
        self._tab_widget.addTab(
            _make_scrollable(pair_scatter_cls(data["pairs"])),
            "Substitutions",
        )

        self._results_widget.setVisible(True)
        self._download_btn.setEnabled(True)

        n_a, n_b, tier = len(meta["paths_a"]), len(meta["paths_b"]), meta["tier"]
        self.set_status(f"Compared {n_a} + {n_b} TextGrids  ·  tier: {tier}", "success")

    # ── Download ─────────────────────────────────────────────────────────────

    def _browse_output_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Select Output Folder", str(Path.home()))
        if folder:
            self._dl_folder = folder
            self._dl_folder_label.setText(folder)

    def _download_plots(self) -> None:
        if self._last_comparison is None:
            return
        if not self._dl_folder:
            self.set_status("Select an output folder first.", "ready")
            self._browse_output_folder()
            if not self._dl_folder:
                return

        from alignment_comparison_plots import (
            plot_phoneme_counts,
            plot_phoneme_overlap,
            plot_phoneme_overlap_rate,
            plot_phoneme_pair_scatter,
        )

        c = self._last_comparison
        out = Path(self._dl_folder)
        saved: list[str] = []
        errors: list[str] = []

        specs = [
            (self._dl_counts_cb, plot_phoneme_counts, "phoneme_counts.png", {}),
            (self._dl_overlap_cb, plot_phoneme_overlap, "phoneme_overlap.png", {}),
            (
                self._dl_rate_cb,
                plot_phoneme_overlap_rate,
                "phoneme_overlap_rate.png",
                {"threshold": c["threshold"]},
            ),
            (self._dl_scatter_cb, plot_phoneme_pair_scatter, "phoneme_pair_scatter.png", {}),
        ]

        for cb, plot_fn, filename, extra_kwargs in specs:
            if not cb.isChecked():
                continue
            try:
                plot_fn(
                    paths_a=c["paths_a"],
                    paths_b=c["paths_b"],
                    label_a=c["label_a"],
                    label_b=c["label_b"],
                    tier_name=c["tier"],
                    aggregate_emphasis=c["aggregate"],
                    save_png=str(out / filename),
                    exec_=False,
                    **extra_kwargs,
                )
                saved.append(filename)
            except Exception as exc:
                errors.append(f"{filename}: {exc}")

        if errors:
            self.set_status(f"Saved {len(saved)} plot(s); errors: {'; '.join(errors)}", "error")
        elif saved:
            self.set_status(f"Saved {len(saved)} plot(s) to {self._dl_folder}", "success")
        else:
            self.set_status("No plots selected for download.", "ready")

    # ── File Inspector: selection handlers ───────────────────────────────────

    def _on_speaker_changed(self, speaker: str) -> None:
        self._file_list.clear()
        self._all_audio_files = []
        self._inspector_display.setVisible(False)
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

    def _filter_file_list(self, query: str) -> None:
        self._file_list.clear()
        q = query.strip().lower()
        matches = (
            [f for f in self._all_audio_files if q in f.lower()] if q else self._all_audio_files
        )
        self._file_list.addItems(matches)
        if self._inspector_display and self._inspector_display.isVisible():
            self._inspector_display.setVisible(False)

    def _on_file_selected(self, item, _prev=None) -> None:
        if not item:
            self._inspector_display.setVisible(False)
            return

        speaker = self._speaker_dropdown.currentText()
        filename = item.text()
        stem = Path(filename).stem

        if not self._current_data_path or not self._a_alignment_meta or not self._b_alignment_meta:
            return

        audio_path = self._current_data_path / speaker / filename
        tg_path_a = find_textgrid(Path(self._a_alignment_meta["tg_path"]), speaker, stem)
        tg_path_b = find_textgrid(Path(self._b_alignment_meta["tg_path"]), speaker, stem)

        self._load_inspector(audio_path, tg_path_a, tg_path_b)
        self._inspector_display.setVisible(True)

    def _on_spectrogram_toggled(self, checked: bool) -> None:
        self._show_spectrogram = checked
        self._spectrogram.setVisible(checked)
        if checked and self._current_audio_path and self._current_audio_path.exists():
            self._spectrogram.load_audio(self._current_audio_path)

    # ── File Inspector: loading ──────────────────────────────────────────────

    @staticmethod
    def _load_tiers_for_label(tg_path: Path | None) -> tuple[list[dict], str]:
        """Parse a TextGrid for the inspector, returning (tiers, status suffix).

        The suffix is appended to that alignment's header label so a missing
        or unparsable TextGrid is visible right next to the (otherwise empty)
        tier display, rather than silently showing nothing.
        """
        if not tg_path or not tg_path.exists():
            return [], "  (no TextGrid found for this file)"
        try:
            return parse_textgrid(str(tg_path)), ""
        except Exception as exc:
            return [], f"  [TextGrid parse error: {exc}]"

    def _load_inspector(
        self, audio_path: Path, tg_path_a: Path | None, tg_path_b: Path | None
    ) -> None:
        # Only called from _on_file_selected(), right after it's confirmed both
        # are set.
        assert self._a_alignment_meta is not None
        assert self._b_alignment_meta is not None
        self._current_audio_path = audio_path
        self._audio_path_label.setText(str(audio_path))

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

        tiers_a, note_a = self._load_tiers_for_label(tg_path_a)
        tiers_b, note_b = self._load_tiers_for_label(tg_path_b)

        duration = 0.0
        for tiers in (tiers_a, tiers_b):
            for tier in tiers:
                if tier["class"] == "IntervalTier" and tier["intervals"]:
                    duration = max(duration, tier["intervals"][-1]["end"])
        if duration <= 0 and MULTIMEDIA_AVAILABLE and self._player:
            duration = self._player.duration() / 1000.0

        self._loaded_tiers_a = tiers_a
        self._loaded_tiers_b = tiers_b
        self._set_shared_duration(tiers_a, tiers_b, duration)

        label_a = self._alignment_label(self._a_alignment_meta)
        label_b = self._alignment_label(self._b_alignment_meta)
        self._label_a_widget.setText(f"Alignment A — {label_a}{note_a}")
        self._label_b_widget.setText(f"Alignment B — {label_b}{note_b}")

    def _set_shared_duration(
        self, tiers_a: list[dict], tiers_b: list[dict], duration: float
    ) -> None:
        """Push the same duration to every timeline-synced panel.

        Why: keeping this in one place is what guarantees the two TextGrid
        timelines, waveform, and spectrogram panels never disagree on their
        time axis (see TimeAxisMixin) — never call
        ``set_data``/``set_duration`` on them individually from elsewhere.
        """
        self._timeline_a.set_data(tiers_a, duration)
        self._timeline_b.set_data(tiers_b, duration)
        for panel in self._synced_panels:
            if panel not in (self._timeline_a, self._timeline_b):
                panel.set_duration(duration)

        self._stop_selection_playback()
        self._sel_start = None
        self._sel_end = None
        if self._play_selection_btn:
            self._play_selection_btn.setEnabled(False)
        self._update_scrollbar()

    # ── File Inspector: zoom / scroll / selection ────────────────────────────

    def _on_zoom_requested(self, anchor_time: float, anchor_fraction: float, factor: float) -> None:
        """Zoom the shared view in/out, keeping ``anchor_time`` under the cursor."""
        duration = self._timeline_a._duration
        if duration <= 0:
            return
        old_span = self._timeline_a._view_end - self._timeline_a._view_start
        new_span = max(0.05, min(duration, old_span / factor))
        new_start = anchor_time - anchor_fraction * new_span
        new_start = max(0.0, min(duration - new_span, new_start))
        self._set_shared_view(new_start, new_start + new_span)

    def _on_pan_requested(self, dtime: float) -> None:
        """Pan the shared view by ``dtime`` seconds, clamped to the file bounds."""
        duration = self._timeline_a._duration
        if duration <= 0:
            return
        span = self._timeline_a._view_end - self._timeline_a._view_start
        new_start = max(0.0, min(duration - span, self._timeline_a._view_start + dtime))
        self._set_shared_view(new_start, new_start + span)

    def _zoom_by(self, factor: float) -> None:
        """Zoom in/out via the +/- buttons, anchored on the playhead if it's
        within the current view, else the view's midpoint."""
        view_start, view_end = self._timeline_a._view_start, self._timeline_a._view_end
        anchor_time = self._timeline_a._current_time
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
        duration = self._timeline_a._duration
        span = self._timeline_a._view_end - self._timeline_a._view_start
        if duration <= 0 or span >= duration - 1e-6:
            self._time_scrollbar.setEnabled(False)
            self._time_scrollbar.setRange(0, 0)
            return

        resolution = 10000
        self._time_scrollbar.blockSignals(True)
        self._time_scrollbar.setEnabled(True)
        self._time_scrollbar.setRange(0, resolution)
        self._time_scrollbar.setPageStep(max(1, int(span / duration * resolution)))
        self._time_scrollbar.setValue(int(self._timeline_a._view_start / duration * resolution))
        self._time_scrollbar.blockSignals(False)

    def _on_scrollbar_changed(self, value: int) -> None:
        duration = self._timeline_a._duration
        if duration <= 0:
            return
        span = self._timeline_a._view_end - self._timeline_a._view_start
        new_start = max(0.0, min(duration - span, value / 10000 * duration))
        self._set_shared_view(new_start, new_start + span)

    # ── File Inspector: audio player ─────────────────────────────────────────

    def _toggle_playback(self) -> None:
        if not self._player:
            return
        self._stop_selection_playback()
        if self._player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self._player.pause()
        else:
            self._player.play()

    def _stop_playback(self) -> None:
        self._stop_selection_playback()
        if self._player:
            self._player.stop()

    def _seek_to_ms(self, ms: int) -> None:
        self._stop_selection_playback()
        if self._player:
            self._player.setPosition(ms)

    def _seek_to_seconds(self, seconds: float) -> None:
        self._stop_selection_playback()
        if self._player:
            self._player.setPosition(int(seconds * 1000))

    def _on_playback_state_changed(self, state) -> None:
        if self._play_btn is None:
            return
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self._play_btn.setText("⏸  Pause")
        else:
            self._play_btn.setText("▶  Play")

    def _on_position_changed(self, position_ms: int) -> None:
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

    def _on_duration_changed(self, duration_ms: int) -> None:
        if self._seek_slider:
            self._seek_slider.setRange(0, duration_ms)
        # Correct to the audio player's precise duration whenever it
        # meaningfully differs from the TextGrid-derived one -- see the
        # identical fix in ViewerStacker._on_duration_changed for why this
        # tolerance must be symmetric and small.
        if self._timeline_a and (self._loaded_tiers_a or self._loaded_tiers_b) and duration_ms > 0:
            dur_s = duration_ms / 1000.0
            existing = self._timeline_a._duration
            if abs(existing - dur_s) > 0.001:
                self._set_shared_duration(self._loaded_tiers_a, self._loaded_tiers_b, dur_s)

    @staticmethod
    def _fmt_ms(ms: int) -> str:
        total_seconds = max(0, ms) // 1000
        return f"{total_seconds // 60}:{total_seconds % 60:02d}"

    # ── File Inspector: Play Selection (sample-accurate) ─────────────────────

    def _play_selection(self) -> None:
        """Play only the selected span, sample-accurately.

        See ViewerStacker._play_selection for the full rationale: slices the
        already-loaded raw samples to [sel_start, sel_end), writes them to a
        temp WAV, and plays that clip on a dedicated player to its own
        natural end-of-media, since QMediaPlayer.pause() can't stop a longer
        stream exactly at a short phone boundary.
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
        """Best-effort delete of previous selection-clip temp files.

        See ViewerStacker's identical method: the media backend releases its
        file handle on the *previous* clip asynchronously, so a fresh clip's
        immediate predecessor may not be deletable yet -- retry the whole
        pending list on every call rather than leaking it.
        """
        still_pending = []
        for path in self._selection_temp_paths:
            try:
                if path.exists():
                    path.unlink()
            except OSError:
                still_pending.append(path)
        self._selection_temp_paths = still_pending

    # ── Helpers ──────────────────────────────────────────────────────────────

    @staticmethod
    def _alignment_label(meta: AlignmentMetadata) -> str:
        return f"{meta['engine_id']} / {meta['model_metadata']['name']}"

    @staticmethod
    def _make_section_label(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(Labels.SECTION_LABEL)
        return lbl


__all__ = ["ComparisonStacker"]
