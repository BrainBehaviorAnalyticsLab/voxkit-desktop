from voxkit.gui.components.loading_dialog import LoadingDialog, _WaveformStrip


class TestLoadingDialog:
    def test_default_message(self, qtbot):
        dialog = LoadingDialog()
        qtbot.addWidget(dialog)

        assert dialog.message_label.text() == "Loading..."

    def test_custom_message(self, qtbot):
        dialog = LoadingDialog(message="Please wait...")
        qtbot.addWidget(dialog)

        assert dialog.message_label.text() == "Please wait..."

    def test_update_message(self, qtbot):
        dialog = LoadingDialog(message="Step 1")
        qtbot.addWidget(dialog)

        dialog.update_message("Step 2")

        assert dialog.message_label.text() == "Step 2"

    def test_default_title_is_voxkit(self, qtbot):
        dialog = LoadingDialog()
        qtbot.addWidget(dialog)

        # The VoxKit brand name must appear so users know what launched.
        assert dialog._brand_title_label.text() == "VoxKit"

    def test_subtitle_hidden_by_default(self, qtbot):
        dialog = LoadingDialog(message="Loading...")
        qtbot.addWidget(dialog)

        assert dialog.subtitle_label.text() == ""
        assert dialog.subtitle_label.isVisible() is False

    def test_subtitle_shown_when_provided(self, qtbot):
        dialog = LoadingDialog(message="Loading...", subtitle="Almost there")
        qtbot.addWidget(dialog)

        assert dialog.subtitle_label.text() == "Almost there"

    def test_update_subtitle(self, qtbot):
        dialog = LoadingDialog(message="Loading...", subtitle="Downloading")
        qtbot.addWidget(dialog)

        dialog.update_subtitle("")
        assert dialog.subtitle_label.text() == ""

        dialog.update_subtitle("Finishing up")
        assert dialog.subtitle_label.text() == "Finishing up"

    def test_has_waveform(self, qtbot):
        dialog = LoadingDialog()
        qtbot.addWidget(dialog)

        assert isinstance(dialog.waveform, _WaveformStrip)

    def test_waveform_advances_phase(self, qtbot):
        dialog = LoadingDialog()
        qtbot.addWidget(dialog)

        before = dialog.waveform._phase
        dialog.waveform.advance()
        assert dialog.waveform._phase > before

    def test_is_modal(self, qtbot):
        dialog = LoadingDialog()
        qtbot.addWidget(dialog)
        assert dialog.isModal() is True

    def test_fixed_size(self, qtbot):
        dialog = LoadingDialog()
        qtbot.addWidget(dialog)
        assert dialog.width() == 420
        assert dialog.height() == 290

    def test_close_gracefully_stops_timer(self, qtbot):
        dialog = LoadingDialog()
        qtbot.addWidget(dialog)

        assert dialog.wave_timer.isActive()
        dialog.close_gracefully()
        assert dialog.wave_timer.isActive() is False
