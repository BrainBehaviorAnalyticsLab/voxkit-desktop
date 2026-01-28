"""VoxKit Storage Module.

This module provides persistence and CRUD operations for VoxKit entities including
datasets, models, and alignments. It manages the hierarchical storage structure
and ensures data integrity across the application.

Storage Structure
-----------------
The storage system follows this hierarchy:

    ~/.voxkit/                          # STORAGE_ROOT
    ├── datasets/                       # Dataset storage
    │   ├── dataset_id_1/
    │   │   ├── voxkit_dataset.json    # Dataset metadata
    │   │   ├── alignments/            # Alignment outputs
    │   │   └── cache/                 # Optional cached dataset copy
    │   └── dataset_id_2/
    │       └── ...
    ├── engine_id_1/                   # Engine-specific storage
    │   ├── train/                     # Model storage
    │   │   ├── model_id_1/
    │   │   │   ├── voxkit_model.json # Model metadata
    │   │   │   ├── entrypoint.model  # Model file
    │   │   │   ├── data/             # Training data
    │   │   │   ├── eval/             # Evaluation results
    │   │   │   └── train/            # Training artifacts
    │   │   └── model_id_2/
    │   │       └── ...
    │   └── ...
    └── engine_id_2/
        └── ...

Submodules
----------
- **datasets**: Dataset CRUD operations and validation
- **models**: Model management and import/export
- **alignments**: Alignment creation and tracking
- **utils**: Utility functions for ID generation and path management
- **config**: Storage configuration constants

Usage
-----
    from voxkit.storage import datasets, models, alignments

    # Create a new dataset
    success, metadata = datasets.create_dataset(
        name="My Dataset",
        description="Training data",
        original_path="/path/to/data",
        cached=True,
        anonymize=False
    )

    # List available models
    model_list = models.list_models(engine_id="mfa")

    # Create an alignment
    success, alignment = alignments.create_alignment(
        dataset_id="20240101_120000_000000",
        engine_id="mfa",
        model_id="20240101_120000_000000"
    )

Notes
-----
- All IDs are unique timestamps with microsecond precision
- Storage root is automatically created on first access
- Failed operations automatically clean up partial changes
- All paths are managed using pathlib for cross-platform compatibility
"""

__author__ = "Beckett Frey"
__email__ = "beckett.frey@gmail.com"
__version__ = "0.0.1"


# Import utils but don't call get_storage_root() at module import time
from . import alignments, datasets, models, utils
from .alignments import AlignmentStatus


def _ensure_storage_root():
    """Ensure storage root directory exists. Called lazily when needed.

    Returns:
        Path: Path to the storage root directory

    Raises:
        Exception: If storage root cannot be created or accessed
    """
    try:
        from pathlib import Path

        storage_root = Path(utils.get_storage_root())
        if not storage_root.exists():
            storage_root.mkdir(parents=True, exist_ok=True)
        return storage_root
    except Exception as e:
        print(f"Error initializing storage root: {e}")
        raise e


_ensure_storage_root()

__all__ = [
    "alignments",
    "datasets",
    "models",
    "utils",
    "AlignmentStatus",
]
