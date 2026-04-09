from typing import cast

from PyQt6.QtCore import Qt
from PyQt6.QtTest import QTest

from voxkit.gui.components.toggle_switch import ToggleSwitch


class TestToggleSwitch:
    def test_default_unchecked(self, qtbot):
        switch = ToggleSwitch()
        qtbot.addWidget(switch)
        assert switch.isChecked() is False

    def test_initial_checked(self, qtbot):
        switch = ToggleSwitch(checked=True)
        qtbot.addWidget(switch)
        assert switch.isChecked() is True

    def test_click_toggles_state(self, qtbot):
        switch = ToggleSwitch(checked=False)
        qtbot.addWidget(switch)
        switch.show()

        from PyQt6.QtWidgets import QWidget as QWidgetType

        QTest.mouseClick(cast(QWidgetType, switch), Qt.MouseButton.LeftButton)
        assert switch.isChecked() is True

        QTest.mouseClick(cast(QWidgetType, switch), Qt.MouseButton.LeftButton)
        assert switch.isChecked() is False

    def test_set_checked_programmatically(self, qtbot):
        switch = ToggleSwitch(checked=False)
        qtbot.addWidget(switch)

        switch.setChecked(True)
        assert switch.isChecked() is True

        switch.setChecked(False)
        assert switch.isChecked() is False

    def test_thumb_position_matches_state(self, qtbot):
        switch = ToggleSwitch(checked=False)
        qtbot.addWidget(switch)
        assert switch.thumb_pos == 0

        switch.setChecked(True)
        expected = switch.width() - switch.height()
        assert switch.thumb_pos == expected

    def test_fixed_size(self, qtbot):
        switch = ToggleSwitch()
        qtbot.addWidget(switch)
        assert switch.width() == 40
        assert switch.height() == 22
