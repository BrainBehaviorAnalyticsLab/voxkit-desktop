import time
from typing import Callable, Literal

from voxkit.storage.utils import get_storage_root

AppName = "VoxKit"
Dimensions = {"min_width": 200, "min_height": 800, "max_width": 500, "max_height": None}
Defaults = {
    "mode": "W2TGENGINE",
    "output_path": "/path/to/output",
    "audio_path": "/path/to/audio",
    "textgrid_path": "/path/to/textgrids",
    "num_epochs": 10,
}

Mode = Literal["MFAENGINE", "W2TGENGINE"]
HELP_URL = "http://localhost:3000/help"


def startup_routine():
    """Example startup routine to be executed on first launch."""
    print("[STARTUP] Initializing VoxKit...")
    time.sleep(1)  # Simulate initialization

    storage_root = get_storage_root()
    print(f"[STARTUP] Storage root: {storage_root}")

    print("[STARTUP] Creating required directories...")
    (storage_root / "computed-likelihoods").mkdir(parents=True, exist_ok=True)
    (storage_root / "custom-likelihoods").mkdir(parents=True, exist_ok=True)
    time.sleep(1)  # Simulate directory setup

    print("[STARTUP] Initialization complete!")


# Startup script configuration
# Set this to a callable function to run on first launch, or None to disable
STARTUP_SCRIPT: Callable[[], None] | None = startup_routine
