"""VoxKit - Speech Analysis and Forced Alignment Toolkit.

A desktop application bridging AI/ML research and clinical speech-language
pathology. Provides accessible interfaces to forced alignment engines and
flexible dataset analysis tools.

Subpackages
-----------
- **engines**: Speech toolkit backends (MFA, Faster-Whisper)
- **analyzers**: Dataset metadata extraction
- **storage**: Persistence for datasets, models, and alignments
- **gui**: PyQt6 desktop interface
- **config**: Application and pipeline configuration
"""

__version__ = "0.1.0"
__author__ = "Beckett Frey @beckettfrey.com"

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
