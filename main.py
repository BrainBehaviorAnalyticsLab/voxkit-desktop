import sys
import faulthandler
import logging
import os
import multiprocessing

# Apply patches for frozen (PyInstaller) environment BEFORE other imports
if getattr(sys, 'frozen', False):
    import _frozen_patch

from voxkit.config.pipeline_config import PipelineConfig
from voxkit.config.app_config import AppConfig, get_app_config, get_profile_config_path
from voxkit.config.logging_config import setup_logging

# Minimal early config so frozen-env messages below are emitted before
# setup_logging() runs in main(); setup_logging() will reconfigure handlers.
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("voxkit.main")

# CRITICAL: Must be at the top for frozen apps using multiprocessing
if __name__ == "__main__":
    multiprocessing.freeze_support()

# Enable detailed crash reports
faulthandler.enable()

# Apply environment patches for frozen (PyInstaller) environment
if getattr(sys, 'frozen', False):
    # Define the minimal required environment
    minimal_env = {
        'HOME': os.environ.get('HOME') or os.path.expanduser('~'),
        'USER': os.environ.get('USER') or os.getlogin(),
        'TMPDIR': os.environ.get('TMPDIR') or '/tmp',
        'QT_ENABLE_EMOJI': '0'
    }

    # Add conda to PATH if available (required for MFA alignment)
    # Check common conda installation locations
    home = os.path.expanduser('~')
    conda_locations = [
        os.path.join(home, 'miniforge3', 'bin'),
        os.path.join(home, 'mambaforge', 'bin'),
        os.path.join(home, 'anaconda3', 'bin'),
        os.path.join(home, 'miniconda3', 'bin'),
        os.path.join(home, 'opt', 'anaconda3', 'bin'),
        os.path.join(home, 'opt', 'miniconda3', 'bin'),
    ]

    # Find first available conda installation
    conda_bin = None
    for location in conda_locations:
        if os.path.exists(os.path.join(location, 'conda')):
            conda_bin = location
            break

    # Build PATH with conda if found
    if conda_bin:
        existing_path = os.environ.get('PATH', '/usr/bin:/bin:/usr/sbin:/sbin')
        minimal_env['PATH'] = f"{conda_bin}:{existing_path}"
        log.info("[FROZEN] Added conda to PATH: %s", conda_bin)
    else:
        minimal_env['PATH'] = os.environ.get('PATH', '/usr/bin:/bin:/usr/sbin:/sbin')
        log.warning("[FROZEN] conda not found in standard locations. MFA alignment may fail.")

    # PyInstaller-specific: Add Qt plugin paths
    if getattr(sys, '_MEIPASS', None):
        bundle_dir = sys._MEIPASS
        qt_plugins = os.path.join(bundle_dir, 'PyQt6', 'Qt6', 'plugins')
        if os.path.exists(qt_plugins):
            minimal_env['QT_PLUGIN_PATH'] = qt_plugins
            minimal_env['QT_QPA_PLATFORM_PLUGIN_PATH'] = os.path.join(qt_plugins, 'platforms')

        # Additional Qt environment for frozen apps
        minimal_env['QT_AUTO_SCREEN_SCALE_FACTOR'] = '1'
        minimal_env['QT_LOGGING_RULES'] = '*.debug=false;qt.qpa.*=false'

        log.info("[FROZEN] Qt plugins directory: %s", qt_plugins)
        log.info("[FROZEN] Bundle directory: %s", bundle_dir)

    # IMPORTANT: Don't clear os.environ - preserve system environment
    # Just add/override our minimal required variables
    for key, value in minimal_env.items():
        if value:
            os.environ[key] = value

    log.info("[FROZEN] Environment configured for frozen app")

from PyQt6.QtWidgets import QApplication
from voxkit.config import STARTUP_SCRIPT
from voxkit.gui import VoxKitGUI
from voxkit.gui.workers.startup import execute_startup_script

def main():
    # Initialize logging as early as possible so startup work is captured.
    # Use config values when available; fall back to defaults otherwise.
    try:
        _cfg = get_app_config()
        setup_logging(
            max_bytes=_cfg.log_max_bytes,
            backup_count=_cfg.log_backup_count,
        )
    except Exception:
        setup_logging()

    # Attach the Qt-aware log handler so live viewers can subscribe.
    from voxkit.gui.components.log_handler import get_gui_log_handler
    get_gui_log_handler()

    log.info("VoxKit starting (frozen=%s)", bool(getattr(sys, "frozen", False)))

    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # Execute startup script on first launch (before GUI initialization)
    log.info("Running startup script")
    execute_startup_script(STARTUP_SCRIPT, app)

    app_config = None
    pipeline_config = None

    # Handle special '_MEIPASS' argument for frozen builds
    # Uses profile system - reads from config/profile.txt to determine active profile
    if getattr(sys, '_MEIPASS', None):
        profile_path = get_profile_config_path()
        app_config = AppConfig.from_yaml(profile_path / "app_info.yaml")
        pipeline_config = PipelineConfig.from_yaml(profile_path / "pipeline_definitions.yaml")

    window = VoxKitGUI(pipeline_config=pipeline_config, app_config=app_config)
    window.show()
    log.info("Main window shown, entering Qt event loop")
    sys.exit(app.exec())


if __name__ == "__main__":
    # Prevent multiprocessing from spawning new app windows in frozen builds
    multiprocessing.set_start_method('spawn', force=True)
    main()
