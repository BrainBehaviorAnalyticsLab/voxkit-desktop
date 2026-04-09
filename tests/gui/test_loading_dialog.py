from PyQt6.QtWidgets import QLabel

from voxkit.gui.components.loading_dialog import LoadingDialog


class TestLoadingDialog:
    def test_default_message(self, qtbot):
        dialog = LoadingDialog()
        qtbot.addWidget(dialog)

        layout = dialog.layout()
        assert layout is not None
        item = layout.itemAt(0)
        assert item is not None
        label = item.widget()
        assert isinstance(label, QLabel)
        assert label.text() == "Loading..."

    def test_custom_message(self, qtbot):
        dialog = LoadingDialog(message="Please wait...")
        qtbot.addWidget(dialog)

        layout = dialog.layout()
        assert layout is not None
        item = layout.itemAt(0)
        assert item is not None
        label = item.widget()
        assert isinstance(label, QLabel)
        assert label.text() == "Please wait..."

    def test_update_message(self, qtbot):
        dialog = LoadingDialog(message="Step 1")
        qtbot.addWidget(dialog)

        dialog.update_message("Step 2")

        layout = dialog.layout()
        assert layout is not None
        item = layout.itemAt(0)
        assert item is not None
        label = item.widget()
        assert isinstance(label, QLabel)
        assert label.text() == "Step 2"

    def test_spinner_frames_cycle(self, qtbot):
        dialog = LoadingDialog()
        qtbot.addWidget(dialog)

        initial = dialog.progress_label.text()
        assert initial == dialog._spinner_frames[0]

        dialog._update_spinner()
        assert dialog.progress_label.text() == dialog._spinner_frames[1]

        dialog._update_spinner()
        assert dialog.progress_label.text() == dialog._spinner_frames[2]

    def test_spinner_wraps_around(self, qtbot):
        dialog = LoadingDialog()
        qtbot.addWidget(dialog)

        for _ in range(len(dialog._spinner_frames)):
            dialog._update_spinner()

        # Should be back to frame 0
        assert dialog.progress_label.text() == dialog._spinner_frames[0]

    def test_is_modal(self, qtbot):
        dialog = LoadingDialog()
        qtbot.addWidget(dialog)
        assert dialog.isModal() is True

    def test_fixed_size(self, qtbot):
        dialog = LoadingDialog()
        qtbot.addWidget(dialog)
        assert dialog.width() == 400
        assert dialog.height() == 250

    def test_close_gracefully_stops_timer(self, qtbot):
        dialog = LoadingDialog()
        qtbot.addWidget(dialog)

        assert dialog.spinner_timer.isActive()
        dialog.close_gracefully()
        assert dialog.spinner_timer.isActive() is False
