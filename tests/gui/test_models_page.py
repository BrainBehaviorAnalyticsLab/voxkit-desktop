"""Tests for ManageAlignersWidget in models_page."""

from unittest.mock import MagicMock, call, patch


class TestReloadModels:
    """reload_models must refresh every engine, not just W2TGENGINE."""

    def _make_widget(self, engines):
        """Return a minimal ManageAlignersWidget stand-in with the given engines."""
        widget = MagicMock()
        widget.get_engines.return_value = engines
        return widget

    def test_calls_set_items_for_every_engine(self):
        engines = ["W2TGENGINE", "MFAENGINE", "CUSTOMENGINE"]
        widget = self._make_widget(engines)

        model_data = {
            "W2TGENGINE": [{"id": "w1", "name": "w2tg_model"}],
            "MFAENGINE": [{"id": "m1", "name": "mfa_model"}],
            "CUSTOMENGINE": [],
        }

        with patch(
            "voxkit.gui.pages.models.models_page.models.list_models",
            side_effect=lambda e: model_data[e],
        ):
            from voxkit.gui.pages.models.models_page import ManageAlignersWidget

            ManageAlignersWidget.reload_models(widget)

        widget.set_items.assert_has_calls(
            [
                call("W2TGENGINE", model_data["W2TGENGINE"]),
                call("MFAENGINE", model_data["MFAENGINE"]),
                call("CUSTOMENGINE", model_data["CUSTOMENGINE"]),
            ],
            any_order=False,
        )
        assert widget.set_items.call_count == len(engines)

    def test_no_set_items_calls_when_no_engines(self):
        widget = self._make_widget([])

        with patch("voxkit.gui.pages.models.models_page.models.list_models"):
            from voxkit.gui.pages.models.models_page import ManageAlignersWidget

            ManageAlignersWidget.reload_models(widget)

        widget.set_items.assert_not_called()

    def test_single_engine_still_calls_set_items(self):
        widget = self._make_widget(["W2TGENGINE"])
        model_list = [{"id": "w1", "name": "w2tg_model"}]

        with patch(
            "voxkit.gui.pages.models.models_page.models.list_models",
            return_value=model_list,
        ):
            from voxkit.gui.pages.models.models_page import ManageAlignersWidget

            ManageAlignersWidget.reload_models(widget)

        widget.set_items.assert_called_once_with("W2TGENGINE", model_list)
