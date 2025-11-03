"""
VoxLab Forum by BrainBehaviorAnalyticsLab
Discussion forum stack widget with configurable categories and interactive threads.
Now using the reusable HorizontalButtonSelector module.
"""

from PyQt6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton,
                             QScrollArea, QFrame)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from config import Dimensions
from ui.widgets.horizontal_button_selector import HorizontalButtonSelector


# =============================================================================
#  DISCUSSION THREAD CARD
# =============================================================================
class DiscussionThread(QFrame):
    """Individual discussion thread displayed as a clickable card"""
    
    clicked = pyqtSignal(dict)

    def __init__(self, title, content, timestamp, parent=None):
        super().__init__(parent)
        self.thread_data = {'title': title, 'content': content, 'timestamp': timestamp}
        self.init_ui()
        self.setObjectName("discussionThread")
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 15, 20, 15)
        layout.setSpacing(8)

        self.setStyleSheet("""
            DiscussionThread {
                background-color: white;
                border: 1px solid #ddd;
                border-radius: 5px;
                margin-bottom: 10px;
            }
            DiscussionThread:hover {
                background-color: #f9f9f9;
                border-color: #ccc;
            }
        """)

        # Title
        title_label = QLabel(self.thread_data['title'])
        title_font = QFont()
        title_font.setPointSize(14)
        # title_font.setBold(True)
        title_label.setFont(title_font)
        layout.addWidget(title_label)

        # Content preview
        content_label = QLabel(self.thread_data['content'])
        content_label.setWordWrap(True)
        content_label.setStyleSheet("color: #555;")
        layout.addWidget(content_label)

        # Timestamp
        time_label = QLabel(self.thread_data['timestamp'])
        time_label.setStyleSheet("color: #888; font-size: 12px;")
        layout.addWidget(time_label)
        

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.thread_data)
        super().mousePressEvent(event)


