"""Application configuration management.

This module provides functionality for loading and accessing application
metadata from the app_info.yaml configuration file.

The config system supports multiple profiles stored in config/profiles/<name>/.
The active profile is specified in config/profile.txt.
"""

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import yaml


def get_config_root() -> Path:
    """Get the path to the config root directory.

    Returns the correct config path whether running from source or as a
    PyInstaller bundle.

    Returns:
        Path to the config directory
    """
    # Check if running as PyInstaller bundle
    if getattr(sys, "_MEIPASS", None):
        # Running as bundled executable
        # mypy: ignore attr-defined on _MEIPASS - it's dynamically added by PyInstaller
        return Path(getattr(sys, "_MEIPASS")) / "config"
    else:
        # Running from source - get project root (3 levels up from this file)
        return Path(__file__).parent.parent.parent.parent / "config"


def get_active_profile() -> str:
    """Get the active configuration profile name.

    Reads from config/profile.txt. Falls back to 'default' if file doesn't exist.

    Returns:
        Profile name string
    """
    config_root = get_config_root()
    profile_file = config_root / "profile.txt"

    if profile_file.exists():
        return profile_file.read_text().strip()
    return "default"


def get_profile_config_path() -> Path:
    """Get the path to the active profile's config directory.

    Returns:
        Path to the active profile directory (e.g., config/profiles/default/)
    """
    config_root = get_config_root()
    profile = get_active_profile()
    profile_path = config_root / "profiles" / profile

    # Fall back to legacy location if profile doesn't exist
    if not profile_path.exists():
        return config_root

    return profile_path


def resolve_config_file(filename: str) -> Path:
    """Resolve a config file path with fallback to default profile.

    Looks for the file in the active profile first, then falls back to
    the default profile if not found. This allows profiles to only
    override the files they need to change.

    Args:
        filename: The config file name (e.g., "app_info.yaml")

    Returns:
        Path to the config file (from active profile or default)

    Raises:
        FileNotFoundError: If file not found in active or default profile
    """
    config_root = get_config_root()
    profile = get_active_profile()

    # Try active profile first
    active_path = config_root / "profiles" / profile / filename
    if active_path.exists():
        return active_path

    # Fall back to default profile
    default_path = config_root / "profiles" / "default" / filename
    if default_path.exists():
        return default_path

    # Fall back to legacy location (config root)
    legacy_path = config_root / filename
    if legacy_path.exists():
        return legacy_path

    raise FileNotFoundError(
        f"Config file '{filename}' not found in profile '{profile}', "
        f"default profile, or config root"
    )


# Legacy alias for backwards compatibility
def get_config_path() -> Path:
    """Get the path to the config directory.

    Deprecated: Use get_profile_config_path() for profile-aware loading,
    or get_config_root() for the config root directory.

    Returns:
        Path to the active profile's config directory
    """
    return get_profile_config_path()


@dataclass
class AppConfig:
    """Application configuration data class."""

    app_name: str
    version: str
    description: str
    introduction: str
    help_url: str = "https://voxkit-web.vercel.app/help"
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
            help_url=data.get("help_url", "https://voxkit-web.vercel.app/help"),
            release_date=data.get("release_date"),
            release_notes=data.get("release_notes"),
        )

    @classmethod
    def load_default(cls) -> "AppConfig":
        """Load the application configuration from the active profile.

        Loads from config/profiles/<active_profile>/app_info.yaml.
        Falls back to default profile or config root if not found.

        Returns:
            AppConfig instance
        """
        config_path = resolve_config_file("app_info.yaml")
        return cls.from_yaml(config_path)


def get_app_config() -> AppConfig:
    """Get the application configuration.

    Convenience function to load the default configuration.

    Returns:
        AppConfig instance
    """
    return AppConfig.load_default()
