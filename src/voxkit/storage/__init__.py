"""
VoxKit Storage Module
-----------

    This package contains modules for managing persistent storage of
    datasets, models, and alignments within the VoxKit framework.

Imports
-------
- datasets: CRUD operations for managing datasets.
- alignments: CRUD operations for managing dataset alignments.
- models: CRUD operations for managing models.

Notes
-----
- Filesystem initialization occurs on import.
- Add other storage-related modules here as needed.
"""

__author__ = "Beckett Frey"
__email__ = "beckett.frey@gmail.com"
__version__ = "0.0.1"


# Import utils but don't call get_storage_root() at module import time
from . import alignments, datasets, models, utils


def _ensure_storage_root():
    """Ensure storage root directory exists. Called lazily when needed."""
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
]
