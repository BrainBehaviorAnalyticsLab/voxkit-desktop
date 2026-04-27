"""This module provides access to configurable info about the application.

Configurations
--------------
- App config: application metadata and provenance (``app_config``).
- Pipeline config: pipeline steps and UI wiring (``pipeline_config``).
- Startup config: launch-time constants and defaults (``startup_config``).
- Logging config: rotating file logger setup (``logging_config``).

Only ``app_config`` and ``pipeline_config`` are dynamic post-build; they are
loaded from YAML files under the active profile and can change without a
rebuild. ``startup_config`` and ``logging_config`` are baked in at build time.

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
from voxkit.config.logging_config import (
    LOG_FILE,
    reset_logging,
    setup_logging,
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
    # Logging config
    "LOG_FILE",
    "setup_logging",
    "reset_logging",
]
