# engines/__init__.py
from __future__ import annotations

import importlib
import pkgutil
from typing import List

from .base import AlignmentEngine

# Import registry FIRST
from .register import _REGISTERED_ENGINES, register_engine


def _import_all_engines() -> None:
    print("[__init__] Discovering engine modules...")
    for finder, name, _ in pkgutil.iter_modules(__path__):
        if name.startswith("_") and name.endswith("_engine"):
            full_name = f"{__package__}.{name}"
            print(f"[__init__] → Importing {full_name}")
            try:
                importlib.import_module(full_name)
            except Exception as e:
                print(f"[__init__] Failed to import {full_name}: {e}")

# Run import
_import_all_engines()

# Define manager
class EngineManager:
    def list_engines(self) -> List[str]:
        keys = list(_REGISTERED_ENGINES.keys())
        print(f"[Manager] Registered engines: {keys}")
        return keys

    @staticmethod
    def get_engine(engine_id: str) -> AlignmentEngine:
        try:
            return _REGISTERED_ENGINES[engine_id]
        except KeyError:
            raise ValueError(f"No engine with id: {engine_id}")

# Export
ManageEngines = EngineManager()
print(f"[__init__] Final registry: {ManageEngines.list_engines()}")

__all__ = ["ManageEngines"]