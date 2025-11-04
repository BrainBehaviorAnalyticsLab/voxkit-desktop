from pathlib import Path
from PyQt6.QtWidgets import (
    QMessageBox
)

def validate_path(parent, path):
    """Validate if a path exists"""
    return Path(path).exists()
    
def validate_paths(parent, paths_dict):
    """Validate multiple paths and show error if any are invalid"""
    invalid_paths = []
    for label, path in paths_dict.items():
        if not validate_path(parent, path):
            invalid_paths.append(f"{label}: {path}")
    
    if invalid_paths:
        QMessageBox.warning(
            parent,
            "Invalid Paths",
            "The following paths do not exist:\n\n" + "\n".join(invalid_paths)
        )
        return False
    return True
