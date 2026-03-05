"""VoxKit configuration module.

This module provides access to application and pipeline configurations.

Profile System
--------------
Configs are organized into profiles under config/profiles/<name>/.
The active profile is specified in config/profile.txt.

Use get_active_profile() to check which profile is active.
Use get_profile_config_path() to get the path to the active profile's directory.
"""

from voxkit.config.app_config import (
    AppConfig,
    get_active_profile,
    get_app_config,
    get_config_root,
    get_profile_config_path,
    resolve_config_file,
)
from voxkit.config.pipeline_config import (
    PipelineConfig,
    PipelineStep,
    UIConfig,
    get_pipeline_config,
)
from voxkit.config.startup_config import (
    HELP_URL,
    STARTUP_SCRIPT,
    AppName,
    Defaults,
    Dimensions,
    Mode,
)

__all__ = [
    # Profile system
    "get_active_profile",
    "get_config_root",
    "get_profile_config_path",
    "resolve_config_file",
    # App config
    "AppConfig",
    "get_app_config",
    # Pipeline config
    "PipelineConfig",
    "PipelineStep",
    "UIConfig",
    "get_pipeline_config",
    # Startup config
    "HELP_URL",
    "AppName",
    "Dimensions",
    "Defaults",
    "Mode",
    "STARTUP_SCRIPT",
]
