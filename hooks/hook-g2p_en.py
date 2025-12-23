"""PyInstaller hook for g2p_en package.

g2p_en includes data files (checkpoint20.npz) that need to be bundled.
"""

from PyInstaller.utils.hooks import collect_data_files

# Collect all data files from g2p_en
datas = collect_data_files("g2p_en")
