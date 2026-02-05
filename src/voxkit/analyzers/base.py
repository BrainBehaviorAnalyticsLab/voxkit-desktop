"""Analyzer Base Module.

Defines the abstract interface for dataset analyzers in VoxKit.

Creating a Custom Analyzer
--------------------------
To create a new analyzer:

1. Subclass ``DatasetAnalyzer``
2. Implement required properties: ``name``, ``description``
3. Implement the ``analyze`` method returning CSV-exportable data
4. Register the instance in ``voxkit.analyzers.__init__``

Example::

    class DurationAnalyzer(DatasetAnalyzer):
        @property
        def name(self) -> str:
            return "Duration"

        @property
        def description(self) -> str:
            return "Total audio duration per speaker"

        def analyze(self, dataset_path: str) -> List[Dict[str, Any]]:
            return [{"speaker_id": "spk1", "duration_seconds": 120.5}]
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Dict, List

if TYPE_CHECKING:
    from PyQt6.QtWidgets import QWidget


class DatasetAnalyzer(ABC):
    """Abstract base class for dataset analysis methods.

    Subclasses must implement the ``name`` and ``description`` properties and
    the ``analyze`` method which returns row dictionaries suitable for CSV
    export.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Display name for this analysis method.

        Returns:
            str: Human readable name used to register and select the analyzer.
        """

    @property
    @abstractmethod
    def description(self) -> str:
        """Short description of the analyzer's behavior.

        Returns:
            str: Brief description suitable for display in UI lists.
        """

    @abstractmethod
    def analyze(self, dataset_path: str) -> List[Dict[str, Any]]:
        """Analyze a dataset and return structured data for CSV export.

        Args:
            dataset_path (str): Path to the dataset root directory. The
                analyzer should inspect subdirectories and files below this
                path.

        Returns:
            List[Dict[str, Any]]: A list of dictionaries where each
            dictionary represents a single CSV row. Dictionary keys will be
            used as CSV column headers.
        """

    def visualize(self, data: List[Dict[str, Any]]) -> QWidget | None:
        """Return a QWidget visualizing the analysis data.

        Subclasses may override this method to provide a custom visualization
        widget. The default implementation returns ``None``, which signals
        the caller to fall back to a plain table view.

        Args:
            data: The analysis results as returned by :meth:`analyze`.

        Returns:
            A QWidget ready for embedding in a dialog, or ``None`` for the
            default table display.
        """
        return None
