"""Tests for CSV Viewer Dialog component."""

import csv

import pytest

from voxkit.gui.components.csv_viewer_dialog import CSVViewerDialog


@pytest.fixture
def sample_csv(tmp_path):
    """Create a sample CSV file for testing.

    Args:
        tmp_path: pytest temporary directory fixture

    Returns:
        Path to the created CSV file
    """
    csv_path = tmp_path / "test_summary.csv"
    data = [
        {"speaker_id": "speaker_001", "audio_file_count": "10"},
        {"speaker_id": "speaker_002", "audio_file_count": "15"},
        {"speaker_id": "speaker_003", "audio_file_count": "8"},
    ]

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["speaker_id", "audio_file_count"])
        writer.writeheader()
        writer.writerows(data)

    return str(csv_path)


def test_csv_viewer_dialog_creation(qtbot, sample_csv):
    """Test that CSVViewerDialog can be created and displayed.

    Args:
        qtbot: pytest-qt bot fixture
        sample_csv: Path to sample CSV file
    """
    dialog = CSVViewerDialog(sample_csv)
    qtbot.addWidget(dialog)

    assert dialog.windowTitle() == "Dataset Analysis Details"
    assert dialog.csv_path == sample_csv


def test_csv_viewer_dialog_loads_data(qtbot, sample_csv):
    """Test that CSVViewerDialog loads and displays CSV data correctly.

    Args:
        qtbot: pytest-qt bot fixture
        sample_csv: Path to sample CSV file
    """
    dialog = CSVViewerDialog(sample_csv)
    qtbot.addWidget(dialog)

    # Check table dimensions
    assert dialog.table.rowCount() == 3
    assert dialog.table.columnCount() == 2

    # Check headers
    assert dialog.table.horizontalHeaderItem(0).text() == "speaker_id"
    assert dialog.table.horizontalHeaderItem(1).text() == "audio_file_count"

    # Check data
    assert dialog.table.item(0, 0).text() == "speaker_001"
    assert dialog.table.item(0, 1).text() == "10"
    assert dialog.table.item(1, 0).text() == "speaker_002"
    assert dialog.table.item(1, 1).text() == "15"

    # Check stats label
    assert "3 rows × 2 columns" in dialog.stats_label.text()


def test_csv_viewer_dialog_file_not_found(qtbot):
    """Test CSVViewerDialog with non-existent file.

    Args:
        qtbot: pytest-qt bot fixture
    """
    dialog = CSVViewerDialog("/nonexistent/file.csv")
    qtbot.addWidget(dialog)

    # Should show error in stats label
    assert "not found" in dialog.stats_label.text().lower()


def test_csv_viewer_dialog_empty_csv(qtbot, tmp_path):
    """Test CSVViewerDialog with empty CSV file.

    Args:
        qtbot: pytest-qt bot fixture
        tmp_path: pytest temporary directory fixture
    """
    csv_path = tmp_path / "empty.csv"
    csv_path.write_text("", encoding="utf-8")

    dialog = CSVViewerDialog(str(csv_path))
    qtbot.addWidget(dialog)

    # Should show error in stats label
    assert "empty" in dialog.stats_label.text().lower()
