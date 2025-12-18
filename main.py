import sys
import faulthandler
import os
import multiprocessing

# CRITICAL: Must be at the top for frozen apps using multiprocessing
if __name__ == "__main__":
    multiprocessing.freeze_support()

# Enable detailed crash reports
faulthandler.enable()

# Apply patches for frozen (PyInstaller) environment
if getattr(sys, 'frozen', False):
    import _frozen_patch
    
    # # Set Qt plugin path for PyInstaller bundle
    # bundle_dir = sys._MEIPASS
    # qt_plugins = os.path.join(bundle_dir, 'PyQt6', 'Qt6', 'plugins')
    # if os.path.exists(qt_plugins):
    #     os.environ['QT_PLUGIN_PATH'] = qt_plugins
    
    # # Also try the platform plugins specifically
    # platform_plugins = os.path.join(bundle_dir, 'PyQt6', 'Qt6', 'plugins', 'platforms')
    # if os.path.exists(platform_plugins):
    #     os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = platform_plugins

        # Define the minimal required environment
    minimal_env = {
        'HOME': os.environ.get('HOME') or os.path.expanduser('~'),
        'USER': os.environ.get('USER') or os.getlogin(),
        'TMPDIR': os.environ.get('TMPDIR') or '/tmp',
    }
    
    # Clear all environment variables
    os.environ.clear()
    
    # Set only the minimal required ones
    for key, value in minimal_env.items():
        if value:
            os.environ[key] = value

    

from gui import AlignmentGUI
from PyQt6.QtWidgets import QApplication
from voxkit.storage.utils import get_storage_root


def main():
    # Ensure required directories exist in storage root
    try:
        storage_root = get_storage_root()
        print(f"[INFO] Storage root: {storage_root}")
        
        (storage_root / "computed-likelihoods").mkdir(parents=True, exist_ok=True)
        (storage_root / "custom-likelihoods").mkdir(parents=True, exist_ok=True)
        print("[INFO] Created required directories")
    except Exception as e:
        print(f"[WARNING] Could not create directories: {e}")
        # Continue anyway - directories will be created on-demand if needed
    
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = AlignmentGUI()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    # Prevent multiprocessing from spawning new app windows in frozen builds
    multiprocessing.freeze_support()
    multiprocessing.set_start_method('spawn', force=True)
    main()
