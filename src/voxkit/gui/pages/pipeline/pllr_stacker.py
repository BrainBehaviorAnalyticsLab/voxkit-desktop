"""PLLR Stacker Module.

Pipeline page for extracting PLLR (Goodness of Pronunciation) scores using PLLR.

API
---
- **PLLRStacker**: PLLR extraction workflow UI
- **get_pllr_settings_config**: Returns PLLR settings configuration

Notes
-----
- PLLR = Probabilistic Linear Likelihood Ratio
- Requires existing alignments (TextGrids) and audio files
- Outputs phonewise and framewise probability CSVs
"""

import csv
import logging
import re
from datetime import datetime
from pathlib import Path

from pypllrcomputer import compute_pllr
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from voxkit.config import Defaults
from voxkit.gui.components import MultiColumnComboBox
from voxkit.gui.frameworks.settings_modal import (
    FieldConfig,
    FieldType,
    GenericDialog,
    SettingsConfig,
)
from voxkit.gui.styles import Buttons, Containers, Labels
from voxkit.gui.utils import validate_path, validate_paths
from voxkit.gui.workers.worker_thread import WorkerThread
from voxkit.storage import alignments, datasets
from voxkit.storage.utils import get_storage_root

logger = logging.getLogger(__name__)

FIELDS: list[FieldConfig] = [
    FieldConfig(
        name="acoustic_model",
        label="Acoustic Model:",
        field_type=FieldType.LINEEDIT,
        default_value="pkadambi/w2v2_pronunciation_score_model",
        tooltip="HuggingFace model name or path to local model directory.",
    ),
    FieldConfig(
        name="phone_key",
        label="Phone Key:",
        field_type=FieldType.LINEEDIT,
        default_value="phones",
        tooltip="Key in the model's config for phone labels.",
    ),
    FieldConfig(
        name="recompute_probas",
        label="Recompute Probabilities:",
        field_type=FieldType.CHECKBOX,
        default_value=True,
        tooltip="Check to recompute framewise probabilities even if cached data exists.",
    ),
    FieldConfig(
        name="likelihood_dct",
        label="Likelihood Dict Path:",
        field_type=FieldType.LINEEDIT,
        default_value="",  # Will be set at runtime
        tooltip="Path to save/load the computed likelihood dictionary.",
    ),
    FieldConfig(
        name="aggregation_function",
        label="Aggregation Function:",
        field_type=FieldType.COMBOBOX,
        default_value="aggregate_by_phoneme_occurrence",
        options=[
            "aggregate_by_phoneme_occurrence",
            "aggregate_by_unique_phonemes_in_utterance",
            "aggregate_by_utterance",
            "aggregate_by_phoneme_per_speaker",
            "aggregate_by_type_per_speaker",
            "aggregate_by_speaker",
        ],
        tooltip="Method to aggregate framewise probabilities into phonewise scores.",
    ),
]


def get_pllr_settings_config() -> SettingsConfig:
    """Get PLLR settings config with runtime-computed default paths."""
    # Find the likelihood_dct field and set its default value at runtime
    fields = FIELDS.copy()
    for field in fields:
        if field.name == "likelihood_dct" and not field.default_value:
            field.default_value = str(
                get_storage_root() / "computed-likelihoods" / "likelihood_dict.pkl"
            )

    return SettingsConfig(
        title="PLLR Extraction Settings",
        dimensions=(400, 400),
        apply_blur=True,
        fields=fields,
        store_file="pllr_settings.json",
    )


