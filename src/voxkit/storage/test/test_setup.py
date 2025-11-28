
import os
import shutil

from ..utils import get_storage_root


def activate_test_environment(engine_ids) -> None:
    """Activate the test environment by overriding storage paths."""
    import os
    os.environ["TESTING"] = "1"
    for engine_id in engine_ids:
        engine_root = get_storage_root() / engine_id
        engine_root.mkdir(parents=True, exist_ok=True)


def deactivate_test_environment() -> None:
    """Deactivate the test environment by resetting storage paths."""
    os.environ["TESTING"] = "1"
    if os.environ.get("TESTING") == "1":
        storage_root = get_storage_root()
        if storage_root.exists():
            shutil.rmtree(storage_root)