# =============================================================================
#  MAIN DISCUSSIONS STACK
# =============================================================================
class DiscussionsStack(QWidget):
    """
    Discussion forum with horizontal category selector and thread list.
    
    Signals:
        thread_clicked(dict): Emitted when a discussion thread is clicked
        new_discussion_clicked(str): Emitted when New Discussion button clicked (with category)
    """
    
    thread_clicked = pyqtSignal(dict)
    new_discussion_clicked = pyqtSignal(str)

    def __init__(self, categories=None, discussions=None, parent=None):
        super().__init__(parent)
        self.parent_window = parent

        self.categories = categories or [
            "Papers",
            "General", "Issues",
            "Features", "Bugs"
        ]

        self.discussions = discussions or self._create_default_discussions()
        self.init_ui()

    def _create_default_discussions(self):
        """Create default example discussions for each category"""
        return {
            "Papers": [
                {
                    'title': 'New Advances in Speech Alignment',
                    'content': 'Discussing the latest research on speech alignment techniques.',
                    'timestamp': '2 days ago'
                },
                {
                    'title': 'Neural Networks for Phoneme Recognition',
                    'content': 'Exploring deep learning models for phoneme recognition tasks.',
                    'timestamp': '4 days ago'
                },
                {
                    'title': 'Survey of Forced Alignment Tools',
                    'content': 'A comprehensive review of current forced alignment software.',
                    'timestamp': '1 week ago'
                },
            ],
            "General": [
                {
                    'title': 'Welcome to VoxKit Forum!',
                    'content': 'Discuss speech, AI, and neuroscience.',
                    'timestamp': '5 days ago'
                },
                {
                    'title': 'VoxKit v1.0 Released',
                    'content': 'Check out the new features in version 1.0.?',
                    'timestamp': '1 day ago'
                },
                {
                    'title': 'How to get started with VoxKit?',
                    'content': 'Check out the documentation and tutorials.',
                    'timestamp': '3 days ago'
                },
                {
                    'title': 'Community Guidelines',
                    'content': 'Please read our forum rules and guidelines.',
                    'timestamp': '1 week ago'
                }
            ],
            "Issues": [
                {
                    'title': 'Training stuck at 90%',
                    'content': 'Model stops improving after epoch 50.',
                    'timestamp': '2 hours ago'
                },
                {
                    'title': 'GPU OOM on large datasets',
                    'content': 'Any batch size tips?',
                    'timestamp': '1 day ago'
                },
                {
                    'title': 'Alignment offsets in output TextGrids',
                    'content': 'Phoneme timings seem shifted by 0.2s.',
                    'timestamp': 'Yesterday'
                }
            ],
            "Features": [
                {
                    'title': 'Request: Support for new audio formats',
                    'content': 'Please add FLAC and OGG support.',
                    'timestamp': '3 days ago'
                },
                {
                    'title': 'Feature idea: More granular alignment options',
                    'content': 'Allow custom phoneme sets during training.',
                    'timestamp': '4 days ago'
                },
                {
                    'title': 'Suggestion: Real-time alignment feedback',
                    'content': 'Would be great to see live alignment progress.',
                    'timestamp': '1 week ago'
                },
                {
                    'title': 'Enhancement: Improved UI for managing models',
                    'content': 'Make it easier to switch between different alignment models.',
                    'timestamp': '2 weeks ago'
                },
                {
                    'title': 'Add multi-language support',
                    'content': 'Support for languages other than English would be beneficial.',
                    'timestamp': '3 weeks ago'
                }
            ],

        }

    def init_ui(self):
        """Initialize the user interface"""
        from PyQt6.QtCore import QTimer
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(0, 0, 0, 0)

        # === Horizontal Category Selector ===
        self.category_selector = HorizontalButtonSelector()
        
        # Configure with categories (no callbacks, we'll use the signal)
        button_config = [(cat, None) for cat in self.categories]
        self.category_selector.configure(button_config)
        
        # Connect to selection change
        self.category_selector.selection_changed.connect(self._on_category_changed)
        
        layout.addWidget(self.category_selector)

        # === Main Content ===
        content_container = QWidget()
        content_layout = QVBoxLayout(content_container)
        content_layout.setContentsMargins(20, 0, 20, 0)
        content_layout.setSpacing(20)

        # Header
        # header = QLabel("Discussions")
        # header_font = QFont()
        # header_font.setPointSize(24)
        # header_font.setBold(True)
        # header.setFont(header_font)
        # content_layout.addWidget(header)

        # Scrollable Threads
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)

        self.threads_container = QWidget()
        self.threads_layout = QVBoxLayout(self.threads_container)
        self.threads_layout.setSpacing(0)
        self.threads_layout.setContentsMargins(0, 0, 0, 0)
        self.threads_layout.addStretch()

        scroll_area.setWidget(self.threads_container)
        content_layout.addWidget(scroll_area, stretch=1)

        # New Discussion Button
        self.new_discussion_btn = QPushButton("New Discussion")
        self.new_discussion_btn.setMinimumHeight(50)
        self.new_discussion_btn.setStyleSheet("""
            QPushButton {
                background-color: #0d8ac7;
                color: white;
                font-size: 16px;
                border: none;
                border-radius: 5px;
            }
            QPushButton:hover { background-color: #0b7ab0; }
            QPushButton:pressed { background-color: #096a99; }
        """)
        self.new_discussion_btn.clicked.connect(self._on_new_discussion_clicked)
        content_layout.addWidget(self.new_discussion_btn)

        layout.addWidget(content_container, stretch=1)

        # === Footer Credit ===
        credit = QLabel("VoxKit by BrainBehaviorAnalyticsLab")
        credit.setStyleSheet("color: #999; font-size: 10px; padding: 5px;")
        credit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(credit)

        QTimer.singleShot(100, lambda: self.category_selector._on_button_clicked("Issues")) # HERE WHY DOES IT NOT
        

    def _on_category_changed(self, button_name: str, index: int):
        """Handle category selection change from HorizontalButtonSelector"""
        print(f"Category changed to: {button_name}")
        self.load_discussions(button_name)

    def load_discussions(self, category: str):
        """Load and display discussions for a specific category"""
        # Clear existing threads (keep the stretch at the end)
        while self.threads_layout.count() > 1:
            item = self.threads_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Get threads for this category
        threads = self.discussions.get(category, [])
        
        if not threads:
            # Show empty state
            empty = QLabel(f"No discussions yet in <b>{category}</b>")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setStyleSheet("color: #999; font-size: 16px; padding: 40px;")
            self.threads_layout.insertWidget(0, empty)
        else:
            # Add discussion threads
            for data in threads:
                thread = DiscussionThread(data['title'], data['content'], data['timestamp'])
                thread.clicked.connect(self._on_thread_clicked)
                self.threads_layout.insertWidget(self.threads_layout.count() - 1, thread)

    def _on_thread_clicked(self, data: dict):
        """Handle click on a discussion thread"""
        self.thread_clicked.emit(data)

    def _on_new_discussion_clicked(self):
        """Handle click on New Discussion button"""
        cat = self.get_current_category()
        if cat:
            self.new_discussion_clicked.emit(cat)

    def add_discussion(self, category: str, title: str, content: str, timestamp: str = "Just now"):
        """
        Add a new discussion thread to a category.
        
        Args:
            category: Category name to add the discussion to
            title: Discussion title
            content: Discussion content/preview
            timestamp: When the discussion was posted
        """
        if category not in self.discussions:
            self.discussions[category] = []
        
        self.discussions[category].insert(0, {
            'title': title,
            'content': content,
            'timestamp': timestamp
        })
        
        # Refresh if this is the current category
        if self.get_current_category() == category:
            self.load_discussions(category)

    def set_categories(self, categories: list[str]):
        """
        Update the categories list.
        
        Args:
            categories: New list of category names
        """
        self.categories = categories
        
        # Reconfigure the button selector
        button_config = [(cat, None) for cat in categories]
        self.category_selector.configure(button_config)
        
        # Initialize discussions dict for new categories
        for cat in categories:
            self.discussions.setdefault(cat, [])
        
        # Load first category
        # self.category_selector.select_button(0)

    def get_current_category(self) -> str:
        """
        Get the currently selected category name.
        
        Returns:
            Current category name or empty string if none selected
        """
        button_name, index = self.category_selector.get_current_selection()
        return button_name if index >= 0 else ""


# =============================================================================
#  EXPORT
# =============================================================================
__all__ = ['DiscussionsStack', 'DiscussionThread']