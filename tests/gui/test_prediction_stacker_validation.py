"""Tests for pre-flight validation in PredictionStacker.on_predict_alignments.

These guard against passing an unselected dataset/engine/model to the engine,
which otherwise surfaces as a raw "Model 'None' for engine ... not found" error.
"""

from types import SimpleNamespace

import pytest

from voxkit.gui.pages.pipeline import prediction_stacker
from voxkit.gui.pages.pipeline.prediction_stacker import PredictionStacker


class _WarningRecorder:
    def __init__(self):
        self.calls = []

    def __call__(self, parent, title, text, *args, **kwargs):
        self.calls.append((title, text))


@pytest.fixture
def recorder(monkeypatch):
    rec = _WarningRecorder()
    monkeypatch.setattr(prediction_stacker.QMessageBox, "warning", rec)
    return rec


def _make_stacker(dataset_id, engine, model_id):
    """Build a PredictionStacker with just the attributes the handler reads."""
    stacker = PredictionStacker.__new__(PredictionStacker)
    stacker.predict_dataset_dropdown = SimpleNamespace(current_id=lambda: dataset_id)
    stacker.model_panel = SimpleNamespace(
        get_selected_engine=lambda: engine,
        get_selected_model_id=lambda: model_id,
    )
    stacker.engines = SimpleNamespace(
        get_engine=lambda eid: SimpleNamespace(name=lambda: "Montreal Forced Aligner")
    )
    # If a guard is missed, starting a worker would explode here, failing the test.
    stacker.worker = None
    return stacker


class TestPredictAlignmentsValidation:
    def test_no_dataset_shows_warning(self, qtbot, recorder):
        stacker = _make_stacker(dataset_id=None, engine="MFAENGINE", model_id="english")
        stacker.on_predict_alignments()

        assert recorder.calls == [
            ("No Dataset Selected", "Please select a dataset from the dropdown.")
        ]
        assert stacker.worker is None

    def test_no_engine_shows_warning(self, qtbot, recorder):
        stacker = _make_stacker(dataset_id="ds1", engine=None, model_id="english")
        stacker.on_predict_alignments()

        assert recorder.calls[0][0] == "No Engine Selected"
        assert stacker.worker is None

    def test_no_model_shows_actionable_warning(self, qtbot, recorder):
        stacker = _make_stacker(dataset_id="ds1", engine="MFAENGINE", model_id=None)
        stacker.on_predict_alignments()

        assert len(recorder.calls) == 1
        title, text = recorder.calls[0]
        assert title == "No Model Selected"
        # Actionable: names the engine and points to where to get a model.
        assert "Montreal Forced Aligner" in text
        assert "Models page" in text
        assert stacker.worker is None
