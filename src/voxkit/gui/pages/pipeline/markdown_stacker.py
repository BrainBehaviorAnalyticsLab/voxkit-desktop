"""Markdown Stacker Module.

Pipeline stacker for displaying markdown-formatted text content.

API
---
- **MarkdownStacker**: Stacker widget that renders markdown text
"""

from PyQt6.QtWidgets import QSizePolicy, QTextBrowser

from voxkit.gui.styles import Containers

from .base_stacker import BaseStacker


class MarkdownStacker(BaseStacker):
    """A stacker widget that displays markdown content."""

    def __init__(self, parent=None, markdown_content: str = ""):
        """Initialize the markdown stacker.

        Args:
            parent: Parent widget
            markdown_content: Markdown text to display
        """
        self.markdown_content = markdown_content
        self.text_browser = None
        super().__init__(parent)

        # Remove the stretch at the end added by BaseStacker to allow
        # the text browser to expand and fill all available vertical space
        if self.main_layout.count() > 0:
            last_item = self.main_layout.itemAt(self.main_layout.count() - 1)
            if last_item and last_item.spacerItem():
                self.main_layout.removeItem(last_item)

    def build_ui(self):
        """Build the markdown display UI."""
        # Create text browser for markdown rendering
        self.text_browser = QTextBrowser()
        self.text_browser.setObjectName("markdownDisplay")
        self.text_browser.setOpenExternalLinks(True)  # Allow clickable links
        self.text_browser.setStyleSheet(Containers.MARKDOWN_DISPLAY)

        # Set size policy to expand and fill available space
        self.text_browser.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        # Set markdown content
        self.set_markdown(self.markdown_content)

        # Add with stretch factor to fill available vertical space
        self.content_layout.addWidget(self.text_browser, stretch=1)

    def has_status_label(self) -> bool:
        """Markdown display doesn't need a status label."""
        return False

    def set_markdown(self, markdown_text: str):
        """Set the markdown content to display.

        Args:
            markdown_text: Markdown formatted text
        """
        self.markdown_content = markdown_text
        if self.text_browser:
            self.text_browser.setMarkdown(markdown_text)

    def get_markdown(self) -> str:
        """Get the current markdown content.

        Returns:
            Current markdown text
        """
        return self.markdown_content
