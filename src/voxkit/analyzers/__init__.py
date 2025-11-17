"""
VoxKit analyzer package
===============================

This module centralizes the integration points for lower-level dataset analysis
implementations used by VoxKit. It auto-discovers and imports analysis
implementation modules in this package so their registration side-effects run at
import time and exposes a small manager object, ``ManageAnalysis``, which
provides runtime lookup of registered analyzers.

The package will import modules matching the pattern ``*_analyzer.py`` so that
their decorators (which register analysis implementations) can execute and
populate the module-level registry.

The intended workflow for adding a new analysis implementation is:

1. Implement an analyzer subclass of :class:`voxkit.analyzers.base.DatasetAnalyzer`.
2. Annotate the implementation with the ``@register_analyzer`` decorator defined
	in :mod:`voxkit.analyzers.register` (the decorator supports both ``@register_analyzer``
	and ``@register_analyzer(author='name')`` forms).
3. Place the implementation module inside the ``voxkit.analyzers`` package. The package
 initializer will import analyzer modules matching the pattern ``*_analyzer.py`` so their 
 decorators execute and populate the global registry.
"""

from __future__ import annotations

import importlib
import pkgutil
from typing import List

from .base import DatasetAnalyzer
from .register import _REGISTERED_ANALYZERS


def _import_all_analyzers() -> None:
	"""
	Auto-import all analysis modules in the package to trigger their
	registration. Modules should be named ``*_analyzer.py``.
	"""
	print("[analyzer.__init__] Discovering analysis modules...")
	for finder, name, _ in pkgutil.iter_modules(__path__):
		print(f"[analyzer.__init__] Found module: {name}")
		if name.endswith("_analyzer"):
			full_name = f"{__package__}.{name}"
			print(f"[analyzer.__init__] → Importing {full_name}")
			try:
				importlib.import_module(full_name)
			except Exception as e:
				print(f"[analyzer.__init__] Failed to import {full_name}: {e}")


_import_all_analyzers()


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

# Singleton instance for unified export/interface
ManageAnalyzers = AnalyzerManager(_REGISTERED_ANALYZERS)

__all__ = ["ManageAnalyzers"]
