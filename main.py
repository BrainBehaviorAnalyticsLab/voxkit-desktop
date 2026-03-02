import sys
import faulthandler
import os
import multiprocessing

# Apply patches for frozen (PyInstaller) environment BEFORE other imports
if getattr(sys, 'frozen', False):
    import _frozen_patch

from voxkit.config.pipeline_config import PipelineConfig
from voxkit.config.app_config import AppConfig

# Disable Qt emoji support to prevent crashes in frozen builds


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
        print(f"[FROZEN] Added conda to PATH: {conda_bin}")
    else:
        minimal_env['PATH'] = os.environ.get('PATH', '/usr/bin:/bin:/usr/sbin:/sbin')
        print("[FROZEN] Warning: conda not found in standard locations. MFA alignment may fail.")

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
        
        print(f"[FROZEN] Qt plugins directory: {qt_plugins}")
        print(f"[FROZEN] Bundle directory: {bundle_dir}")

    # IMPORTANT: Don't clear os.environ - preserve system environment
    # Just add/override our minimal required variables
    for key, value in minimal_env.items():
        if value:
            os.environ[key] = value
            
    print("[FROZEN] Environment configured for frozen app")



from PyQt6.QtWidgets import QApplication
from voxkit.config import STARTUP_SCRIPT
from voxkit.gui import AlignmentGUI
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
