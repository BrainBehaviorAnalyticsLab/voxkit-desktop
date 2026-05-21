"""This module contains constants for the VoxKit storage layer.

Constants
---------
- **STORAGE_ROOT**: Root directory for all VoxKit storage (~/.voxkit)
- **MODELS_ROOT**: Subdirectory for model storage relative to engine directory
- **DATASETS_ROOT**: Subdirectory for dataset storage relative to STORAGE_ROOT
- **ALIGNMENTS_ROOT**: Subdirectory for alignments relative to dataset directory
- **SUPERSET_AUDIO_EXTENSIONS**: Comprehensive set of audio file extensions

Notes
-----
- STORAGE_ROOT uses tilde (~) notation to reference the user's home directory
- All paths are relative to appropriate parent directories in the hierarchy
"""

STORAGE_ROOT: str = "~/.voxkit"  # Root directory for all storage
MODELS_ROOT: str = "train"  # Path from STORAGE_ROOT to models
DATASETS_ROOT: str = "datasets"  # Path from STORAGE_ROOT to datasets
ALIGNMENTS_ROOT: str = "alignments"  # Path from STORAGE_ROOT/DATASETS_ROOT to alignments
SUPERSET_AUDIO_EXTENSIONS: set[str] = {".wav", ".flac", ".mp3", ".ogg", ".m4a"}
