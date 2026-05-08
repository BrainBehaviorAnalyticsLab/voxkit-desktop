"""Analyzers observe datasets and link metadata. They
extract structured information at registration time (ingestion), producing CSV summaries
that can be visualized within VoxKit without rescanning the filesystem.

API
---
- **AnalyzerManager.list_analyzers**: List registered analyzer IDs
- **AnalyzerManager.get_analyzer**: Retrieve analyzer instance by ID
- **AnalyzerManager.get_analyzers**: Get all registered analyzers

Available Analyzers
-------------------
**DefaultAnalyzer**
    Extracts speaker count and audio file counts per speaker directory.
    Includes a bar chart visualization for quick dataset overview.

**ClipDurationStatisticsAnalyzer**
    Reads audio metadata to compute total, average, min, and max clip duration
    per speaker. Includes a bar chart visualization of total duration.

**AudioFormatProfileAnalyzer**
    Reads audio metadata to surface dominant sample rate, channel count, and
    flags files that deviate from the speaker's dominant format.

Output Structure
----------------
Analyzer output is stored alongside dataset metadata::

    ~/.voxkit/datasets/{dataset_id}/
    ├── voxkit_dataset.json           # Dataset metadata
    ├── {analyzer_name}_summary.csv   # Analyzer output
    └── alignments/                   # Alignment outputs

Notes
-----
- Analyzers run during dataset registration (ingestion)
- Each analyzer's ``name`` property serves as its unique identifier
- Output is a list of dicts where keys become CSV column headers
- Custom visualizations can be provided via the ``visualize`` method
"""

from __future__ import annotations

from typing import List

from .audio_format_profile import AudioFormatProfileAnalyzer
from .base import DatasetAnalyzer
from .clip_duration_statistics import ClipDurationStatisticsAnalyzer
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


_default = DefaultAnalyzer()
_duration = ClipDurationStatisticsAnalyzer()
_format = AudioFormatProfileAnalyzer()

# Singleton instance for unified export/interface
ManageAnalyzers = AnalyzerManager(
    {
        _default.name: _default,
        _duration.name: _duration,
        _format.name: _format,
    }
)

__all__ = [
    "ManageAnalyzers",
]
