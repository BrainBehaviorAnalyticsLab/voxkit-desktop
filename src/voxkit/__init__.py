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

__version__ = "0.4.0"
__author__ = "Beckett Frey - code@beckettfrey.com"

# Import subpackages for pdoc discoverability (not re-exported in __all__)
from . import analyzers, config, engines, gui, storage

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
