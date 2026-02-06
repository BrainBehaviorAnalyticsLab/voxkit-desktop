import json
from pathlib import Path

import pytest

from voxkit.engines.base import AlignmentEngine


class MockField:
    """Mock field object for settings configuration."""

    def __init__(self, name: str, default_value):
        self.name = name
        self.default_value = default_value


class MockSettingsConfig:
    """Mock settings configuration object."""

    def __init__(self, store_file: str, fields: list):
        self.store_file = store_file
        self.fields = fields


class ConcreteTestEngine(AlignmentEngine):
    """Concrete implementation of AlignmentEngine for testing."""

    def __init__(self, **kwargs):
        # Create mock settings configurations
        self.mock_train_config = MockSettingsConfig(
            store_file="test_engine/train_settings.json",
            fields=[
                MockField("param1", "default1"),
                MockField("param2", 42),
            ],
        )

        self.mock_align_config = MockSettingsConfig(
            store_file="test_engine/align_settings.json",
            fields=[
                MockField("align_param", True),
            ],
        )

        settings_configurations = {
            "train": self.mock_train_config,
            "align": self.mock_align_config,
        }

        super().__init__(settings_configurations=settings_configurations, **kwargs)

    def align(self, dataset_id: str, model_id: str) -> None:
        pass

    def train_aligner(
        self, audio_root: Path, textgrid_root: Path, base_model_id: str | None, new_model_id: str
    ) -> None:
        pass

    def _validate_train_settings(self, settings: dict) -> bool:
        return "param1" in settings

    def _validate_align_settings(self, settings: dict) -> bool:
        return "align_param" in settings


@pytest.fixture
def temp_storage(tmp_path, monkeypatch):
    """Create a temporary storage root for testing."""
    monkeypatch.setattr("voxkit.engines.base.get_storage_root", lambda: tmp_path)
    return tmp_path


@pytest.fixture
def engine():
    """Create a test engine instance."""
    return ConcreteTestEngine(
        reference_url="https://example.com",
        description="Test engine description",
        human_readable_name="Test Engine",
        id="test_engine",
    )


class TestAlignmentEngineInit:
    def test_init_with_all_params(self):
        engine = ConcreteTestEngine(
            reference_url="https://example.com",
            description="Custom description",
            human_readable_name="Custom Name",
            id="custom_id",
        )

        assert engine.reference_url == "https://example.com"
        assert engine.description == "Custom description"
        assert engine.human_readable_name == "Custom Name"
        assert engine.id == "custom_id"

    def test_init_with_defaults(self):
        engine = ConcreteTestEngine()

        assert engine.reference_url is None
        assert "ConcreteTestEngine" in engine.description
        assert engine.human_readable_name == "ConcreteTestEngine"
        assert engine.id == "ConcreteTestEngine"

    def test_init_partial_params(self):
        engine = ConcreteTestEngine(
            reference_url="https://test.com",
        )

        assert engine.reference_url == "https://test.com"
        assert engine.human_readable_name == "ConcreteTestEngine"


class TestHasTool:
    def test_has_tool_train(self, engine):
        assert engine.has_tool("train") is True

    def test_has_tool_align(self, engine):
        assert engine.has_tool("align") is True

    def test_has_tool_transcribe_false(self, engine):
        assert engine.has_tool("transcribe") is False


class TestSourceAndName:
    def test_source_with_url(self, engine):
        assert engine.source() == "https://example.com"

    def test_source_without_url(self):
        engine = ConcreteTestEngine()
        assert engine.source() == "No source URL provided."

    def test_name(self, engine):
        assert engine.name() == "Test Engine"

    def test_str(self, engine):
        assert str(engine) == "Test engine description"


