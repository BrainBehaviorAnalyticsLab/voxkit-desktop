"""
Models Manager Module handles model actions and retrieval in the scope of local storage
"""
from typing import TypedDict

from PyQt6.QtCore import QObject, pyqtSignal

from voxkit.engines import ENGINES_ALLOWED

from .paths import collect_models, scrub_training_run


class ModelMeta(TypedDict):
    path: str
    date: str
    time: str
    train_code: str

class ModelsManager(QObject): 
    """
    Manages the collection of models for all allowed engines
    """
    data_changed = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        self._data = {}
        self.refresh()

    def refresh(self, engine_id=None): 
        """
        Refresh the models list by rescanning local storage
        """
        if engine_id is None:
            for engine in ENGINES_ALLOWED:
                self._data[engine] = collect_models(engine)
        else:
            self._data[engine_id] = collect_models(engine_id)
        self.data_changed.emit(self._data)

    def get_data(self):
        return self._data

    def delete_model(self, engine_id, model_name): 
        """
        Erase a model from local storage and update internal state
        """
        if engine_id not in ENGINES_ALLOWED:
            raise ValueError("Invalid engine_id")
        for key in self._data:
            if key == engine_id:
                if model_name in self._data[key]:
                    train_code = self._data[key][model_name]["train_code"]
                    scrub_training_run(engine_id, train_code)
                    self._data[key].remove(model_name)
                    self.data_changed.emit(self._data)

