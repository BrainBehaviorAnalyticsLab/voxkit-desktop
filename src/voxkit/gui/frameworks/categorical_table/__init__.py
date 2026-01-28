"""Categorical Table Framework.

Reusable table widget for displaying data grouped into navigable categories.

API
---
- **CategoricalTableWidget**: Table with category navigation, selection, and CRUD callbacks

Notes
-----
- Categories are navigated via Previous/Next buttons
- Supports single or multi-selection modes
- CRUD operations are delegated to callback functions
- Optional HuggingFace button integration
"""

from .categorical_table import CategoricalTableWidget

__all__ = ["CategoricalTableWidget"]
