"""
VoxKit engines package
======================

This module centralizes the integration points for lowerlevel speech toolkits (engines)
used by VoxKit. It performs two responsibilities:

- Auto-discovers and imports engine implementation modules in the package so
    that their registration side-effects run at import time.
- Exposes a small manager object, ``ManageEngines``, which provides runtime
    lookup of registered engines.

The intended workflow for adding a new engine implementation is:

1. Implement an engine subclass of :class:`voxkit.engines.base.AlignmentEngine`.
2. Annotate the implementation with the ``@register_engine`` decorator defined
     in :mod:`voxkit.engines.register` (the decorator supports both ``@register_engine``
     and ``@register_engine(author='name')`` forms).
3. Place the implementation module inside the ``voxkit.engines`` package. The
     package initializer will import engine modules matching the pattern
     ``*_engine.py`` so their decorators execute and populate the global
     registry.

Engine implementation notes
---------------------------

Each engine encapsulates a set of compatible units of functionality (tools), and a corresponding
configuration of type :class:`voxkit.gui.frameworks.settings_modal.SettingsConfig`
this config serves as both documentation and the settings interface for the engine. The settings
are stored in JSON files under the engine's storage directory.

Registration
------------

Engine modules should call the decorator at definition time. The package
initializer imports engine modules so the decorator runs automatically; the
decorator registers an instantiated engine object in the module-level
``_REGISTERED_ENGINES`` registry (mapping engine ID strings to engine
instances).

API (high level)
-----------------

- ``ManageEngines.list_engines()`` -> List[str]
        Returns the list of registered engine IDs.

- ``ManageEngines.get_engine(engine_id)`` -> AlignmentEngine
        Returns the registered engine instance for ``engine_id`` or raises
        ``ValueError`` if the engine is not found.

- ``ManageEngines.get_tool_providers(tool)`` -> dict[str, AlignmentEngine]
        Returns a mapping of engine IDs to engine instances that provide the specified tool type.
"""

from __future__ import annotations

from typing import List

from .base import AlignmentEngine, ToolType
from .mfa_engine import MFAEngine
from .w2tg_engine import W2TGEngine


class EngineManager:
    """
    Manager class for registered engines.

    Provides a unified interface to list and retrieve registered alignment engines.

    Methods:
        list_engines(): Return a list of registered engine IDs.
        get_engine(engine_id): Retrieve an engine by ID.
        get_tool_providers(tool): Return a list of engines that provide the specified tool type.
    """

    def __init__(self, engines: dict[str, AlignmentEngine]):
        self._engines = engines

    def list_engines(self) -> List[str]:
        """Return a list of registered engine IDs."""
        keys = list(self._engines.keys())
        print(f"[engines.__init__] Registered engines: {keys}")
        return keys

    def get_engine(self, engine_id: str) -> AlignmentEngine:
        """Return the registered engine instance for the given ID."""
        try:
            return self._engines[engine_id]
        except KeyError:
            raise ValueError(f"No engine with id: {engine_id}")

    def get_tool_providers(self, tool: ToolType) -> dict[str, AlignmentEngine]:
        """Return a list of engines that provide the specified tool type."""
        engines = {}
        for _, engine in self._engines.items():
            if engine.has_tool(tool):
                engines[engine.id] = engine
        return engines


# Singleton instance for unified export/interface
w2tg = W2TGEngine(id="W2TGENGINE")
mfa = MFAEngine(id="MFAENGINE")
engines = EngineManager({w2tg.id: w2tg, mfa.id: mfa})

__all__ = ["engines", "W2TGEngine", "MFAEngine", "AlignmentEngine", "ToolType"]
