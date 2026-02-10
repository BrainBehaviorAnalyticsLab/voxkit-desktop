"""PyInstaller hook for pypllrcomputer package.

pypllrcomputer includes data files in the models directory (*.pkl files)
that need to be bundled.
"""

from PyInstaller.utils.hooks import collect_data_files

# Collect all data files from pypllrcomputer (includes models/*.pkl and .py files)
datas = collect_data_files("pypllrcomputer", include_py_files=True)
