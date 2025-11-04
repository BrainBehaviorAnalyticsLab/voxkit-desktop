from PyQt6.QtCore import pyqtSignal, QObject
from .paths import list_modelz, delete_training_run


class ModelsManagerClass(QObject):
    data_changed = pyqtSignal(dict) 
    
    def __init__(self):
        super().__init__()
        self._data = {
            'W2TG Models': list_modelz('W2TG', True),
            'MFA Models': list_modelz('MFA', True)
        }
    
    def update(self, mode):
        if mode == 'W2TG':
            self._data['W2TG Models'] = list_modelz('W2TG', True)
        elif mode == 'MFA':
            self._data['MFA Models'] = list_modelz('MFA', True)

        self.data_changed.emit(self._data)
    
    def get_data(self):
        return self._data

    def delete_model(self, mode, model_name):
        for key in self._data:
            if mode in key:
                if model_name in self._data[key]:
                    delete_training_run(mode, self._data[key]['train_root'])
                    self._data[key].remove(model_name)
                    self.data_changed.emit(self._data)