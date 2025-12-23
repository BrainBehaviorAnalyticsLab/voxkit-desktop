"""PyInstaller hook for pypllrcomputer package.

pypllrcomputer includes data files in the models directory (*.pkl files)
that need to be bundled.
"""

from PyInstaller.utils.hooks import collect_data_files

# Collect all data files from pypllrcomputer (includes models/*.pkl)
datas = collect_data_files("pypllrcomputer")
