"""PyInstaller hook for typeguard

Collects typeguard dependencies at build time.
"""

from __future__ import annotations

from PyInstaller.utils.hooks import collect_all

# Collect everything from typeguard
datas, binaries, hiddenimports = collect_all("typeguard")

# No excludedimports needed
excludedimports: list[str] = []
