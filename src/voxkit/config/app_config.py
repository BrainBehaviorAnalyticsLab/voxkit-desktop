"""Application configuration management.

This module provides functionality for loading and accessing application
metadata from the app_info.yaml configuration file.
"""

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import yaml


def get_config_path() -> Path:
    """Get the path to the config directory.

    Returns the correct config path whether running from source or as a
    PyInstaller bundle.

    Returns:
        Path to the config directory
    """
    # Check if running as PyInstaller bundle
    if getattr(sys, "_MEIPASS", None):
        # Running as bundled executable
        return Path(sys._MEIPASS) / "config"  # type: ignore[attr-defined]
    else:
        # Running from source - get project root (3 levels up from this file)
        return Path(__file__).parent.parent.parent.parent / "config"


@dataclass
class AppConfig:
    """Application configuration data class."""

    app_name: str
    version: str
    description: str
    introduction: str
    help_url: str = "http://localhost:3000/help"
    release_date: Optional[str] = None
    release_notes: Optional[str] = None

    @classmethod
    def from_yaml(cls, config_path: Path) -> "AppConfig":
        """Load application configuration from YAML file.

        Args:
            config_path: Path to the app_info.yaml file

        Returns:
            AppConfig instance with loaded configuration

        Raises:
            FileNotFoundError: If config file doesn't exist
            yaml.YAMLError: If YAML parsing fails
        """
        if not config_path.exists():
            raise FileNotFoundError(f"App config file not found: {config_path}")

        with open(config_path, "r") as f:
            data = yaml.safe_load(f)

        return cls(
            app_name=data.get("app_name", "VoxKit"),
            version=data.get("version", "0.0.0"),
            description=data.get("description", ""),
            introduction=data.get("introduction", ""),
            help_url=data.get("help_url", "http://localhost:3000/help"),
            release_date=data.get("release_date"),
            release_notes=data.get("release_notes"),
        )

    @classmethod
    def load_default(cls) -> "AppConfig":
        """Load the default application configuration.

        Looks for config/app_info.yaml relative to the project root.

        Returns:
            AppConfig instance
        """
        # Get the project root (3 levels up from this file)
        project_root = Path(__file__).parent.parent.parent.parent
        config_path = project_root / "config" / "app_info.yaml"

        return cls.from_yaml(config_path)


def get_app_config() -> AppConfig:
    """Get the application configuration.

    Convenience function to load the default configuration.

    Returns:
        AppConfig instance
    """
    return AppConfig.load_default()
