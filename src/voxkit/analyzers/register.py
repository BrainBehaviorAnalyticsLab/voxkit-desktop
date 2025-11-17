"""
Dataset Analyzer registration system for VoxKit.

This module provides the :func:`register_analyzer` decorator which allows dataset analysis 
implementations to be registered in a global registry. The registry is populated at import time 
when analysis modules are loaded by the package initializer.
"""

from __future__ import annotations

from .base import DatasetAnalyzer

# Global registry
_REGISTERED_ANALYZERS: dict[str, DatasetAnalyzer] = {}

def register_analyzer(cls=None, *, author: str | None = None):
    """
    Decorator to register a DatasetAnalyzer subclass in the global registry.

    Args:
        cls: The analyzer class to register

    Returns:
        The original class, unmodified
        
    Raises:
        ValueError: If the class does not inherit from DatasetAnalyzer,
            or if an analyzer with the same ID is already registered.
    """

    def _register(c: type) -> type:
        print(f"[register] Registering {c.__name__} (author={author})")
        if not issubclass(c, DatasetAnalyzer):
            raise ValueError(f"{c.__name__} must inherit DatasetAnalyzer")

        analyzer_id = c.__name__.upper()
        if analyzer_id in _REGISTERED_ANALYZERS:
            raise ValueError(f"Analyzer {analyzer_id} already registered")

        instance = c()
        _REGISTERED_ANALYZERS[analyzer_id] = instance
        print(f"[register] → {analyzer_id} registered successfully")
        return c

    if cls is None:
        return _register
    return _register(cls)
