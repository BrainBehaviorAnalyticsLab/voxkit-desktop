from abc import ABC, abstractmethod


class AlignmentEngine(ABC):
    @abstractmethod
    def run_alignment(
            self, 
            audio_root, 
            output_root, 
            model_id, 
            settings: dict
        ):
        pass

    @abstractmethod
    def train_aligner(
            self, 
            audio_root, 
            textgrid_root, 
            model_id, 
            settings: dict
        ):
        pass

    

