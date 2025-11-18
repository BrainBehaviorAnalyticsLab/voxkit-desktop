"""
Horizontal Scrolling Button Selector with Radial Scaling Effect

A reusable PyQt6 widget that displays a horizontally scrolling list of buttons.
The button closest to center is automatically selected, with smooth animations
and a radial scaling effect where buttons expand as they approach the center.
"""

from typing import Callable, Dict, List, Optional

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)


class ScalableButton(QPushButton):
    """A button that can smoothly scale in size based on distance from center"""

    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.base_font_size = 14
        self.current_scale = 0.2
        self.button_name = text

        # Base styling
        self.setMinimumWidth(85)
        self.setMinimumHeight(30)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def set_scale(self, scale: float):
        """
        Update button scale (0.6 to 1.3)

        Args:
            scale: Scale factor where 1.3 is centered/selected, 0.6 is far away
        """
        self.current_scale = scale

        # Update font size
        font = QFont()
        font_size = int(self.base_font_size * scale)
        font.setPointSize(max(9, font_size))
        # font.setBold(scale >= 1.2)  # Bold when near/at center
        self.setFont(font)

        # Update widget size
        base_width = 100
        base_height = 40
        scaled_width = int(base_width * scale)
        scaled_height = int(base_height * scale)

        self.setMinimumWidth(scaled_width)
        self.setMinimumHeight(scaled_height)
        self.setMaximumWidth(scaled_width + 60)

        # Note: Don't update style here - will be set by _force_selected_state

    def _force_selected_state(self, is_selected: bool):
        """
        Force the button into selected or unselected state.
        This overrides the automatic scale-based selection.

        Args:
            is_selected: True to make blue/selected, False to make gray/unselected
        """
        if is_selected:
            # Selected/centered style
            self.setStyleSheet("""
                QPushButton {
                    background-color: #0d8ac7;
                    color: white;
                    border: 2px solid #0b7ab0;
                    border-radius: 8px;
                    padding: 8px 16px;
                }
                QPushButton:hover {
                    background-color: #0b7ab0;
                }
            """)
        else:
            # Unselected style with opacity based on scale
            scale = self.current_scale
            opacity = 0.4 + (scale - 0.6) * 0.6  # 0.4 to 1.0
            gray_value = int(140 + (scale - 0.6) * 50)  # Lighter as it gets closer

            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: rgba({gray_value}, {gray_value}, {gray_value}, {opacity});
                    color: rgba(60, 60, 60, {opacity + 0.3});
                    border: 1px solid rgba(180, 180, 180, {opacity * 0.6});
                    border-radius: 6px;
                    padding: 6px 12px;
                }}
                QPushButton:hover {{
                    background-color: rgba({gray_value + 20}, {gray_value + 20}, {gray_value + 20}, {opacity + 0.2});
                }}
            """)


class HorizontalButtonSelector(QWidget):
    """
    Horizontal scrolling button selector with automatic center selection.

    Features:
    - Buttons automatically centered when selected
    - Radial scaling effect (buttons expand as they approach center)
    - Smooth animations
    - Configurable button names and callbacks
    - Click or scroll to select

    Signals:
        selection_changed(str, int): Emitted when selection changes (button_name, index)
    """

    selection_changed = pyqtSignal(str, int)  # button_name, index

    def __init__(self, parent=None):
        super().__init__(parent)
        self.buttons: List[ScalableButton] = []
        self.button_callbacks: Dict[str, Callable] = {}
        self.current_index = 0
        self.is_animating = False

        # Scale configuration
        self.max_scale = 2.5  # Default maximum scale for centered button
        self.min_scale = 0.2  # Default minimum scale for edge buttons

        # Scroll debouncing
        self.scroll_accumulator = 0
        self.scroll_threshold = 120  # Require 120 units before switching
        self.scroll_timer = QTimer()
        self.scroll_timer.setSingleShot(True)
        self.scroll_timer.timeout.connect(self._reset_scroll_accumulator)
        self.scroll_timeout = 300  # Reset accumulator after 300ms of no scrolling

        self._init_ui()

    def _init_ui(self):
        """Initialize the UI"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Create a container that will hold scroll area + fade overlays

        self.scroll_container = QWidget()
        self.scroll_container.setFixedHeight(100)

        # Use absolute positioning for overlays
        self.scroll_container_layout = QVBoxLayout(self.scroll_container)
        self.scroll_container_layout.setContentsMargins(0, 0, 0, 0)
        self.scroll_container_layout.setSpacing(0)

        # Scroll area (base layer)
        self.scroll_area = QScrollArea(self.scroll_container)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setGeometry(0, 0, self.scroll_container.width(), 100)
        self.scroll_area.setStyleSheet("background: transparent;")

        # Container for buttons
        self.container = QWidget()
        self.container.setStyleSheet("background: transparent;")
        self.container_layout = QHBoxLayout(self.container)
        self.container_layout.setSpacing(25)
        self.container_layout.setContentsMargins(400, 15, 400, 15)

        self.scroll_area.setWidget(self.container)

        # Left fade overlay
        self.left_fade = QLabel(self.scroll_container)
        self.left_fade.setFixedWidth(150)
        self.left_fade.setFixedHeight(100)
        self.left_fade.setStyleSheet("""
            background: qlineargradient(
                x1:0, y1:0, x2:1, y2:0,
                stop:0 rgba(245, 247, 250, 255),
                stop:0.7 rgba(245, 247, 250, 200),
                stop:1 rgba(245, 247, 250, 0)
            );
        """)
        self.left_fade.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.left_fade.move(0, 0)
        self.left_fade.raise_()

        # Right fade overlay
        self.right_fade = QLabel(self.scroll_container)
        self.right_fade.setFixedWidth(150)
        self.right_fade.setFixedHeight(100)
        self.right_fade.setStyleSheet("""
            background: qlineargradient(
                x1:0, y1:0, x2:1, y2:0,
                stop:0 rgba(245, 247, 250, 0),
                stop:0.3 rgba(245, 247, 250, 200),
                stop:1 rgba(245, 247, 250, 255)
            );
        """)
        self.right_fade.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.right_fade.raise_()

        main_layout.addWidget(self.scroll_container)

        # Connect scroll to update scales
        self.scroll_area.horizontalScrollBar().valueChanged.connect(self._update_button_scales)

    def configure(self, buttons_config: List[tuple[str, Optional[Callable]]]):
        """
        Configure the button selector with button names and callbacks.

        Args:
            buttons_config: List of tuples (button_name, callback_function)
                           callback can be None if using selection_changed signal

        Example:
            selector.configure([
                ("Home", home_callback),
                ("Settings", settings_callback),
                ("About", None),  # Use signal instead
            ])
        """
        # Clear existing buttons
        for button in self.buttons:
            self.container_layout.removeWidget(button)
            button.deleteLater()

        self.buttons.clear()
        self.button_callbacks.clear()

        # Create new buttons
        for button_name, callback in buttons_config:
            button = ScalableButton(button_name)
            button.clicked.connect(lambda checked, name=button_name: self._on_button_clicked(name))

            self.buttons.append(button)
            self.container_layout.addWidget(button)

            if callback is not None:
                self.button_callbacks[button_name] = callback

        # # Initial selection
        # QTimer.singleShot(100, lambda: self.select_button(0))

    def set_scroll_sensitivity(self, threshold: int = 120, timeout_ms: int = 300):
        """
        Configure scroll wheel sensitivity.

        Args:
            threshold: Amount of scroll delta required to trigger navigation (default: 120)
                      Higher = less sensitive (requires more scrolling)
                      Lower = more sensitive (reacts to smaller scrolls)
            timeout_ms: Time in milliseconds before resetting accumulator (default: 300)
                       Shorter = must scroll quickly to accumulate
                       Longer = can scroll slowly and still accumulate

        Examples:
            set_scroll_sensitivity(80, 200)   # More sensitive, faster timeout
            set_scroll_sensitivity(200, 500)  # Less sensitive, slower timeout
        """
        self.scroll_threshold = max(30, threshold)  # Minimum threshold of 30
        self.scroll_timeout = max(100, timeout_ms)  # Minimum timeout of 100ms

    def set_edge_fade_color(self, r: int = 245, g: int = 247, b: int = 250):
        """
        Configure the color used for edge fade effect.
        Should match the background color of the parent widget.

        Args:
            r: Red component (0-255)
            g: Green component (0-255)
            b: Blue component (0-255)

        Example:
            set_edge_fade_color(255, 255, 255)  # White background
            set_edge_fade_color(240, 240, 245)  # Light gray background
        """
        if not hasattr(self, "left_fade") or not hasattr(self, "right_fade"):
            return

        # Update left fade
        self.left_fade.setStyleSheet(f"""
            background: qlineargradient(
                x1:0, y1:0, x2:1, y2:0,
                stop:0 rgba({r}, {g}, {b}, 255),
                stop:0.7 rgba({r}, {g}, {b}, 200),
                stop:1 rgba({r}, {g}, {b}, 0)
            );
        """)

        # Update right fade
        self.right_fade.setStyleSheet(f"""
            background: qlineargradient(
                x1:0, y1:0, x2:1, y2:0,
                stop:0 rgba({r}, {g}, {b}, 0),
                stop:0.3 rgba({r}, {g}, {b}, 200),
                stop:1 rgba({r}, {g}, {b}, 255)
            );
        """)

    def set_scale_range(self, max_scale: float = 1.8, min_scale: float = 0.5):
        """
        Configure the expansion/scaling range for buttons.

        Args:
            max_scale: Maximum scale for centered button (default: 1.3)
                      Higher = more dramatic expansion
                      Examples: 1.5 (larger), 2.0 (much larger), 1.2 (subtle)
            min_scale: Minimum scale for edge buttons (default: 0.6)
                      Lower = buttons shrink more at edges
                      Examples: 0.4 (much smaller), 0.7 (less shrinking)

        Examples:
            # More dramatic expansion (center 2x, edges 0.5x)
            selector.set_scale_range(max_scale=2.0, min_scale=0.5)

            # Subtle effect (center 1.2x, edges 0.8x)
            selector.set_scale_range(max_scale=1.2, min_scale=0.8)

            # Extreme expansion (center 2.5x!)
            selector.set_scale_range(max_scale=2.5, min_scale=0.4)
        """
        self.max_scale = max(1.0, max_scale)  # At least 1.0x
        self.min_scale = max(0.3, min(min_scale, max_scale - 0.2))  # Min can't exceed max

        # Recalculate all button scales with new range
        if hasattr(self, "buttons") and self.buttons:
            self._update_button_scales()

    def _on_button_clicked(self, button_name: str):
        """Handle button click"""
        try:
            index = [btn.button_name for btn in self.buttons].index(button_name)
            self.select_button(index)
        except ValueError:
            pass

    def select_button(self, index: int):
        """
        Select a button by index, scrolling it to center.

        Args:
            index: Index of button to select (0-based)
        """
        if not (0 <= index < len(self.buttons)) or self.is_animating:
            return

        old_index = self.current_index
        self.current_index = index

        # Scroll to center
        self._scroll_to_center(index)

        # Emit signal
        button_name = self.buttons[index].button_name
        self.selection_changed.emit(button_name, index)

        # Call callback if configured
        if button_name in self.button_callbacks:
            self.button_callbacks[button_name]()

    def select_button_by_name(self, button_name: str):
        """
        Select a button by name.

        Args:
            button_name: Name of button to select
        """
        try:
            index = [btn.button_name for btn in self.buttons].index(button_name)
            self.select_button(index)
        except ValueError:
            print(f"Warning: Button '{button_name}' not found")

    def _scroll_to_center(self, index: int):
        """Smoothly scroll button to center"""
        if index < 0 or index >= len(self.buttons):
            return

        button = self.buttons[index]
        scroll_bar = self.scroll_area.horizontalScrollBar()
        viewport_width = self.scroll_area.viewport().width()

        # Calculate target scroll position
        button_x = button.x()
        button_width = button.width()
        button_center = button_x + button_width // 2
        target_scroll = button_center - viewport_width // 2

        # Clamp to valid range
        target_scroll = max(scroll_bar.minimum(), min(target_scroll, scroll_bar.maximum()))

        # Animate
        current_scroll = scroll_bar.value()
        if abs(target_scroll - current_scroll) < 5:
            scroll_bar.setValue(target_scroll)
            self._update_button_scales()
            return

        self._animate_scroll(current_scroll, target_scroll)

    def _animate_scroll(self, start_value: int, end_value: int):
        """Animate scroll position smoothly"""
        self.is_animating = True
        scroll_bar = self.scroll_area.horizontalScrollBar()

        duration = 350  # milliseconds
        steps = 25
        step_duration = duration // steps

        def animate_step(current_step: int):
            if current_step >= steps:
                scroll_bar.setValue(end_value)
                self._update_button_scales()
                self.is_animating = False
                return

            # Ease in-out cubic
            progress = current_step / steps
            if progress < 0.5:
                eased = 4 * progress**3
            else:
                eased = 1 - pow(-2 * progress + 2, 3) / 2

            value = start_value + (end_value - start_value) * eased
            scroll_bar.setValue(int(value))

            QTimer.singleShot(step_duration, lambda: animate_step(current_step + 1))

        animate_step(0)

    def _update_button_scales(self):
        """Update all button scales based on distance from center"""
        viewport_width = self.scroll_area.viewport().width()
        viewport_center = viewport_width / 2
        scroll_offset = self.scroll_area.horizontalScrollBar().value()

        # Track which button is closest to center
        closest_button = None
        closest_index = -1
        min_distance = float("inf")

        # First pass: calculate distances and find closest
        button_distances = []
        for i, button in enumerate(self.buttons):
            button_rect = button.geometry()
            button_center_x = button_rect.x() + button_rect.width() // 2
            viewport_position = button_center_x - scroll_offset
            distance = abs(viewport_position - viewport_center)

            button_distances.append((button, distance))

            if distance < min_distance:
                min_distance = distance
                closest_button = button
                closest_index = i

        # Check if the closest button changed - if so, update selection
        # BUT only if we're not currently animating (to prevent double-triggering on clicks)
        if closest_index != -1 and closest_index != self.current_index and not self.is_animating:
            old_index = self.current_index
            self.current_index = closest_index

            # Emit signal
            button_name = self.buttons[closest_index].button_name
            self.selection_changed.emit(button_name, closest_index)

            # Call callback if configured
            if button_name in self.button_callbacks:
                self.button_callbacks[button_name]()

        # Second pass: update scales, only closest gets blue
        for button, distance in button_distances:
            # Calculate scale: 1.3 at center, down to 0.6 at edges
            if distance < 30:  # Very close to center
                scale = 1.3
            else:
                max_distance = viewport_width * 0.7
                normalized = min(distance / max_distance, 1.0)
                scale = 1.3 - (0.7 * normalized)

            # Only the closest button gets the "selected" treatment
            is_selected = button == closest_button
            button.set_scale(scale)
            button._force_selected_state(is_selected)

        self.container.updateGeometry()

    def get_current_selection(self) -> tuple[str, int]:
        """
        Get current selection.

        Returns:
            Tuple of (button_name, index)
        """
        if 0 <= self.current_index < len(self.buttons):
            return (self.buttons[self.current_index].button_name, self.current_index)
        return ("", -1)

    def _reset_scroll_accumulator(self):
        """Reset scroll accumulator after timeout"""
        self.scroll_accumulator = 0

    def wheelEvent(self, event):
        """Handle mouse wheel for navigation with debouncing"""
        if self.is_animating:
            event.accept()
            return

        # Get scroll delta
        delta = event.angleDelta().y()

        # Accumulate scroll
        self.scroll_accumulator += delta

        # Restart the timeout timer
        self.scroll_timer.stop()
        self.scroll_timer.start(self.scroll_timeout)

        # Check if we've accumulated enough scroll to trigger a change
        if abs(self.scroll_accumulator) >= self.scroll_threshold:
            if self.scroll_accumulator > 0 and self.current_index > 0:
                # Scroll up/left - go to previous
                self.select_button(self.current_index - 1)
                self.scroll_accumulator = 0
            elif self.scroll_accumulator < 0 and self.current_index < len(self.buttons) - 1:
                # Scroll down/right - go to next
                self.select_button(self.current_index + 1)
                self.scroll_accumulator = 0

        event.accept()

    def resizeEvent(self, event):
        """Handle resize"""
        super().resizeEvent(event)

        # Resize scroll area to match container
        if hasattr(self, "scroll_area") and hasattr(self, "scroll_container"):
            self.scroll_area.setGeometry(0, 0, self.scroll_container.width(), 100)

        # Reposition right fade overlay
        if hasattr(self, "right_fade") and hasattr(self, "scroll_container"):
            self.right_fade.move(self.scroll_container.width() - 150, 0)

        QTimer.singleShot(50, self._update_button_scales)


__all__ = ["HorizontalButtonSelector", "ScalableButton"]