class TestSaveAndLoadJson:
    def test_save_json_creates_file(self, engine, tmp_path):
        file_path = tmp_path / "test.json"
        data = {"key": "value", "number": 42}

        engine._save_json(data, file_path)

        assert file_path.exists()
        with open(file_path) as f:
            loaded = json.load(f)
        assert loaded == data

    def test_save_json_creates_parent_dirs(self, engine, tmp_path):
        file_path = tmp_path / "nested" / "dirs" / "test.json"
        data = {"test": "data"}

        engine._save_json(data, file_path)

        assert file_path.exists()

    def test_save_json_with_string_path(self, engine, tmp_path):
        file_path = str(tmp_path / "string_path.json")
        data = {"string": "path"}

        engine._save_json(data, file_path)

        assert Path(file_path).exists()

    def test_load_json_existing_file(self, engine, tmp_path):
        file_path = tmp_path / "existing.json"
        data = {"existing": "data"}
        with open(file_path, "w") as f:
            json.dump(data, f)

        loaded = engine._load_json(file_path)

        assert loaded == data

    def test_load_json_nonexistent_file(self, engine, tmp_path):
        file_path = tmp_path / "nonexistent.json"

        loaded = engine._load_json(file_path)

        assert loaded == {}

    def test_load_json_with_string_path(self, engine, tmp_path):
        file_path = tmp_path / "string.json"
        data = {"string": "load"}
        with open(file_path, "w") as f:
            json.dump(data, f)

        loaded = engine._load_json(str(file_path))

        assert loaded == data


class TestGetDefaultSettings:
    def test_get_default_settings(self, engine):
        # The mock fields have name and default_value attributes
        defaults = engine._get_default_settings(engine.mock_train_config)

        assert "param1" in defaults
        assert "param2" in defaults
        assert defaults["param1"] == "default1"
        assert defaults["param2"] == 42


class TestGetSettings:
    def test_get_settings_creates_defaults_when_missing(self, engine, temp_storage):
        settings = engine.get_settings("train")

        # Should have created settings file with defaults
        settings_path = temp_storage / "test_engine/train_settings.json"
        assert settings_path.exists()
        assert "param1" in settings

    def test_get_settings_loads_existing(self, engine, temp_storage):
        # Pre-create settings file
        settings_path = temp_storage / "test_engine/train_settings.json"
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        existing_settings = {"param1": "custom_value", "param2": 100}
        with open(settings_path, "w") as f:
            json.dump(existing_settings, f)

        settings = engine.get_settings("train")

        assert settings["param1"] == "custom_value"
        assert settings["param2"] == 100

    def test_get_settings_invalid_tool_type(self, engine, temp_storage):
        with pytest.raises(ValueError) as exc_info:
            engine.get_settings("transcribe")

        assert "not available" in str(exc_info.value)

    def test_get_settings_validation_failure(self, engine, temp_storage):
        # Pre-create invalid settings file (missing required param1)
        settings_path = temp_storage / "test_engine/train_settings.json"
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        invalid_settings = {"wrong_param": "value"}
        with open(settings_path, "w") as f:
            json.dump(invalid_settings, f)

        with pytest.raises(ValueError) as exc_info:
            engine.get_settings("train")

        assert "Invalid" in str(exc_info.value)


class TestGetSettingsConfig:
    def test_get_settings_config_valid(self, engine):
        config = engine.get_settings_config("train")

        assert config == engine.mock_train_config

    def test_get_settings_config_invalid(self, engine):
        with pytest.raises(ValueError) as exc_info:
            engine.get_settings_config("invalid_tool")

        assert "No settings configuration found" in str(exc_info.value)


class TestTranscribe:
    def test_transcribe_not_implemented(self, engine):
        with pytest.raises(NotImplementedError) as exc_info:
            engine.transcribe("dataset_id")

        assert "does not support transcription" in str(exc_info.value)

    def test_validate_transcribe_settings_default(self, engine):
        # Default implementation returns True
        assert engine._validate_transcribe_settings({}) is True
        assert engine._validate_transcribe_settings({"any": "settings"}) is True
