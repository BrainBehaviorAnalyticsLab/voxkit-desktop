import json

import pytest

from voxkit.storage import utils
from voxkit.storage.utils import generate_unique_id, readable_from_unique_id

from .test_setup import (
    activate_test_environment,
    deactivate_test_environment,
    mock_get_storage_root,
)


@pytest.fixture(autouse=True)
def manage_test_environment():
    # Setup before each test
    activate_test_environment(mock_get_storage_root())
    yield
    # Cleanup after each test
    deactivate_test_environment(mock_get_storage_root())


class TestUtils:
    class TestIsFirstLaunch:
        def test_is_first_launch_true(self, monkeypatch):
            """Test that is_first_launch returns True when flag file doesn't exist."""
            monkeypatch.setattr(utils, "get_storage_root", mock_get_storage_root)

            # Ensure no flag file exists
            flag_file = mock_get_storage_root() / ".first_launch_complete"
            if flag_file.exists():
                flag_file.unlink()

            result = utils.is_first_launch()
            assert result is True

        def test_is_first_launch_false(self, monkeypatch):
            """Test that is_first_launch returns False when flag file exists."""
            monkeypatch.setattr(utils, "get_storage_root", mock_get_storage_root)

            # Create the flag file
            flag_file = mock_get_storage_root() / ".first_launch_complete"
            flag_file.touch()

            result = utils.is_first_launch()
            assert result is False

    class TestMarkFirstLaunchComplete:
        def test_mark_first_launch_complete(self, monkeypatch):
            """Test that mark_first_launch_complete creates the flag file."""
            monkeypatch.setattr(utils, "get_storage_root", mock_get_storage_root)

            # Ensure no flag file exists
            flag_file = mock_get_storage_root() / ".first_launch_complete"
            if flag_file.exists():
                flag_file.unlink()

            # Verify first launch is True before marking complete
            assert utils.is_first_launch() is True

            # Mark first launch complete
            utils.mark_first_launch_complete()

            # Verify flag file now exists
            assert flag_file.exists() is True

            # Verify first launch is now False
            assert utils.is_first_launch() is False

        def test_mark_first_launch_complete_idempotent(self, monkeypatch):
            """Test that calling mark_first_launch_complete multiple times is safe."""
            monkeypatch.setattr(utils, "get_storage_root", mock_get_storage_root)

            # Call multiple times - should not raise
            utils.mark_first_launch_complete()
            utils.mark_first_launch_complete()
            utils.mark_first_launch_complete()

            flag_file = mock_get_storage_root() / ".first_launch_complete"
            assert flag_file.exists() is True

    class TestSaveJson:
        def test_save_json_success(self, monkeypatch):
            """Test that save_json writes JSON data correctly."""
            monkeypatch.setattr(utils, "get_storage_root", mock_get_storage_root)

            test_data = {"key": "value", "number": 42, "nested": {"inner": "data"}}
            file_path = mock_get_storage_root() / "test_output.json"

            utils.save_json(file_path, test_data)

            assert file_path.exists() is True

            with open(file_path, "r") as f:
                loaded_data = json.load(f)

            assert loaded_data == test_data

        def test_save_json_creates_parent_directories(self, monkeypatch):
            """Test that save_json creates parent directories if they don't exist."""
            monkeypatch.setattr(utils, "get_storage_root", mock_get_storage_root)

            test_data = {"test": "data"}
            nested_path = mock_get_storage_root() / "nested" / "dirs" / "output.json"

            # Ensure parent doesn't exist
            assert nested_path.parent.exists() is False

            utils.save_json(nested_path, test_data)

            assert nested_path.exists() is True
            assert nested_path.parent.exists() is True

            with open(nested_path, "r") as f:
                loaded_data = json.load(f)

            assert loaded_data == test_data

        def test_save_json_overwrites_existing(self, monkeypatch):
            """Test that save_json overwrites existing files."""
            monkeypatch.setattr(utils, "get_storage_root", mock_get_storage_root)

            file_path = mock_get_storage_root() / "overwrite_test.json"

            # Write initial data
            initial_data = {"initial": "data"}
            utils.save_json(file_path, initial_data)

            # Write new data
            new_data = {"new": "data", "completely": "different"}
            utils.save_json(file_path, new_data)

            with open(file_path, "r") as f:
                loaded_data = json.load(f)

            assert loaded_data == new_data
            assert "initial" not in loaded_data

    class TestGenerateUniqueId:
        def test_generate_unique_id_format(self):
            """Test that generate_unique_id returns correct format."""
            unique_id = generate_unique_id()

            # Format should be YYYYMMDD_HHMMSS_ffffff
            parts = unique_id.split("_")
            assert len(parts) == 3
            assert len(parts[0]) == 8  # YYYYMMDD
            assert len(parts[1]) == 6  # HHMMSS
            assert len(parts[2]) == 6  # ffffff (microseconds)

        def test_generate_unique_id_with_prefix(self):
            """Test that generate_unique_id handles prefix correctly."""
            unique_id = generate_unique_id(prefix="test")

            assert unique_id.startswith("test_")
            parts = unique_id.split("_")
            assert len(parts) == 4  # prefix + 3 timestamp parts
            assert parts[0] == "test"

        def test_generate_unique_id_uniqueness(self):
            """Test that multiple calls generate unique IDs."""
            ids = [generate_unique_id() for _ in range(100)]
            unique_ids = set(ids)

            # All IDs should be unique
            assert len(unique_ids) == len(ids)

    class TestReadableFromUniqueId:
        def test_readable_from_unique_id(self):
            """Test that readable_from_unique_id converts correctly."""
            unique_id = "20240115_143022_123456"
            readable = readable_from_unique_id(unique_id)

            assert "January" in readable
            assert "15" in readable
            assert "2024" in readable

        def test_readable_from_unique_id_format(self):
            """Test that readable output has expected format."""
            unique_id = "20231225_120000_000000"
            readable = readable_from_unique_id(unique_id)

            # Should contain "at" for time separator
            assert " at " in readable
            # Should contain AM/PM
            assert "AM" in readable or "PM" in readable
