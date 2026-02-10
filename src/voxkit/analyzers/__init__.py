"""VoxKit Analyzers Module.

Analyzers observe datasets and link metadata in flexible, abstract ways. They
extract structured information at registration time, producing CSV summaries
that can be visualized within VoxKit without rescanning the filesystem.

API
---
- **AnalyzerManager.list_analyzers**: List registered analyzer IDs
- **AnalyzerManager.get_analyzer**: Retrieve analyzer instance by ID
- **AnalyzerManager.get_analyzers**: Get all registered analyzers
- **DatasetAnalyzer**: Abstract base class for all analyzers

Available Analyzers
-------------------
**DefaultAnalyzer** (``default_analyzer.py``)
    Extracts speaker count and audio file counts per speaker directory.
    Includes a bar chart visualization for quick dataset overview.

Output Structure
----------------
Analyzer output is stored alongside dataset metadata::

    ~/.voxkit/datasets/{dataset_id}/
    ├── voxkit_dataset.json           # Dataset metadata
    ├── {analyzer_name}_summary.csv   # Analyzer output
    └── alignments/                   # Alignment outputs

Notes
-----
- Analyzers run during dataset registration
- Each analyzer's ``name`` property serves as its unique identifier
- Output is a list of dicts where keys become CSV column headers
- Custom visualizations can be provided via the ``visualize`` method
"""

from __future__ import annotations

from typing import List

from .base import DatasetAnalyzer
from .default_analyzer import DefaultAnalyzer


class AnalyzerManager:
    """
    Manager for registered dataset analyzers.

    Provides a unified interface to list and retrieve registered analyzer
    implementations.
    """

    def __init__(self, analyzers: dict[str, DatasetAnalyzer]):
        # Expect a mapping of id -> DatasetAnalyzer instance
        self._analyzers = analyzers

    def list_analyzers(self) -> List[str]:
        """Return a list of registered analyzer IDs."""
        keys = list(self._analyzers.keys())
        print(f"[AnalyzerManager] Registered analyzers: {keys}")
        return keys

    def get_analyzers(self) -> dict[str, DatasetAnalyzer]:
        """Return the registered analyzers mapping."""
        return self._analyzers

    def get_analyzer(self, analyzer_id: str) -> DatasetAnalyzer:
        """Return the registered analyzer instance for the given ID."""
        try:
            return self._analyzers[analyzer_id]
        except KeyError:
            raise ValueError(f"No analyzer with id: {analyzer_id}")


default_analyzer_instance = DefaultAnalyzer()
# Singleton instance for unified export/interface
ManageAnalyzers = AnalyzerManager({default_analyzer_instance.name: default_analyzer_instance})

__all__ = [
    "ManageAnalyzers",
    "AnalyzerManager",
    "DatasetAnalyzer",
    "DefaultAnalyzer",
]
