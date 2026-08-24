"""Tests for manual-alignment filtering in TrainingStacker.

Training against machine-generated alignments teaches a model whatever errors
those alignments already contain, so both dropdowns on the Train Aligners page
list only hand/corrected data. These guard the filter and, just as importantly,
the empty states -- "nothing registered" and "nothing that qualifies" are
different problems and must not collapse into the same message.
"""

import pytest

from voxkit.gui.pages.pipeline import training_stacker
from voxkit.gui.pages.pipeline.training_stacker import (
    MANUAL_ALIGNMENT_NOTICE,
    TrainingStacker,
)


class _Dropdown:
    """Records what the stacker put in a dropdown, without needing a real widget."""

    def __init__(self, current_id=None):
        self.rows = None
        self.headers = None
        self.placeholder = None
        self.enabled = None
        self._current_id = current_id

    def set_data(self, rows, headers=None, placeholder=None):
        self.rows = rows
        self.headers = headers
        self.placeholder = placeholder

    def setEnabled(self, value):  # noqa: N802 - Qt naming
        self.enabled = value

    def current_id(self):
        return self._current_id

    def ids(self):
        return [row["id"] for row in self.rows]


def _dataset(dataset_id, name="Dataset"):
    return {
        "id": dataset_id,
        "name": name,
        "registration_date": "2026-01-01",
        "description": "",
    }


def _alignment(alignment_id, alignment_type, engine_id="MFAENGINE"):
    return {
        "id": alignment_id,
        "engine_id": engine_id,
        "alignment_type": alignment_type,
        "model_metadata": {"name": "english_us_arpa"},
        "alignment_date": "2026-01-02",
        "status": "completed",
    }


@pytest.fixture
def stacker():
    """A TrainingStacker with only the attributes these handlers touch."""
    instance = TrainingStacker.__new__(TrainingStacker)
    instance.train_dataset_dropdown = _Dropdown(current_id="ds1")
    instance.train_alignment_dropdown = _Dropdown()
    return instance


class TestDatasetDropdownFilter:
    def test_lists_only_datasets_with_manual_alignments(self, monkeypatch, stacker):
        monkeypatch.setattr(
            training_stacker.datasets,
            "list_datasets_metadata",
            lambda: [_dataset("ds1"), _dataset("ds2"), _dataset("ds3")],
        )
        monkeypatch.setattr(
            training_stacker.alignments,
            "has_manual_alignments",
            lambda dataset_id: dataset_id in {"ds1", "ds3"},
        )

        stacker._populate_dataset_dropdown()

        assert stacker.train_dataset_dropdown.ids() == ["ds1", "ds3"]
        assert stacker.train_dataset_dropdown.enabled is True

    def test_registered_but_unqualified_datasets_get_their_own_message(self, monkeypatch, stacker):
        """The user has datasets; they just cannot be trained on yet. Telling them
        "No datasets registered" here would send them off to register a duplicate."""
        monkeypatch.setattr(
            training_stacker.datasets,
            "list_datasets_metadata",
            lambda: [_dataset("ds1"), _dataset("ds2")],
        )
        monkeypatch.setattr(training_stacker.alignments, "has_manual_alignments", lambda _: False)

        stacker._populate_dataset_dropdown()

        assert stacker.train_dataset_dropdown.placeholder == "No datasets with manual alignments"
        assert stacker.train_dataset_dropdown.enabled is False

    def test_no_datasets_at_all_keeps_the_original_message(self, monkeypatch, stacker):
        monkeypatch.setattr(training_stacker.datasets, "list_datasets_metadata", lambda: [])
        monkeypatch.setattr(training_stacker.alignments, "has_manual_alignments", lambda _: False)

        stacker._populate_dataset_dropdown()

        assert stacker.train_dataset_dropdown.placeholder == "No datasets registered"
        assert stacker.train_dataset_dropdown.enabled is False


class TestAlignmentDropdownFilter:
    def test_populates_from_manual_alignments_only(self, monkeypatch, stacker):
        """The stacker must call list_manual_alignments, not filter list_alignments
        itself -- the predicate lives in storage so it stays testable and shared."""
        captured = {}

        def _list_manual(dataset_id):
            captured["dataset_id"] = dataset_id
            return [_alignment("al2", "hand"), _alignment("al4", "corrected-v2")]

        monkeypatch.setattr(training_stacker.alignments, "list_manual_alignments", _list_manual)

        stacker.on_dataset_selected()

        assert captured["dataset_id"] == "ds1"
        assert stacker.train_alignment_dropdown.ids() == ["al2", "al4"]
        assert stacker.train_alignment_dropdown.enabled is True

    def test_empty_state_names_the_actual_requirement(self, monkeypatch, stacker):
        """A dataset can have plenty of automatic alignments and still land here, so
        "No alignments registered" would be actively wrong."""
        monkeypatch.setattr(training_stacker.alignments, "list_manual_alignments", lambda _: [])

        stacker.on_dataset_selected()

        assert (
            stacker.train_alignment_dropdown.placeholder == "No manual alignments for this dataset"
        )
        assert stacker.train_alignment_dropdown.enabled is False


class TestNoticeCopy:
    def test_notice_explains_both_the_why_and_the_filtering(self):
        """Users see an unexpectedly short dataset list; the notice is the only
        thing on screen that accounts for it."""
        assert "only meaningful on datasets with manual alignments" in MANUAL_ALIGNMENT_NOTICE
        assert "will appear in the list below" in MANUAL_ALIGNMENT_NOTICE
