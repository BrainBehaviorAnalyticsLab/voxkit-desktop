"""VoxKit Storage Module.

Persistence and CRUD operations for datasets, models, and alignments.

Submodules
----------
- **datasets**: Dataset CRUD and validation
- **models**: Model management and import/export
- **alignments**: Alignment creation and tracking
- **utils**: ID generation and path management

Storage Structure
-----------------
::

    ~/.voxkit/
    ├── datasets/{dataset_id}/
    │   ├── voxkit_dataset.json
    │   ├── alignments/{alignment_id}/
    │   └── cache/
    └── {engine_id}/train/{model_id}/
        ├── voxkit_model.json
        └── entrypoint.model

Notes
-----
- IDs are unique timestamps (YYYYMMDD_HHMMSS_ffffff)
- Storage root is created on first access
- Failed operations clean up partial changes
"""

__author__ = "Beckett Frey"
__email__ = "beckett.frey@gmail.com"
__version__ = "0.0.1"


# Import utils but don't call get_storage_root() at module import time
from . import alignments, datasets, models, utils
from .alignments import HAND_ALIGNMENT_SENTINEL, AlignmentStatus


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
    "HAND_ALIGNMENT_SENTINEL",
]
