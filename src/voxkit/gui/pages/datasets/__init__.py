"""Datasets Page Module.

UI for registering, validating, and managing speech datasets and their alignments.

API
---
- **DatasetsPage**: Main dataset management interface with alignment viewer

Notes
-----
- Datasets follow the MFA/Kaldi organization pattern
- Alignments are displayed per-dataset with engine filtering
- Supports import/export and HuggingFace dataset browsing (planned)
"""

from .datasets_page import DatasetsPage

__all__ = ["DatasetsPage"]
