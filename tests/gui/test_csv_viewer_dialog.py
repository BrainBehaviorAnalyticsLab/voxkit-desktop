from voxkit.gui.components.csv_viewer_dialog import CSVViewerDialog


class TestCSVViewerDialog:
    def test_loads_csv_data(self, qtbot, sample_csv):
        dialog = CSVViewerDialog(csv_path=sample_csv)
        qtbot.addWidget(dialog)

        assert dialog.table.rowCount() == 3
        assert dialog.table.columnCount() == 3

    def test_headers_match_csv(self, qtbot, sample_csv):
        dialog = CSVViewerDialog(csv_path=sample_csv)
        qtbot.addWidget(dialog)

        headers = []
        for i in range(dialog.table.columnCount()):
            item = dialog.table.horizontalHeaderItem(i)
            if item is not None:
                headers.append(item.text())
        assert headers == ["name", "age", "city"]

    def test_cell_content(self, qtbot, sample_csv):
        dialog = CSVViewerDialog(csv_path=sample_csv)
        qtbot.addWidget(dialog)

        item1 = dialog.table.item(0, 0)
        assert item1 is not None
        assert item1.text() == "Alice"
        item2 = dialog.table.item(1, 1)
        assert item2 is not None
        assert item2.text() == "25"
        item3 = dialog.table.item(2, 2)
        assert item3 is not None
        assert item3.text() == "Chicago"

    def test_stats_label_shows_dimensions(self, qtbot, sample_csv):
        dialog = CSVViewerDialog(csv_path=sample_csv)
        qtbot.addWidget(dialog)

        assert "3 rows" in dialog.stats_label.text()
        assert "3 columns" in dialog.stats_label.text()

    def test_missing_csv_shows_error(self, qtbot, missing_csv):
        dialog = CSVViewerDialog(csv_path=missing_csv)
        qtbot.addWidget(dialog)

        assert "not found" in dialog.stats_label.text()

    def test_empty_csv_shows_error(self, qtbot, empty_csv):
        dialog = CSVViewerDialog(csv_path=empty_csv)
        qtbot.addWidget(dialog)

        assert "empty" in dialog.stats_label.text()

    def test_cells_are_read_only(self, qtbot, sample_csv):
        from PyQt6.QtCore import Qt

        dialog = CSVViewerDialog(csv_path=sample_csv)
        qtbot.addWidget(dialog)

        item = dialog.table.item(0, 0)
        assert item is not None
        assert not (item.flags() & Qt.ItemFlag.ItemIsEditable)

    def test_window_title(self, qtbot, sample_csv):
        dialog = CSVViewerDialog(csv_path=sample_csv)
        qtbot.addWidget(dialog)

        assert dialog.windowTitle() == "Dataset Analysis Details"
