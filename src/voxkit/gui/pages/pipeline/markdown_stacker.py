"""Markdown display stacker for showing formatted text content.

This stacker displays markdown-formatted text, useful for instructions,
documentation, or any text-heavy content in the pipeline.
"""

from PyQt6.QtWidgets import QTextBrowser, QVBoxLayout, QWidget


class MarkdownStacker(QWidget):
    """A stacker widget that displays markdown content."""

    def __init__(self, parent=None, markdown_content: str = ""):
        """Initialize the markdown stacker.

        Args:
            parent: Parent widget
            markdown_content: Markdown text to display
        """
        super().__init__(parent)
        self.parent = parent
        self.markdown_content = markdown_content
        self.init_ui()

    def init_ui(self):
        """Initialize the UI with a text browser for markdown display."""
        layout = QVBoxLayout(self)
        # Match the application window margins (20px all around)
        layout.setContentsMargins(0, 0, 0, 0)

        # Create text browser for markdown rendering
        self.text_browser = QTextBrowser()
        self.text_browser.setObjectName("markdownDisplay")
        self.text_browser.setOpenExternalLinks(True)  # Allow clickable links
        self.text_browser.setStyleSheet("""
            QTextBrowser#markdownDisplay {
                background-color: white;
                border: 1px solid #E0E0E0;
                border-radius: 6px;
                padding: 20px;
                font-size: 14px;
                line-height: 1.6;
            }
        """)

        # Set markdown content
        self.set_markdown(self.markdown_content)

        layout.addWidget(self.text_browser)

    def set_markdown(self, markdown_text: str):
        """Set the markdown content to display.

        Args:
            markdown_text: Markdown formatted text
        """
        self.markdown_content = markdown_text
        self.text_browser.setMarkdown(markdown_text)

    def get_markdown(self) -> str:
        """Get the current markdown content.

        Returns:
            Current markdown text
        """
        return self.markdown_content
