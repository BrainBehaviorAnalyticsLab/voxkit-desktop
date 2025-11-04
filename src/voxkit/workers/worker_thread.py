from PyQt6.QtCore import QThread, pyqtSignal

class WorkerThread(QThread):
    """Thread for running operations without blocking the UI"""
    finished = pyqtSignal(bool, str)  # success, message
    
    def __init__(self, operation_func):
        super().__init__()
        self.operation_func = operation_func
    
    def run(self):
        try:
            result = self.operation_func()
            self.finished.emit(True, result if result else "Operation completed successfully")
        except Exception as e:
            self.finished.emit(False, str(e))
