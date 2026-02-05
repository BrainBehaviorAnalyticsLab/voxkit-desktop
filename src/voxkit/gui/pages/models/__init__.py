"""Models Page Module.

UI for viewing, importing, exporting, and deleting alignment models across engines.

API
---
- **ManageAlignersWidget**: CategoricalTableWidget-based model management interface

Notes
-----
- Models are grouped by engine ID (MFA, W2TG, etc.)
- Supports HuggingFace model import via ImportModelDialog
- Uses categorical_table framework for consistent table UI
"""

from .models_page import ManageAlignersWidget

__all__ = ["ManageAlignersWidget"]
