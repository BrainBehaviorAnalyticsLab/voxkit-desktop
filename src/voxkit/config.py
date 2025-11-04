from typing import Literal

AppName = "VoxKit"
Dimensions = {
    "min_width": 1100,
    "min_height": 800,
    "max_width": 200,
    "max_height": None
}
Defaults = {
    "mode": "MFA",
    "output_path": "/path/to/output",
    "audio_path": "/path/to/audio",
    "textgrid_path": "/path/to/textgrids",
}

Mode = Literal['MFA', 'W2TG']