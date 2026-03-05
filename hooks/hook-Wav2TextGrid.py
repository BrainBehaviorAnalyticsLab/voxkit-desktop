"""PyInstaller hook for Wav2TextGrid package.

Wav2TextGrid needs all its Python files bundled for proper operation.
"""

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# Collect all data files including Python source files
datas = collect_data_files("Wav2TextGrid", include_py_files=True)

# Ensure all submodules are collected as hidden imports
hiddenimports = collect_submodules("Wav2TextGrid")

print("[HOOK] hook-Wav2TextGrid.py executing...")
