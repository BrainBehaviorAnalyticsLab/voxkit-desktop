"""Test suite for AlignmentEngine base functionality."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from voxkit.engines.base import AlignmentEngine
from voxkit.gui.frameworks.settings_modal import FieldConfig, FieldType, SettingsConfig


class MockEngine(AlignmentEngine):
    """Mock implementation of AlignmentEngine for testing."""

    def align(self, dataset_id: str, model_id: str) -> None:
        """Mock align method."""
        pass

    def train_aligner(
        self, audio_root: Path, textgrid_root: Path, base_model_id: str | None, new_model_id: str
    ) -> None:
        """Mock train_aligner method."""
        pass

    def _validate_train_settings(self, settings: dict) -> bool:
        """Validate training settings."""
        required_keys = ["epochs", "use_gpu"]
        return all(key in settings for key in required_keys)

    def _validate_align_settings(self, settings: dict) -> bool:
        """Validate alignment settings."""
        required_keys = ["use_speaker_adaptation", "file_type"]
        return all(key in settings for key in required_keys)


@pytest.fixture
def temp_storage_root(tmp_path):
    """Provide a temporary storage root directory."""
    return tmp_path


@pytest.fixture
def mock_engine():
    """Create a mock engine with test configurations."""
    train_config = SettingsConfig(
        title="Test Training Settings",
        dimensions=(400, 300),
        apply_blur=True,
        fields=[
            FieldConfig(
                name="epochs",
                label="Number of Epochs",
                field_type=FieldType.SPINBOX,
                default_value=50,
                min_value=1,
                max_value=1000,
            ),
            FieldConfig(
                name="use_gpu",
                label="Use GPU",
                field_type=FieldType.CHECKBOX,
                default_value=False,
            ),
        ],
        store_file="TEST_ENGINE/train/settings.json",
    )

    align_config = SettingsConfig(
        title="Test Alignment Settings",
        dimensions=(400, 300),
        apply_blur=True,
        fields=[
            FieldConfig(
                name="use_speaker_adaptation",
                label="Use Speaker Adaptation",
                field_type=FieldType.CHECKBOX,
                default_value=False,
            ),
            FieldConfig(
                name="file_type",
                label="File Type",
                field_type=FieldType.LINEEDIT,
                default_value="wav",
            ),
        ],
        store_file="TEST_ENGINE/align/settings.json",
    )

    return MockEngine(
        settings_configurations={"train": train_config, "align": align_config},
        id="TEST_ENGINE",
    )


class TestGetDefaultSettings:
    """Test the _get_default_settings method."""

    def test_extracts_defaults_from_config(self, mock_engine):
        """Test that default settings are correctly extracted from SettingsConfig."""
        train_config = mock_engine.settings_configurations["train"]
        defaults = mock_engine._get_default_settings(train_config)

        assert defaults == {"epochs": 50, "use_gpu": False}

    def test_handles_empty_fields(self, mock_engine):
        """Test handling of SettingsConfig with no fields."""
        empty_config = SettingsConfig(
            title="Empty Config",
            dimensions=(400, 300),
            apply_blur=False,
            fields=[],
            store_file="empty.json",
        )
        defaults = mock_engine._get_default_settings(empty_config)
        assert defaults == {}


class TestGetSettings:
    """Test the get_settings method with default fallback behavior."""

    def test_returns_defaults_when_file_missing(self, mock_engine, temp_storage_root):
        """Test that default settings are returned when JSON file doesn't exist."""
        with patch("voxkit.engines.base.get_storage_root", return_value=temp_storage_root):
            settings = mock_engine.get_settings("align")

            # Should return the default values
            assert settings == {"use_speaker_adaptation": False, "file_type": "wav"}

            # Should have created the settings file
            settings_path = temp_storage_root / "TEST_ENGINE/align/settings.json"
            assert settings_path.exists()

            # Verify the saved file contains the defaults
            with open(settings_path) as f:
                saved_settings = json.load(f)
            assert saved_settings == settings

    def test_loads_existing_settings(self, mock_engine, temp_storage_root):
        """Test that existing settings are loaded when file exists."""
        # Create settings file with custom values
        settings_path = temp_storage_root / "TEST_ENGINE/train/settings.json"
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        custom_settings = {"epochs": 100, "use_gpu": True}
        with open(settings_path, "w") as f:
            json.dump(custom_settings, f)

        with patch("voxkit.engines.base.get_storage_root", return_value=temp_storage_root):
            settings = mock_engine.get_settings("train")
            assert settings == custom_settings

    def test_validates_loaded_settings(self, mock_engine, temp_storage_root):
        """Test that loaded settings are validated."""
        # Create settings file with invalid values
        settings_path = temp_storage_root / "TEST_ENGINE/align/settings.json"
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        invalid_settings = {"invalid_key": "value"}
        with open(settings_path, "w") as f:
            json.dump(invalid_settings, f)

        with patch("voxkit.engines.base.get_storage_root", return_value=temp_storage_root):
            with pytest.raises(ValueError, match="Invalid align settings"):
                mock_engine.get_settings("align")

    def test_validates_default_settings(self, mock_engine, temp_storage_root):
        """Test that default settings pass validation."""
        with patch("voxkit.engines.base.get_storage_root", return_value=temp_storage_root):
            # Should not raise an error
            settings = mock_engine.get_settings("train")
            assert settings is not None

    def test_raises_error_for_unavailable_tool(self, mock_engine):
        """Test that error is raised for unavailable tool type."""
        with pytest.raises(ValueError, match="Tool type 'invalid' is not available"):
            mock_engine.get_settings("invalid")

    def test_unified_behavior_train_and_align(self, mock_engine, temp_storage_root):
        """Test that train and align tool types behave consistently."""
        with patch("voxkit.engines.base.get_storage_root", return_value=temp_storage_root):
            # Both should work without errors and create default settings
            train_settings = mock_engine.get_settings("train")
            align_settings = mock_engine.get_settings("align")

            assert train_settings is not None
            assert align_settings is not None

            # Both should have created files
            train_path = temp_storage_root / "TEST_ENGINE/train/settings.json"
            align_path = temp_storage_root / "TEST_ENGINE/align/settings.json"
            assert train_path.exists()
            assert align_path.exists()


class TestSaveJson:
    """Test the _save_json method."""

    def test_creates_parent_directories(self, mock_engine, temp_storage_root):
        """Test that parent directories are created if they don't exist."""
        test_path = temp_storage_root / "deep/nested/path/test.json"
        test_data = {"key": "value"}

        mock_engine._save_json(test_data, test_path)

        assert test_path.exists()
        with open(test_path) as f:
            loaded_data = json.load(f)
        assert loaded_data == test_data
