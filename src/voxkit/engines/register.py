"""
Engine registration system for VoxKit.

This module provides the :func:`register_engine` decorator which allows
alignment engine implementations to be registered in a global registry.
The registry is populated at import time when engine modules are loaded
by the package initializer.

The registry enables runtime discovery and instantiation of engines by
their unique IDs, which are derived from the engine class name in uppercase.

The optional ``author`` parameter is recorded for attribution purposes.
"""

from __future__ import annotations

from .base import AlignmentEngine

# Global registry
_REGISTERED_ENGINES: dict[str, AlignmentEngine] = {}

def register_engine(cls=None, *, author: str | None = None):
    """
    Decorator to register an AlignmentEngine subclass in the global registry.

    This decorator supports both forms:
      - ``@register_engine`` (simple form)
      - ``@register_engine(author="name")`` (with author attribution)

    When used with parentheses, it returns a decorator function. When used
    without, it directly registers the provided class.

    The engine is registered under an ID derived from the class name in
    uppercase (e.g., ``MyEngine`` becomes ``MYENGINE``). The optional
    ``author`` parameter is recorded for attribution but does not affect
    functionality.

    Args:
        cls: The engine class to register, or ``None`` when used as a
            decorator factory.
        author: Optional author name for attribution.

    Returns:
        The original class, unmodified.

    Raises:
        ValueError: If the class does not inherit from AlignmentEngine,
            or if an engine with the same ID is already registered.
    """

    def _register(c: type) -> type:
        print(f"[register] Registering {c.__name__} (author={author})")
        if not issubclass(c, AlignmentEngine):
            raise ValueError(f"{c.__name__} must inherit AlignmentEngine")

        engine_id = c.__name__.upper()
        if engine_id in _REGISTERED_ENGINES:
            raise ValueError(f"Engine {engine_id} already registered")

        instance = c(id=engine_id)
        _REGISTERED_ENGINES[engine_id] = instance
        print(f"[register] → Registered as {engine_id}")
        return c

    if cls is None:
        return _register
    return _register(cls)