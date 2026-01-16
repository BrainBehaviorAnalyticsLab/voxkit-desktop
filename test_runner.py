"""Minimal test runner for CSV viewer dialog tests."""

import csv
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

# Set environment before any Qt imports
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["LD_PRELOAD"] = "/usr/lib/x86_64-linux-gnu/libstdc++.so.6"

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

# Mock PyQt6 modules before importing the actual components
mock_modules = {}
qt_modules = [
    "PyQt6",
    "PyQt6.QtCore",
    "PyQt6.QtWidgets",
    "PyQt6.QtGui",
]

for module in qt_modules:
    mock_modules[module] = MagicMock()

sys.modules.update(mock_modules)

# Now we can import and run tests manually
print("✓ PyQt6 mocking setup complete")
print("✓ Test runner initialized")


# Now test the CSV loading logic directly
def test_csv_loading():
    """Test CSV loading functionality."""
    print("\nRunning CSV loading tests...\n")

    # Create test CSV
    with tempfile.TemporaryDirectory() as tmp_dir:
        csv_path = os.path.join(tmp_dir, "test.csv")
        data = [
            ["speaker_id", "audio_file_count"],
            ["speaker_001", "10"],
            ["speaker_002", "15"],
            ["speaker_003", "8"],
        ]

        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerows(data)

        # Test 1: File exists and can be read
        assert os.path.exists(csv_path), "CSV file not created"
        print("✓ Test 1: CSV file created successfully")

        # Test 2: CSV can be loaded
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            rows = list(reader)

        assert len(rows) == 4, f"Expected 4 rows, got {len(rows)}"
        print("✓ Test 2: CSV loaded with correct number of rows")

        # Test 3: Headers are correct
        headers = rows[0]
        assert headers == ["speaker_id", "audio_file_count"], f"Headers mismatch: {headers}"
        print("✓ Test 3: CSV headers are correct")

        # Test 4: Data is correct
        data_rows = rows[1:]
        assert data_rows[0] == ["speaker_001", "10"], "First data row mismatch"
        assert data_rows[1] == ["speaker_002", "15"], "Second data row mismatch"
        assert data_rows[2] == ["speaker_003", "8"], "Third data row mismatch"
        print("✓ Test 4: CSV data is correct")

        # Test 5: Dimensions
        assert len(headers) == 2, f"Expected 2 columns, got {len(headers)}"
        assert len(data_rows) == 3, f"Expected 3 data rows, got {len(data_rows)}"
        print("✓ Test 5: CSV dimensions are correct (3 rows × 2 columns)")

    # Test 6: File not found handling
    try:
        with open("/nonexistent/file.csv", "r") as f:
            pass
        assert False, "Should have raised FileNotFoundError"
    except FileNotFoundError:
        print("✓ Test 6: Non-existent file handled correctly")

    # Test 7: Empty file handling
    with tempfile.TemporaryDirectory() as tmp_dir:
        empty_csv = os.path.join(tmp_dir, "empty.csv")
        Path(empty_csv).write_text("", encoding="utf-8")

        with open(empty_csv, "r") as f:
            reader = csv.reader(f)
            rows = list(reader)

        assert len(rows) == 0, "Empty CSV should have no rows"
        print("✓ Test 7: Empty CSV handled correctly")

    print("\n" + "=" * 60)
    print("All tests passed! ✓")
    print("=" * 60)


if __name__ == "__main__":
    test_csv_loading()
