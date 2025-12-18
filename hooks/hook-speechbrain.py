"""PyInstaller hook for speechbrain package.

speechbrain needs to be extracted to the filesystem because code tries to access
the package directory directly. We force extraction by collecting as data files.
"""
import os
from pathlib import Path
from PyInstaller.utils.hooks import get_package_paths, collect_data_files

# Get speechbrain package location
pkg_base, pkg_dir = get_package_paths('speechbrain')

# Collect all Python files and data files as "datas" to force filesystem extraction
datas = []
for root, dirs, files in os.walk(pkg_dir):
    for file in files:
        if file.endswith(('.py', '.yaml', '.txt', '.json')):
            src = os.path.join(root, file)
            # Calculate relative path from package base
            rel_path = os.path.relpath(root, pkg_base)
            datas.append((src, rel_path))

# Also collect submodules as hidden imports so they're available for import
from PyInstaller.utils.hooks import collect_submodules
hiddenimports = collect_submodules('speechbrain')
