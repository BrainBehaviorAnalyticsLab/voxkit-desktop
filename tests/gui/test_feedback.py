from types import SimpleNamespace

from voxkit.gui import (
    FEEDBACK_BODY_TEMPLATE,
    FEEDBACK_SUBJECT,
    VoxKitGUI,
    build_feedback_mailto_url,
)


class TestFeedback:
    def test_build_feedback_mailto_url(self):
        result = build_feedback_mailto_url("feedback@example.com")

        assert result.startswith("mailto:feedback@example.com?")
        assert "subject=VoxKit%20Feedback" in result
        assert "Please%20share%20your%20feedback%20below." in result

    def test_open_feedback_opens_mailto_url(self, monkeypatch):
        gui = VoxKitGUI.__new__(VoxKitGUI)
        gui.app_config = SimpleNamespace(feedback_email="feedback@example.com")
        opened_urls = []
        monkeypatch.setattr("voxkit.gui.webbrowser.open", opened_urls.append)

        gui.open_feedback()

        assert opened_urls == [
            build_feedback_mailto_url(
                "feedback@example.com",
                subject=FEEDBACK_SUBJECT,
                body=FEEDBACK_BODY_TEMPLATE,
            )
        ]

    def test_open_feedback_no_email_noop(self, monkeypatch):
        gui = VoxKitGUI.__new__(VoxKitGUI)
        gui.app_config = SimpleNamespace(feedback_email=None)
        opened_urls = []
        monkeypatch.setattr("voxkit.gui.webbrowser.open", opened_urls.append)

        gui.open_feedback()

        assert opened_urls == []
