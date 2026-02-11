"""PyInstaller hook for g2p_en package.

g2p_en includes data files (checkpoint20.npz, homographs.en) that need to be bundled.
"""

from PyInstaller.utils.hooks import collect_data_files, get_package_paths

# Collect all data files from g2p_en
datas = collect_data_files("g2p_en", include_py_files=False)

# If collect_data_files doesn't work, manually specify critical files
if not datas:
    import os

    pkg_base, pkg_dir = get_package_paths("g2p_en")
    datas = [
        (os.path.join(pkg_dir, "checkpoint20.npz"), "g2p_en"),
        (os.path.join(pkg_dir, "homographs.en"), "g2p_en"),
    ]
