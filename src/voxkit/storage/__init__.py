# TODO : Docstring for storage package.

from .models_manager import ModelsManager
from .paths import (
    create_train_destination,
    get_storage_root,
    list_models,
    list_modelz,
)

ModelsManagerInstance = ModelsManager()
__all__ = [
    "get_storage_root",
    "list_models",
    "list_modelz",
    "create_train_destination",
    "ModelsManagerInstance",
]
