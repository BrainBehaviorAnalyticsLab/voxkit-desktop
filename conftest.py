"""Pytest configuration for handling GUI dependencies in headless tests."""

import os
import sys
from unittest.mock import MagicMock

# Add src to path for tests FIRST before any voxkit imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Set environment variables for headless operation
os.environ['QT_QPA_PLATFORM'] = 'offscreen'

# Ensure libEGL can be found
os.environ['LD_LIBRARY_PATH'] = '/usr/local/share/chromium/chrome-linux:' + os.environ.get('LD_LIBRARY_PATH', '')

# Mock ALL problematic modules BEFORE importing anything from voxkit
problematic_modules = [
    'PyQt6', 'PyQt6.QtCore', 'PyQt6.QtGui', 'PyQt6.QtWidgets', 'PyQt6.QtSvg',
    'PyQt6.QtPrintSupport',
    'pypllrcomputer',
    'Wav2TextGrid', 'Wav2TextGrid.wav2textgrid', 'Wav2TextGrid.wav2textgrid_train',
    'alignment_comparison_plots',
    'faster_whisper',
]

# Create mock QObject first
class MockQObject:
    pass

# Mock all modules
for mod in problematic_modules:
    if mod not in sys.modules:
        sys.modules[mod] = MagicMock()

# Now override PyQt6.QtCore.QObject with our custom class
if 'PyQt6.QtCore' in sys.modules:
    sys.modules['PyQt6.QtCore'].QObject = MockQObject
if 'PyQt6' in sys.modules:
    sys.modules['PyQt6'].QtCore.QObject = MockQObject
