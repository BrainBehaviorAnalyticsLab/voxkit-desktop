"""VoxKit - Speech Analysis and Forced Alignment Toolkit.

VoxKit provides a unified interface for speech analysis and forced alignment,
integrating industry-standard tools like the Montreal Forced Aligner (MFA)
with extensible storage and analysis capabilities.

Subpackages
-----------
analyzers
    Dataset analysis implementations with auto-discovery and registration.
    Provides the `ManageAnalyzers` interface for runtime lookup of registered analyzers.

engines
    Speech toolkit integrations (MFA, W2TG) with auto-discovery and registration.
    Provides the `ManageEngines` interface for runtime lookup of registered engines.

storage
    Persistent storage for datasets, models, and alignments.
    CRUD operations with automatic filesystem initialization.

gui
    PyQt6-based graphical user interface for managing datasets, pipelines, and models.

config
    Application configuration constants and settings.

Quick Start
-----------
List available engines:

    >>> from voxkit.engines import engines
    >>> engines.list_engines()
    ['W2TGENGINE', 'MFAENGINE']

Get a specific engine:

    >>> engine = engines.get_engine('MFAENGINE')
    >>> engine.has_tool('align')
    True

Work with storage:

    >>> from voxkit import storage
    >>> dataset = storage.datasets.create_dataset(
    ...     name="My Dataset",
    ...     audio_path="/path/to/audio"
    ... )

Notes
-----
- Engine and analyzer modules use decorator-based registration
- Storage initialization occurs automatically on import
- All IDs use timestamp-based unique identifiers with microsecond precision
- See individual submodule documentation for detailed API references
"""

__version__ = "1.0.0"
__author__ = "Beckett Frey @beckettfrey.com"
