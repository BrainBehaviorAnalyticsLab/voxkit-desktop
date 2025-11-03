"""
Demo script for HorizontalButtonSelector

Shows how to use the horizontal scrolling button selector with callbacks.
"""

import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt
from ui.widgets.horizontal_button_selector import HorizontalButtonSelector


class DemoWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Horizontal Button Selector Demo")
        self.setMinimumSize(900, 400)
        
        # Light background
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f7fa;
            }
        """)
        
        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        
        # Status label to show selections
        self.status_label = QLabel("Click a button or scroll with mouse wheel")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("""
            QLabel {
                font-size: 18px;
                color: #333;
                padding: 20px;
                background-color: white;
                border-radius: 8px;
            }
        """)
        layout.addWidget(self.status_label)
        
        # Create the horizontal button selector
        self.selector = HorizontalButtonSelector()
        
        # Configure with buttons and callbacks
        buttons_config = [
            ("Home", self.on_home),
            ("Products", self.on_products),
            ("Services", self.on_services),
            ("About", self.on_about),
            ("Contact", self.on_contact),
            ("Blog", self.on_blog),
            ("Support", self.on_support),
            ("Careers", self.on_careers),
        ]
        
        self.selector.configure(buttons_config)
        
        # Also connect to the signal (alternative to callbacks)
        self.selector.selection_changed.connect(self.on_selection_changed)
        
        layout.addWidget(self.selector)
        layout.addStretch()
    
    # Callback functions
    def on_home(self):
        print("Home callback called!")
    
    def on_products(self):
        print("Products callback called!")
    
    def on_services(self):
        print("Services callback called!")
    
    def on_about(self):
        print("About callback called!")
    
    def on_contact(self):
        print("Contact callback called!")
    
    def on_blog(self):
        print("Blog callback called!")
    
    def on_support(self):
        print("Support callback called!")
    
    def on_careers(self):
        print("Careers callback called!")
    
    # Signal handler
    def on_selection_changed(self, button_name: str, index: int):
        """Handle selection change via signal"""
        self.status_label.setText(f"Selected: {button_name} (index {index})")
        print(f"Selection changed signal: {button_name} at index {index}")


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = DemoWindow()
    window.show()
    
    print("\n=== Horizontal Button Selector Demo ===")
    print("- Click any button to select it")
    print("- Use mouse wheel to navigate")
    print("- Watch buttons scale as they move toward/away from center")
    print("- Check console for callback and signal output\n")
    
    sys.exit(app.exec())