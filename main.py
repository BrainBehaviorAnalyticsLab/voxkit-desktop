import sys
import faulthandler
import os
import multiprocessing

from voxkit.config.pipeline_config import PipelineConfig, PipelineStep, UIConfig, get_pipeline_config
from voxkit.config.app_config import AppConfig

# Disable Qt emoji support to prevent crashes in frozen builds


# CRITICAL: Must be at the top for frozen apps using multiprocessing
if __name__ == "__main__":
    multiprocessing.freeze_support()

# Enable detailed crash reports
faulthandler.enable()

# Apply patches for frozen (PyInstaller) environment
if getattr(sys, 'frozen', False):
    import _frozen_patch

    # Define the minimal required environment
    minimal_env = {
        'HOME': os.environ.get('HOME') or os.path.expanduser('~'),
        'USER': os.environ.get('USER') or os.getlogin(),
        'TMPDIR': os.environ.get('TMPDIR') or '/tmp',
        'QT_ENABLE_EMOJI': '0'
    }

    # PyInstaller-specific: Add Qt plugin paths
    if getattr(sys, '_MEIPASS', None):
        bundle_dir = sys._MEIPASS
        qt_plugins = os.path.join(bundle_dir, 'PyQt6', 'Qt6', 'plugins')
        if os.path.exists(qt_plugins):
            minimal_env['QT_PLUGIN_PATH'] = qt_plugins

        platform_plugins = os.path.join(bundle_dir, 'PyQt6', 'Qt6', 'plugins', 'platforms')
        if os.path.exists(platform_plugins):
            minimal_env['QT_QPA_PLATFORM_PLUGIN_PATH'] = platform_plugins

    # # Clear all environment variables
    # os.environ.clear()

    # Set the minimal required ones
    for key, value in minimal_env.items():
        if value:
            os.environ[key] = value



from gui import AlignmentGUI
from PyQt6.QtWidgets import QApplication
from voxkit.config import STARTUP_SCRIPT
from voxkit.gui.workers.startup import execute_startup_script
from pathlib import Path


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # Execute startup script on first launch (before GUI initialization)
    execute_startup_script(STARTUP_SCRIPT, app)

    app_config = None
    pipeline_config = None
    
    # Handle special '_MEIPASS' argument for frozen builds
    if getattr(sys, '_MEIPASS', None):
        app_config = AppConfig.from_yaml(
            Path(sys._MEIPASS) / "config" / "app_info.yaml"
        )
        pipeline_config = PipelineConfig.from_yaml(
            Path(sys._MEIPASS) / "config" / "pipeline_definitions.yaml"
        )

    window = AlignmentGUI(pipeline_config=pipeline_config, app_config=app_config)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    # Prevent multiprocessing from spawning new app windows in frozen builds
    multiprocessing.freeze_support()
    multiprocessing.set_start_method('spawn', force=True)
    main()
