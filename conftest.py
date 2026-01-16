"""Test configuration."""

import os
import sys

# Set up Qt to use offscreen platform before importing PyQt6
os.environ["QT_QPA_PLATFORM"] = "offscreen"

# Ensure the src directory is in the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
