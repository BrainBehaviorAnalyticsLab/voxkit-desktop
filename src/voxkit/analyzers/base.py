"""
voxkit.datasets.analysis.base
=================================

This module defines the base class for dataset analysis methods.
The public surface area includes:

- :class:`DatasetAnalyzer`: Abstract base class for dataset analysis methods. Subclasses must 
implement the ``name`` and ``description`` properties and the ``analyze`` method which returns 
row dictionaries suitable for CSV export.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List


class DatasetAnalyzer(ABC):
    """
    Abstract base class for dataset analysis methods.

    Subclasses must implement the ``name`` and ``description`` properties and
    the ``analyze`` method which returns row dictionaries suitable for CSV
    export.
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """
        Display name for this analysis method.

        Returns:
            str: Human readable name used to register and select the analyzer.
        """
    
    @property
    @abstractmethod
    def description(self) -> str:
        """
        Short description of the analyzer's behavior.

        Returns:
            str: Brief description suitable for display in UI lists.
        """
    
    @abstractmethod
    def analyze(self, dataset_path: str) -> List[Dict[str, Any]]:
        """
        Analyze a dataset and return structured data for CSV export.

        Args:
            dataset_path (str): Path to the dataset root directory. The
                analyzer should inspect subdirectories and files below this
                path.

        Returns:
            List[Dict[str, Any]]: A list of dictionaries where each
            dictionary represents a single CSV row. Dictionary keys will be
            used as CSV column headers.
        """


