"""Animated Stack Module.

QStackedWidget with smooth slide transition animations.

API
---
- **AnimatedStackedWidget**: Stacked widget with animated page transitions
"""

from PyQt6.QtCore import QEasingCurve, QPoint, QPropertyAnimation
from PyQt6.QtWidgets import QStackedWidget


class AnimatedStackedWidget(QStackedWidget):
    """Custom QStackedWidget with slide animations.

    Provides horizontal slide transitions when changing pages.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_index = 0
        self._animation = None

    def slideToIndex(self, index):
        """Animate transition to a new index with slide effect"""
        if index == self.currentIndex() or index < 0 or index >= self.count():
            return

        # Determine slide direction based on index comparison
        direction = 1 if index > self.currentIndex() else -1

        # Get widgets
        old_widget = self.currentWidget()
        new_widget = self.widget(index)

        if old_widget is None or new_widget is None:
            self.setCurrentIndex(index)
            return

        # Get dimensions
        width = self.width()
        height = self.height()

        # Position new widget off-screen (below if going forward, above if going back)
        new_widget.setGeometry(0, height * direction, width, height)
        new_widget.show()
        new_widget.raise_()

        # Create animations
        old_animation = QPropertyAnimation(old_widget, b"pos")
        old_animation.setDuration(350)
        old_animation.setStartValue(QPoint(0, 0))
        old_animation.setEndValue(QPoint(0, -height * direction))
        old_animation.setEasingCurve(QEasingCurve.Type.InOutCubic)

        new_animation = QPropertyAnimation(new_widget, b"pos")
        new_animation.setDuration(350)
        new_animation.setStartValue(QPoint(0, height * direction))
        new_animation.setEndValue(QPoint(0, 0))
        new_animation.setEasingCurve(QEasingCurve.Type.InOutCubic)

        # When animation finishes, update current index
        def on_animation_finished():
            self.setCurrentIndex(index)
            old_widget.hide()
            new_widget.setGeometry(0, 0, width, height)

        new_animation.finished.connect(on_animation_finished)

        # Start animations
        old_animation.start()
        new_animation.start()

        # Store reference to prevent garbage collection
        self._animation = (old_animation, new_animation)