def _append_run_metadata_to_csv(csv_path: str, run_metadata: dict[str, str]) -> None:
    """Append run metadata columns to every row of a GOP output CSV, in place.

    Why: compute_pllr() (external pypllrcomputer package) writes phonewise/
    framewise CSVs with no provenance info, making it impossible to trace a
    results file back to the corpus, engine, and model that produced it once
    it's been moved or shared. Appending columns here avoids touching the
    external package.

    Args:
        csv_path: Path to the CSV file to enrich. No-op if it doesn't exist.
        run_metadata: Column name -> value pairs appended to every row.
    """
    path = Path(csv_path)
    if not path.exists():
        return

    with open(path, "r", encoding="utf-8", newline="") as f:
        rows = list(csv.reader(f))

    if not rows:
        return

    header, *data_rows = rows
    metadata_columns = list(run_metadata.keys())
    metadata_values = [run_metadata[key] for key in metadata_columns]

    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header + metadata_columns)
        writer.writerows(row + metadata_values for row in data_rows)


def _sanitize_filename_part(text: str) -> str:
    """Make a string safe to embed in a filename across platforms."""
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "_", text.strip())
    return cleaned.strip("_") or "unknown"


def _rename_with_run_metadata(
    csv_path: str, corpus_name: str, engine_id: str, date_stamp: str
) -> str:
    """Rename a GOP output CSV to embed corpus/engine/date, returning the new path.

    Why: the appended metadata columns identify a file's provenance once
    opened, but don't help distinguish files at a glance in a file browser
    when working across multiple corpora, engines, or runs.
    """
    path = Path(csv_path)
    if not path.exists():
        return csv_path

    suffix = "_".join(
        _sanitize_filename_part(part) for part in (corpus_name, engine_id, date_stamp)
    )
    new_path = path.with_name(f"{path.stem}_{suffix}{path.suffix}")
    path.rename(new_path)
    return str(new_path)


