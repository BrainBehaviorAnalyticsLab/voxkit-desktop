"""Storage Configuration.

This module contains configuration constants for the VoxKit storage system.

Constants
---------
- **STORAGE_ROOT**: Root directory for all VoxKit storage (~/.voxkit)
- **MODELS_ROOT**: Subdirectory for model storage relative to engine directory
- **DATASETS_ROOT**: Subdirectory for dataset storage relative to STORAGE_ROOT
- **ALIGNMENTS_ROOT**: Subdirectory for alignments relative to dataset directory

Notes
-----
- STORAGE_ROOT uses tilde (~) notation to reference the user's home directory
- All paths are relative to appropriate parent directories in the hierarchy
- The directory structure is created automatically on first use
"""

STORAGE_ROOT = "~/.voxkit"  # Root directory for all storage
MODELS_ROOT = "train"  # Path from STORAGE_ROOT to models
DATASETS_ROOT = "datasets"  # Path from STORAGE_ROOT to datasets
ALIGNMENTS_ROOT = "alignments"  # Path from STORAGE_ROOT/DATASETS_ROOT to alignments
