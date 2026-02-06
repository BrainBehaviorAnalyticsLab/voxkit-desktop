import shutil
from pathlib import Path

from voxkit.storage.config import MODELS_ROOT

ENGINE_IDS = ["ENGINE_A", "ENGINE_B", "ENGINE_C"]


def activate_test_environment(storage_root, engine_ids=ENGINE_IDS) -> None:
    """Activate the test environment by overriding storage paths."""
    for engine_id in engine_ids:
        engine_root = storage_root / engine_id / MODELS_ROOT
        engine_root.mkdir(parents=True, exist_ok=False)


def deactivate_test_environment(storage_root) -> None:
    """Deactivate the test environment by resetting storage paths."""
    if storage_root.exists():
        shutil.rmtree(storage_root)


def mock_get_storage_root():
    return Path("./temp_test_storage_models")