class PLLRStacker(QWidget):
    """PLLR extraction pipeline page.

    Allows users to extract Goodness of Pronunciation scores from
    existing alignments using the PLLR (Probabilistic Linear Likelihood Ratio) method.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__()
        self._parent_widget = parent
        self.pllr_dataset_dropdown: MultiColumnComboBox
        self.pllr_alignment_dropdown: MultiColumnComboBox
        self.init_ui()

    def on_extract_settings(self):
        settings_dialog = GenericDialog(self, get_pllr_settings_config())

        result = settings_dialog.exec()

        # Clean up blur applied by GenericDialog to self.parent()
        if self.parent():
            self.parent().setGraphicsEffect(None)

        if result == QDialog.DialogCode.Accepted:
            settings_dialog.save()

    def on_dataset_selected(self):
        """Handle dataset selection change and load corresponding alignments"""
        selected_index = self.pllr_dataset_dropdown.currentIndex()
        selected_dataset_id = self.pllr_dataset_dropdown.itemData(selected_index)

        # Clear alignment dropdown
        self.pllr_alignment_dropdown.clear()

        if selected_dataset_id and selected_dataset_id != "No datasets registered":
            # Load alignments for this dataset
            alignments_list = alignments.list_alignments(selected_dataset_id)

            if alignments_list:
                rows = []
                for alignment in alignments_list:
                    # Display format: "EngineID - ModelName (Date)"
                    rows.append(
                        {
                            "id": alignment["id"],
                            "data": (
                                alignment["engine_id"],
                                alignment["model_metadata"]["name"],
                                alignments.get_alignment_type(alignment),
                                alignment["alignment_date"],
                                alignment["status"],
                            ),
                        }
                    )

                self.pllr_alignment_dropdown.set_data(
                    rows,
                    ["Engine ID", "Model Name", "Type", "Date Registered", "Status"],
                    placeholder="Click to select an alignment",
                )

                self.pllr_alignment_dropdown.setEnabled(True)
            else:
                self.pllr_alignment_dropdown.set_data(
                    [{"id": None, "data": ("No alignments registered", "", "")}],
                    ["Method", "Model", "Date", "Status"],
                    placeholder="No alignments registered",
                )
                self.pllr_alignment_dropdown.setEnabled(False)
        else:
            self.pllr_alignment_dropdown.set_data([], [])
            self.pllr_alignment_dropdown.setEnabled(False)

    def reload_datasets(self):
        """Reload datasets in the dropdown"""
        self.pllr_dataset_dropdown.clear()
        datasets_meta = datasets.list_datasets_metadata()
        data = []
        headers = ["Name", "Date", "Description"]
        if datasets_meta:
            for d in datasets_meta:
                name = d["name"]
                date_registered = d["registration_date"]
                id = d["id"]
                description = d["description"]
                data.append({"id": id, "data": (name, date_registered, description)})
            self.pllr_dataset_dropdown.set_data(data, headers, placeholder="Select a dataset")
            self.pllr_dataset_dropdown.setEnabled(True)
        else:
            self.pllr_dataset_dropdown.set_data([], [], placeholder="No datasets registered")
            self.pllr_dataset_dropdown.setEnabled(False)
        self.pllr_alignment_dropdown.set_data(
            [{"id": None, "data": ("Select a dataset first", "", "")}],
            ["Method", "Model", "Date", "Status"],
            placeholder="Select a dataset first",
        )  # Line 151
        self.pllr_alignment_dropdown.setEnabled(False)

    def init_ui(self):
        """Create the extract PLLR scores page"""
        self.setMinimumWidth(600)
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(30, 30, 30, 30)

        # Header with title and settings button
        header_layout = QHBoxLayout()

        # Title
        title = QLabel("Extract PLLR Scoring")
        title.setStyleSheet(Labels.PAGE_TITLE)
        header_layout.addWidget(title)

        header_layout.addStretch()

        # Settings button
        settings_btn = QPushButton("⚙️")
        settings_btn.setFixedSize(65, 40)
        settings_btn.setStyleSheet(Buttons.ICON)
        settings_btn.clicked.connect(self.on_extract_settings)
        header_layout.addWidget(settings_btn)

        layout.addLayout(header_layout)

        layout.addSpacing(10)

        # Dataset selection dropdown
        dataset_label = QLabel("① Choose a PLLR Dataset")
        dataset_label.setStyleSheet(Labels.SECTION_LABEL)
        layout.addWidget(dataset_label)

        self.pllr_dataset_dropdown = MultiColumnComboBox()
        self.pllr_dataset_dropdown.setStyleSheet(Containers.COMBOBOX_STANDARD)

        # Connect to selection handler
        self.pllr_dataset_dropdown.currentIndexChanged.connect(self.on_dataset_selected)

        layout.addWidget(self.pllr_dataset_dropdown)

        # Alignment selection dropdown (initially disabled)
        alignment_label = QLabel("② Choose an Alignment")
        alignment_label.setStyleSheet(Labels.SECTION_LABEL)
        layout.addWidget(alignment_label)

        self.pllr_alignment_dropdown = MultiColumnComboBox()
        self.pllr_alignment_dropdown.setStyleSheet(Containers.COMBOBOX_STANDARD)

        self.pllr_alignment_dropdown.set_data(
            [{"id": None, "data": ("Select a dataset first", "", "")}],
            ["Method", "Model", "Date", "Status"],
            placeholder="Select a dataset first",
        )
        self.pllr_alignment_dropdown.setEnabled(False)

        layout.addWidget(self.pllr_alignment_dropdown)

        # Populate with registered datasets
        self.reload_datasets()

        # Output Path
        extract_output_label = QLabel("③ Output Path")
        extract_output_label.setStyleSheet(Labels.SECTION_LABEL)
        layout.addWidget(extract_output_label)

        extract_output_layout = QHBoxLayout()
        extract_output_layout.setSpacing(5)
        self.extract_output_path = QLineEdit(Defaults["output_path"])
        self.extract_browse = QPushButton("Browse")
        self.extract_browse.setFixedWidth(100)
        self.extract_browse.setStyleSheet(Buttons.BROWSE)
        self.extract_browse.clicked.connect(lambda: self.browse_directory(self.extract_output_path))
        extract_output_layout.addWidget(self.extract_output_path, stretch=1)
        extract_output_layout.addWidget(self.extract_browse)
        layout.addLayout(extract_output_layout)

        layout.addSpacing(15)

        # Extract PLLR Button
        self.extract_btn = QPushButton("④ Start PLLR Extraction")
        self.extract_btn.setMinimumHeight(45)
        self.extract_btn.setStyleSheet(Buttons.PRIMARY)
        self.extract_btn.clicked.connect(self.on_extract_pllr)
        layout.addWidget(self.extract_btn)

        # Status label
        self.extract_status = QLabel("Ready")
        self.extract_status.setStyleSheet(Labels.INFO_SMALL)
        self.extract_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.extract_status)

        # Indeterminate (busy) bar: range (0, 0) makes Qt render a bouncing
        # bar instead of a percentage, since work here has no known progress.
        self.extract_progress = QProgressBar()
        self.extract_progress.setRange(0, 0)
        self.extract_progress.setTextVisible(False)
        self.extract_progress.setStyleSheet(Containers.PROGRESS_BAR)
        self.extract_progress.setVisible(False)
        layout.addWidget(self.extract_progress)

        layout.addStretch()
        return self

    def browse_directory(self, line_edit):
        """Open directory browser and update the line edit"""
        directory = QFileDialog.getExistingDirectory(
            self,
            "Select Directory",
            line_edit.text() if Path(line_edit.text()).exists() else str(Path.home()),
        )
        if directory:
            line_edit.setText(directory)
            if not validate_path(self, directory):
                QMessageBox.warning(self, "Invalid Path", f"The path does not exist:\n{directory}")

    def on_extract_pllr(self):
        """Handle Extract PLLR button click"""
        # Get selected dataset
        selected_index = self.pllr_dataset_dropdown.currentIndex()
        selected_dataset_id = self.pllr_dataset_dropdown.itemData(selected_index)

        if not selected_dataset_id or selected_dataset_id == "No datasets registered":
            logger.warning("PLLR extraction aborted: no dataset selected")
            QMessageBox.warning(
                self, "No Dataset Selected", "Please select a dataset from the dropdown."
            )
            return

        # Get selected alignment
        alignment_index = self.pllr_alignment_dropdown.currentIndex()
        selected_alignment_id = self.pllr_alignment_dropdown.itemData(alignment_index)

        if not selected_alignment_id:
            logger.warning("PLLR extraction aborted: no alignment selected")
            QMessageBox.warning(
                self, "No Alignment Selected", "Please select an alignment from the dropdown."
            )
            return

        # Get alignment path
        alignment_data = alignments.get_alignment_metadata(
            selected_dataset_id, selected_alignment_id
        )
        if not alignment_data:
            logger.error("Could not find alignment data for ID %s", selected_alignment_id)
            QMessageBox.warning(
                self,
                "Invalid Alignment",
                f"Could not find alignment data for ID '{selected_alignment_id}'.",
            )
            return

        # tg_path is always the alignment's actual TextGrid directory --
        # every alignment-creation path (create_alignment, create_hand_alignment,
        # create_corrected_alignment) writes directly into it, never into a
        # nested "cache" subfolder. That subfolder only exists for a *dataset's*
        # cached audio (see get_dataset_data_path), a separate concept this
        # used to incorrectly conflate with an alignment's `local` flag --
        # which silently worked only because no alignment type previously had
        # local=True without also being on a non-cached dataset; corrected
        # alignments are always local=True regardless of the dataset's own
        # cached flag, which is what exposed this.
        textgrid_path = alignment_data["tg_path"]

        if not textgrid_path or not Path(textgrid_path).exists():
            logger.error("TextGrid path does not exist: %s", textgrid_path)
            QMessageBox.warning(
                self,
                "Invalid Alignment Path",
                f"Alignment output path does not exist: {textgrid_path}",
            )
            return

        # Get dataset path
        dataset_meta = datasets.get_dataset_metadata(selected_dataset_id)
        if not dataset_meta:
            logger.error("Could not find dataset metadata for ID %s", selected_dataset_id)
            QMessageBox.warning(self, "Invalid Dataset", "Could not find dataset metadata.")
            return

        wavlab_path: Path | str | None = datasets.get_dataset_data_path(dataset_meta)

        if not wavlab_path:
            logger.error("Could not resolve dataset path for ID %s", selected_dataset_id)
            QMessageBox.warning(self, "Invalid Dataset", "Could not find path for dataset.")
            return

        # Validate inputs
        paths = {
            "TextGrid Path": textgrid_path,
            "Wav/lab Path": wavlab_path,
            "Output Path": self.extract_output_path.text(),
        }

        if not validate_paths(self, paths):
            logger.warning("PLLR path validation failed: %s", paths)
            return

        # Get current settings
        output_path = self.extract_output_path.text()

        logger.info(
            "Extracting PLLR: dataset=%s alignment=%s textgrids=%s wavlab=%s output=%s",
            selected_dataset_id,
            selected_alignment_id,
            textgrid_path,
            wavlab_path,
            output_path,
        )

        # Update UI
        self.extract_status.setText("Processing...")
        self.extract_status.setStyleSheet("color: #f39c12; font-size: 12px; margin-top: 5px;")
        self.extract_progress.setVisible(True)
        self.extract_btn.setEnabled(False)

        # Start worker thread
        self.worker = WorkerThread(
            lambda: self.extract_pllr_logic(
                textgrid_path, wavlab_path, output_path, dataset_meta, alignment_data
            )
        )
        self.worker.finished.connect(self.on_extract_finished)
        self.worker.start()

    def extract_pllr_logic(
        self, textgrid_path, wavlab_path, output_path, dataset_meta=None, alignment_data=None
    ):
        """Actual PLLR extraction logic"""

        phonewise_path = str(Path(output_path) / "phonewise_proba.csv")
        framewise_path = str(Path(output_path) / "framewise_proba.csv")

        # Input inventory -- the usual cause of an empty result is one of these
        # directories not containing what the caller assumed.
        tg_path_obj = Path(textgrid_path)
        if tg_path_obj.is_dir():
            logger.debug(
                "Found %d .TextGrid files in %s",
                len(list(tg_path_obj.glob("*.TextGrid"))),
                textgrid_path,
            )
        else:
            logger.warning("TextGrid path is not a directory: %s", textgrid_path)

        wav_path_obj = Path(wavlab_path)
        if wav_path_obj.is_dir():
            logger.debug(
                "Found %d .wav files in %s", len(list(wav_path_obj.glob("*.wav"))), wavlab_path
            )
        else:
            logger.warning("Wav/lab path is not a directory: %s", wavlab_path)

        # READ THE SETTINGS FROM THE FILE
        path_to_pllr_settings = get_storage_root() / "pllr_settings.json"
        pllr_settings = {}
        if path_to_pllr_settings.exists():
            from json import load as json_load

            with open(path_to_pllr_settings, "r", encoding="utf-8") as f:
                pllr_settings = json_load(f)
            logger.debug("Loaded PLLR settings from %s", path_to_pllr_settings)
        else:
            config = get_pllr_settings_config()
            for key in config.fields:
                pllr_settings[key.name] = key.default_value
            logger.debug("No settings at %s; using defaults", path_to_pllr_settings)

        logger.debug(
            "Calling compute_pllr(tg=%s, wav=%s, phonewise=%s, framewise=%s)",
            textgrid_path,
            wavlab_path,
            phonewise_path,
            framewise_path,
        )

        try:
            from pypllrcomputer.pypllr_compute import (
                aggregate_by_phoneme_occurrence,
                aggregate_by_phoneme_per_speaker,
                aggregate_by_speaker,
                aggregate_by_type_per_speaker,
                aggregate_by_unique_phonemes_in_utterance,
                aggregate_by_utterance,
            )

            _agg_fns = {
                "aggregate_by_phoneme_occurrence": aggregate_by_phoneme_occurrence,
                "aggregate_by_unique_phonemes_in_utterance": (
                    aggregate_by_unique_phonemes_in_utterance
                ),
                "aggregate_by_utterance": aggregate_by_utterance,
                "aggregate_by_phoneme_per_speaker": aggregate_by_phoneme_per_speaker,
                "aggregate_by_type_per_speaker": aggregate_by_type_per_speaker,
                "aggregate_by_speaker": aggregate_by_speaker,
            }
            agg_key = pllr_settings.get("aggregation_function", "aggregate_by_phoneme_occurrence")
            agg_fn = _agg_fns.get(agg_key, aggregate_by_phoneme_occurrence)

            compute_pllr(
                tg_files_path=textgrid_path,
                wav_files_path=wavlab_path,
                phone_key="phones",
                phonewise_proba_df=phonewise_path,
                framewise_proba_df=framewise_path,
                recompute_probas=pllr_settings.get("recompute_probas", True),
                likelihood_dct=pllr_settings.get("likelihood_dct", None),
                aggregation_function=agg_fn,
            )
            logger.debug("compute_pllr() completed successfully")

            model_metadata = (alignment_data or {}).get("model_metadata") or {}
            now = datetime.now()
            run_metadata = {
                "run_datetime": now.isoformat(timespec="seconds"),
                "corpus_name": (dataset_meta or {}).get("name", ""),
                "corpus_id": (dataset_meta or {}).get("id", ""),
                "engine_id": (alignment_data or {}).get("engine_id", ""),
                "model_name": model_metadata.get("name", ""),
                "model_id": model_metadata.get("id", ""),
            }
            # Full timestamp (not just date) so multiple runs on the same day
            # against the same corpus/engine never collide on rename below.
            date_stamp = now.strftime("%Y%m%d_%H%M%S")

            # compute_pllr() writes phonewise_path verbatim only when the
            # aggregation function returns a single DataFrame. Aggregations
            # like aggregate_by_phoneme_occurrence return a dict of
            # per-statistic DataFrames instead, written to
            # "{stem}_{method}.csv" (e.g. phonewise_proba_mean.csv) — so glob
            # for every variant rather than assuming the literal filename.
            phonewise_stem = Path(phonewise_path).stem
            phonewise_outputs = list(Path(phonewise_path).parent.glob(f"{phonewise_stem}*.csv"))
            if not phonewise_outputs:
                logger.warning("No phonewise output CSVs found matching %s*.csv", phonewise_stem)

            output_paths = [*phonewise_outputs, Path(framewise_path)]
            renamed_paths = []
            for csv_path in output_paths:
                _append_run_metadata_to_csv(str(csv_path), run_metadata)
                renamed_paths.append(
                    _rename_with_run_metadata(
                        str(csv_path),
                        run_metadata["corpus_name"],
                        run_metadata["engine_id"],
                        date_stamp,
                    )
                )
            logger.info("Appended run metadata and renamed output CSVs: %s", renamed_paths)

            return "PLLR extracted successfully"
        except Exception:
            # logger.exception records the traceback, so the manual
            # traceback.format_exc() dance is no longer needed.
            logger.exception("compute_pllr() failed")
            raise

    def on_extract_finished(self, success, message):
        """Handle completion of extract PLLR operation"""
        self.extract_btn.setEnabled(True)
        self.extract_progress.setVisible(False)

        if success:
            logger.info("PLLR extraction finished: %s", message)
            self.extract_status.setText("✓ " + message)
            self.extract_status.setStyleSheet("color: #27ae60; font-size: 12px; margin-top: 5px;")
            QMessageBox.information(self, "Success", message)
        else:
            logger.error("PLLR extraction failed: %s", message)
            self.extract_status.setText("✗ Error occurred")
            self.extract_status.setStyleSheet("color: #e74c3c; font-size: 12px; margin-top: 5px;")
            QMessageBox.critical(self, "Error", f"An error occurred:\n{message}")
