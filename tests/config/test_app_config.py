from pathlib import Path

import pytest

from voxkit.config.app_config import AppConfig, get_app_config, get_config_path


class TestGetConfigPath:
    def test_returns_path_object(self):
        result = get_config_path()
        assert isinstance(result, Path)

    def test_path_ends_with_config(self):
        result = get_config_path()
        assert result.name == "config"


class TestAppConfig:
    def test_dataclass_fields(self):
        config = AppConfig(
            app_name="TestApp",
            version="1.0.0",
            description="Test description",
            introduction="Test intro",
        )
        assert config.app_name == "TestApp"
        assert config.version == "1.0.0"
        assert config.description == "Test description"
        assert config.introduction == "Test intro"
        assert config.help_url == "http://localhost:3000/help"
        assert config.release_date is None
        assert config.release_notes is None

    def test_dataclass_with_optional_fields(self):
        config = AppConfig(
            app_name="TestApp",
            version="2.0.0",
            description="Desc",
            introduction="Intro",
            help_url="http://example.com/help",
            release_date="2024-01-01",
            release_notes="Initial release",
        )
        assert config.help_url == "http://example.com/help"
        assert config.release_date == "2024-01-01"
        assert config.release_notes == "Initial release"


class TestAppConfigFromYaml:
    def test_from_yaml_success(self, tmp_path):
        yaml_content = """
app_name: MyApp
version: 1.2.3
description: My application description
introduction: Welcome to MyApp
help_url: http://myapp.com/help
release_date: "2024-06-01"
release_notes: Bug fixes and improvements
"""
        config_file = tmp_path / "app_info.yaml"
        config_file.write_text(yaml_content)

        config = AppConfig.from_yaml(config_file)

        assert config.app_name == "MyApp"
        assert config.version == "1.2.3"
        assert config.description == "My application description"
        assert config.introduction == "Welcome to MyApp"
        assert config.help_url == "http://myapp.com/help"
        assert config.release_date == "2024-06-01"
        assert config.release_notes == "Bug fixes and improvements"

    def test_from_yaml_with_defaults(self, tmp_path):
        # Empty dict in YAML - all fields should use defaults
        yaml_content = "{}"
        config_file = tmp_path / "app_info.yaml"
        config_file.write_text(yaml_content)

        config = AppConfig.from_yaml(config_file)

        assert config.app_name == "VoxKit"
        assert config.version == "0.0.0"
        assert config.description == ""
        assert config.introduction == ""
        assert config.help_url == "http://localhost:3000/help"
        assert config.release_date is None
        assert config.release_notes is None

    def test_from_yaml_file_not_found(self, tmp_path):
        nonexistent_file = tmp_path / "nonexistent.yaml"

        with pytest.raises(FileNotFoundError) as exc_info:
            AppConfig.from_yaml(nonexistent_file)

        assert "not found" in str(exc_info.value)

    def test_from_yaml_partial_config(self, tmp_path):
        yaml_content = """
app_name: PartialApp
version: 0.1.0
"""
        config_file = tmp_path / "app_info.yaml"
        config_file.write_text(yaml_content)

        config = AppConfig.from_yaml(config_file)

        assert config.app_name == "PartialApp"
        assert config.version == "0.1.0"
        assert config.description == ""
        assert config.introduction == ""


class TestAppConfigLoadDefault:
    def test_load_default_returns_config(self):
        # This tests the actual config file in the project
        config = AppConfig.load_default()
        assert isinstance(config, AppConfig)
        assert config.app_name is not None
        assert config.version is not None

    def test_get_app_config_returns_config(self):
        config = get_app_config()
        assert isinstance(config, AppConfig)
        assert config.app_name is not None
