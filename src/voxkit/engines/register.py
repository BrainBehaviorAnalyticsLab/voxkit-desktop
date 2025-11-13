# engines/register.py
from __future__ import annotations

from .base import AlignmentEngine

# Global registry
_REGISTERED_ENGINES: dict[str, AlignmentEngine] = {}

def register_engine(cls=None, *, author: str | None = None):
    """
    Register an AlignmentEngine subclass.
    Usage:
        @register_engine
        class MyEngine(...)

        @register_engine(author="name")
        class MyEngine(...)
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