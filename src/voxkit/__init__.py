"""Modules for VoxKit; Provides accessible interfaces to forced alignment engines and
flexible dataset analysis and management tools.

Subpackages
-----------
- **engines**: Speech toolkit backends (MFA, W2TG. FasterWhisper, etc.)
- **analyzers**: Dataset metadata extraction
- **storage**: Persistence for datasets, models, and alignments
- **gui**: PyQt6 desktop interface
- **config**: Application and pipeline configuration
"""

import sys
from pathlib import Path

# Import subpackages for pdoc discoverability (not re-exported in __all__)
from . import analyzers, config, engines, gui, storage


def _read_version() -> str:
    if getattr(sys, "_MEIPASS", None):
        root = Path(getattr(sys, "_MEIPASS")) / "config"
    else:
        root = Path(__file__).resolve().parents[2] / "config"
    return (root / "VERSION").read_text(encoding="utf-8").strip()


__version__ = _read_version()
__author__ = "Beckett Frey - code@beckettfrey.com"

__all__ = [
    "__version__",
    "__author__",
    # Subpackages (for pdoc navigation, not deep re-exports)
    "analyzers",
    "config",
    "engines",
    "gui",
    "storage",
]
