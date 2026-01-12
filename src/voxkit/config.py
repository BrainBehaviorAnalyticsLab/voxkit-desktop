from typing import Callable, Literal

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

# Startup script configuration
# Set this to a callable function to run on first launch, or None to disable
STARTUP_SCRIPT: Callable[[], None] | None = None
