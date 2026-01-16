"""Test Qt environment setup."""

import os
import sys

# Must set Qt platform BEFORE importing any Qt module
os.environ["QT_QPA_PLATFORM"] = "offscreen"

# Try to work around missing EGL
os.environ["QT_DEBUG_PLUGINS"] = "1"

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

# Try importing PyQt6
try:
    from PyQt6.QtWidgets import QApplication

    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    print("✓ PyQt6 initialized successfully")
except Exception as e:
    print(f"✗ Failed to initialize PyQt6: {e}")
    sys.exit(1)
