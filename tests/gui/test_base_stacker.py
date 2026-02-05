import pytest

from voxkit.gui.pages.pipeline.base_stacker import BaseStacker


class ConcreteStacker(BaseStacker):
    """Minimal concrete implementation for testing the base class."""

    def build_ui(self):
        pass

    def get_title(self):
        return "Test Stacker"


class NoTitleStacker(BaseStacker):
    """Stacker with no title to test the no-header path."""

    def build_ui(self):
        pass


class SettingsStacker(BaseStacker):
    """Stacker that reports having a settings button."""

    def __init__(self, parent=None):
        self.settings_clicked = False
        super().__init__(parent)

    def build_ui(self):
        pass

    def get_title(self):
        return "With Settings"

    def has_settings(self):
        return True

    def on_settings(self):
        self.settings_clicked = True


class TestBaseStacker:
    def test_status_label_created(self, qtbot):
        stacker = ConcreteStacker()
        qtbot.addWidget(stacker)

        assert stacker.status_label is not None
        assert stacker.status_label.text() == "Ready"

    def test_set_status_updates_text(self, qtbot):
        stacker = ConcreteStacker()
        qtbot.addWidget(stacker)

        stacker.set_status("Processing...", "working")
        assert stacker.status_label.text() == "Processing..."

    def test_set_status_all_types(self, qtbot):
        stacker = ConcreteStacker()
        qtbot.addWidget(stacker)

        for status_type in ("ready", "working", "success", "error"):
            stacker.set_status(f"Status: {status_type}", status_type)
            assert stacker.status_label.text() == f"Status: {status_type}"

    def test_set_status_unknown_type_uses_ready(self, qtbot):
        stacker = ConcreteStacker()
        qtbot.addWidget(stacker)

        stacker.set_status("Unknown", "nonexistent_type")
        assert stacker.status_label.text() == "Unknown"

    def test_no_title_skips_header(self, qtbot):
        stacker = NoTitleStacker()
        qtbot.addWidget(stacker)

        # Should still have status label but no header
        assert stacker.status_label is not None

    def test_minimum_width(self, qtbot):
        stacker = ConcreteStacker()
        qtbot.addWidget(stacker)

        assert stacker.minimumWidth() == 600

    def test_build_ui_not_implemented_raises(self, qtbot):
        with pytest.raises(NotImplementedError):
            BaseStacker()

    def test_reload_calls_both(self, qtbot):
        stacker = ConcreteStacker()
        qtbot.addWidget(stacker)

        # Default reload_models and reload_datasets are no-ops;
        # just verify reload() doesn't raise
        stacker.reload()

    def test_content_layout_exists(self, qtbot):
        stacker = ConcreteStacker()
        qtbot.addWidget(stacker)

        assert stacker.content_layout is not None
        assert stacker.main_layout is not None
