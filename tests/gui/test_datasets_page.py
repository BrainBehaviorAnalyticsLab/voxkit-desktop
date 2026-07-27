from unittest.mock import patch

import pytest

from voxkit.gui.pages.datasets.datasets_page import DatasetsPage


@pytest.fixture
def datasets_page(qtbot):
    """DatasetsPage instance with no real datasets loaded."""
    with patch(
        "voxkit.gui.pages.datasets.datasets_page.datasets.list_datasets_metadata", return_value=[]
    ):
        page = DatasetsPage()
        qtbot.addWidget(page)
        return page


class TestRefreshDatasets:
    def test_empty_state_shows_label_and_hides_table(self, qtbot, datasets_page):
        with patch(
            "voxkit.gui.pages.datasets.datasets_page.datasets.list_datasets_metadata",
            return_value=[],
        ):
            datasets_page.refresh_datasets()

        assert not datasets_page.empty_label.isHidden()
        assert datasets_page.dataset_table.isHidden()

    def test_populated_state_shows_table_and_hides_label(self, qtbot, datasets_page):
        sample_metadata = [
            {
                "id": "ds-1",
                "name": "Test Dataset",
                "description": "A test dataset",
                "cached": False,
                "anonymize": False,
                "transcribed": False,
                "registration_date": "2024-01-01T00:00:00",
            }
        ]
        with patch(
            "voxkit.gui.pages.datasets.datasets_page.datasets.list_datasets_metadata",
            return_value=sample_metadata,
        ):
            datasets_page.refresh_datasets()

        assert datasets_page.empty_label.isHidden()
        assert not datasets_page.dataset_table.isHidden()
        assert datasets_page.dataset_table.rowCount() == 1

    def test_location_column_shows_original_path(self, qtbot, datasets_page):
        sample_metadata = [
            {
                "id": "ds-1",
                "name": "Test Dataset",
                "description": "A test dataset",
                "original_path": r"C:\corpora\timit_train",
                "cached": True,
                "anonymize": False,
                "transcribed": False,
                "registration_date": "2024-01-01T00:00:00",
            }
        ]
        with patch(
            "voxkit.gui.pages.datasets.datasets_page.datasets.list_datasets_metadata",
            return_value=sample_metadata,
        ):
            datasets_page.refresh_datasets()

        location_item = datasets_page.dataset_table.item(0, 2)
        assert location_item.text() == r"C:\corpora\timit_train"
        assert location_item.toolTip() == r"C:\corpora\timit_train"

    def test_location_column_falls_back_when_missing(self, qtbot, datasets_page):
        sample_metadata = [
            {
                "id": "ds-1",
                "name": "Test Dataset",
                "description": "A test dataset",
                "cached": False,
                "anonymize": False,
                "transcribed": False,
                "registration_date": "2024-01-01T00:00:00",
            }
        ]
        with patch(
            "voxkit.gui.pages.datasets.datasets_page.datasets.list_datasets_metadata",
            return_value=sample_metadata,
        ):
            datasets_page.refresh_datasets()

        assert datasets_page.dataset_table.item(0, 2).text() == "Unknown"


class TestDisplayAlignments:
    def test_location_column_shows_tg_path(self, qtbot, datasets_page):
        sample_alignment = {
            "id": "align-1",
            "engine_id": "mfa",
            "model_metadata": {"id": "model-1", "name": "Test Model"},
            "alignment_date": "2024-01-01T00:00:00",
            "status": "completed",
            "tg_path": r"C:\voxkit_storage\datasets\ds-1\alignments\align-1\textgrids",
        }

        datasets_page._display_alignments([sample_alignment])

        location_item = datasets_page.alignments_table.item(0, 3)
        assert location_item.text() == sample_alignment["tg_path"]
        assert location_item.toolTip() == sample_alignment["tg_path"]

    def test_location_column_falls_back_when_missing(self, qtbot, datasets_page):
        sample_alignment = {
            "id": "align-1",
            "engine_id": "mfa",
            "model_metadata": {"id": "model-1", "name": "Test Model"},
            "alignment_date": "2024-01-01T00:00:00",
            "status": "completed",
        }

        datasets_page._display_alignments([sample_alignment])

        assert datasets_page.alignments_table.item(0, 3).text() == "Unknown"

    def test_type_column_shows_corrected_for_corrected_alignment(self, qtbot, datasets_page):
        sample_alignment = {
            "id": "align-2",
            "engine_id": "MFAENGINE",
            "model_metadata": {"id": "model-1", "name": "Test Model"},
            "alignment_date": "2024-01-01T00:00:00",
            "status": "completed",
            "tg_path": r"C:\voxkit_storage\datasets\ds-1\alignments\align-2\textgrids",
            "source_alignment_id": "align-1",
            "alignment_type": "corrected",
        }

        datasets_page._display_alignments([sample_alignment])

        assert datasets_page.alignments_table.item(0, 2).text() == "corrected"

    def test_type_column_defaults_to_automatic_for_legacy_alignment(self, qtbot, datasets_page):
        """Alignments predating the alignment_type field should read as "automatic"."""
        sample_alignment = {
            "id": "align-1",
            "engine_id": "MFAENGINE",
            "model_metadata": {"id": "model-1", "name": "Test Model"},
            "alignment_date": "2024-01-01T00:00:00",
            "status": "completed",
            "tg_path": r"C:\voxkit_storage\datasets\ds-1\alignments\align-1\textgrids",
        }

        datasets_page._display_alignments([sample_alignment])

        assert datasets_page.alignments_table.item(0, 2).text() == "automatic"

    def test_type_column_shows_hand_for_hand_alignment_sentinel(self, qtbot, datasets_page):
        sample_alignment = {
            "id": "hand",
            "engine_id": "hand",
            "model_metadata": {"id": "hand", "name": "hand"},
            "alignment_date": "2024-01-01T00:00:00",
            "status": "completed",
            "tg_path": r"C:\voxkit_storage\datasets\ds-1\alignments\hand\textgrids",
        }

        datasets_page._display_alignments([sample_alignment])

        assert datasets_page.alignments_table.item(0, 2).text() == "hand"
