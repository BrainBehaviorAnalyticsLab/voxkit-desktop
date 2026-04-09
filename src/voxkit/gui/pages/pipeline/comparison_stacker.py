"""Comparison Stacker Module.

Pipeline page for comparing two forced-alignment outputs from the same dataset
using four phoneme-level visualizations from the alignment-comparison-plots library:
counts, mean IoU overlap, overlap rate, and phoneme-pair substitution scatter.

API
---
- **ComparisonStacker**: Alignment comparison workflow UI
"""

import glob
from pathlib import Path

from PyQt6.QtWidgets import (
    QCheckBox,
    QDoubleSpinBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from voxkit.gui.components import MultiColumnComboBox
from voxkit.gui.pages.pipeline.base_stacker import BaseStacker
from voxkit.gui.styles import Buttons, Colors, Containers, Labels
from voxkit.storage import alignments, datasets


def _get_tg_paths(alignment_meta: dict) -> list[str]:
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

    def __init__(self, parent=None):
        # Shared dataset state
        self._dataset_dropdown: MultiColumnComboBox | None = None
        self._dataset_meta: dict | None = None

        # A-side alignment state
        self._a_alignment_dropdown: MultiColumnComboBox | None = None
        self._a_alignment_meta: dict | None = None

        # B-side alignment state
        self._b_alignment_dropdown: MultiColumnComboBox | None = None
        self._b_alignment_meta: dict | None = None

        # Options
        self._tier_input: QLineEdit | None = None
        self._aggregate_cb: QCheckBox | None = None
        self._threshold_spin: QDoubleSpinBox | None = None
        self._compare_btn: QPushButton | None = None

        # Results
        self._results_widget: QWidget | None = None
        self._tab_widget: QTabWidget | None = None

        # Download
        self._dl_folder: str = ""
        self._dl_folder_label: QLabel | None = None
        self._dl_counts_cb: QCheckBox | None = None
        self._dl_overlap_cb: QCheckBox | None = None
        self._dl_rate_cb: QCheckBox | None = None
        self._dl_scatter_cb: QCheckBox | None = None
        self._download_btn: QPushButton | None = None

        # Last comparison parameters (populated on successful compare)
        self._last_comparison: dict | None = None

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
            "padding: 4px; font-size: 12px; color: black; background: white; selection-color: black; selection-background-color: #cce5ff; }"
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

        self.reload_datasets()

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
            [{"id": None, "data": ("Select a dataset first", "", "", "")}],
            ["Engine", "Model", "Date", "Status"],
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

    def reload_datasets(self):
        """Refresh the dataset dropdown from storage."""
        if self._dataset_dropdown is None:
            return

        self._dataset_meta = None
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
                [{"id": None, "data": ("Select a dataset first", "", "", "")}],
                ["Engine", "Model", "Date", "Status"],
                placeholder="Select a dataset first",
            )
            al_dd.setEnabled(False)

        self._update_compare_btn()

    # ── Selection handlers ───────────────────────────────────────────────────

    def _on_dataset_changed(self):
        dataset_id = self._dataset_dropdown.itemData(self._dataset_dropdown.currentIndex())
        self._dataset_meta = None
        self._a_alignment_meta = None
        self._b_alignment_meta = None

        if not dataset_id:
            for al_dd in (self._a_alignment_dropdown, self._b_alignment_dropdown):
                al_dd.set_data(
                    [{"id": None, "data": ("Select a dataset first", "", "", "")}],
                    ["Engine", "Model", "Date", "Status"],
                    placeholder="Select a dataset first",
                )
                al_dd.setEnabled(False)
            self._update_compare_btn()
            return

        self._dataset_meta = datasets.get_dataset_metadata(dataset_id)
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
            for al_dd in (self._a_alignment_dropdown, self._b_alignment_dropdown):
                al_dd.set_data(
                    rows, ["Engine", "Model", "Date", "Status"], placeholder="Select an alignment"
                )
                al_dd.setEnabled(True)
        else:
            for al_dd in (self._a_alignment_dropdown, self._b_alignment_dropdown):
                al_dd.set_data(
                    [{"id": None, "data": ("No alignments found", "", "", "")}],
                    ["Engine", "Model", "Date", "Status"],
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

        label_a = (
            f"{self._a_alignment_meta['engine_id']} / "
            f"{self._a_alignment_meta['model_metadata']['name']}"
        )
        label_b = (
            f"{self._b_alignment_meta['engine_id']} / "
            f"{self._b_alignment_meta['model_metadata']['name']}"
        )

        self.set_status("Running comparison…", "working")

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

        try:
            counts_a = count_phonemes(paths_a, tier_name=tier, normalize=aggregate)
            counts_b = count_phonemes(paths_b, tier_name=tier, normalize=aggregate)
            overlap = compute_phoneme_overlap(paths_a, paths_b, tier_name=tier, normalize=aggregate)
            rates = compute_phoneme_overlap_rate(
                paths_a, paths_b, tier_name=tier, normalize=aggregate, threshold=threshold
            )
            pairs = compute_phoneme_pair_overlap(
                paths_a, paths_b, tier_name=tier, normalize=aggregate
            )
        except Exception as exc:
            self.set_status(f"Comparison failed: {exc}", "error")
            return

        # Cache parameters for download
        self._last_comparison = {
            "paths_a": paths_a,
            "paths_b": paths_b,
            "label_a": label_a,
            "label_b": label_b,
            "tier": tier,
            "aggregate": aggregate,
            "threshold": threshold,
        }

        # Rebuild tab widget — each chart is wrapped in a scroll area so it
        # can expand horizontally/vertically without being clipped.
        self._tab_widget.clear()
        self._tab_widget.addTab(
            _make_scrollable(BarChartWidget(counts_a, counts_b, label_a, label_b)),
            "Phoneme Counts",
        )
        self._tab_widget.addTab(
            _make_scrollable(OverlapChartWidget(overlap)),
            "Overlap (IoU)",
        )
        self._tab_widget.addTab(
            _make_scrollable(OverlapRateWidget(rates, threshold)),
            f"Overlap Rate  ≥{threshold:.2f}",
        )
        self._tab_widget.addTab(
            _make_scrollable(PairScatterWidget(pairs)),
            "Substitutions",
        )

        self._results_widget.setVisible(True)
        self._download_btn.setEnabled(True)

        self.set_status(
            f"Compared {len(paths_a)} + {len(paths_b)} TextGrids  ·  tier: {tier}",
            "success",
        )

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

    # ── Helpers ──────────────────────────────────────────────────────────────

    @staticmethod
    def _make_section_label(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(Labels.SECTION_LABEL)
        return lbl


__all__ = ["ComparisonStacker"]
