from PyQt6.QtCore import Qt

from voxkit.gui.components.column_dropdown import MultiColumnComboBox

SAMPLE_DATA = [
    {"id": 1, "data": ("Alice", "30", "New York")},
    {"id": 2, "data": ("Bob", "25", "Los Angeles")},
    {"id": 3, "data": ("Charlie", "35", "Chicago")},
]
HEADERS = ["Name", "Age", "City"]


class TestMultiColumnComboBox:
    def test_set_data_populates_rows(self, qtbot):
        combo = MultiColumnComboBox()
        qtbot.addWidget(combo)
        combo.set_data(SAMPLE_DATA, headers=HEADERS)

        model = combo.model()
        assert model.rowCount() == 3
        assert model.columnCount() == 3

    def test_headers_are_set(self, qtbot):
        combo = MultiColumnComboBox()
        qtbot.addWidget(combo)
        combo.set_data(SAMPLE_DATA, headers=HEADERS)

        model = combo.model()
        for i, header in enumerate(HEADERS):
            assert model.headerData(i, Qt.Orientation.Horizontal) == header

    def test_current_id_after_selection(self, qtbot):
        combo = MultiColumnComboBox()
        qtbot.addWidget(combo)
        combo.set_data(SAMPLE_DATA, headers=HEADERS)

        combo.setCurrentIndex(1)
        assert combo.current_id() == 2

    def test_current_id_no_selection(self, qtbot):
        combo = MultiColumnComboBox()
        qtbot.addWidget(combo)
        combo.set_data(SAMPLE_DATA, headers=HEADERS, placeholder="Select...")

        # placeholder sets index to -1
        assert combo.current_id() is None

    def test_placeholder_text(self, qtbot):
        combo = MultiColumnComboBox()
        qtbot.addWidget(combo)
        combo.set_data(SAMPLE_DATA, headers=HEADERS, placeholder="Pick one")

        assert combo.currentIndex() == -1
        assert combo.placeholderText() == "Pick one"

    def test_cell_data_matches_input(self, qtbot):
        combo = MultiColumnComboBox()
        qtbot.addWidget(combo)
        combo.set_data(SAMPLE_DATA, headers=HEADERS)

        model = combo.model()
        assert model.item(0, 0).text() == "Alice"
        assert model.item(1, 2).text() == "Los Angeles"
        assert model.item(2, 1).text() == "35"

    def test_row_id_stored_in_user_role(self, qtbot):
        combo = MultiColumnComboBox()
        qtbot.addWidget(combo)
        combo.set_data(SAMPLE_DATA, headers=HEADERS)

        model = combo.model()
        for row_idx, row in enumerate(SAMPLE_DATA):
            index = model.index(row_idx, 0)
            assert model.data(index, Qt.ItemDataRole.UserRole) == row["id"]
