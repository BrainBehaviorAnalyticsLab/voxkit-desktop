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
