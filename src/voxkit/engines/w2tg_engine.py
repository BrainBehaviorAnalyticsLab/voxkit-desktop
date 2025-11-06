from typing import TypedDict

from voxkit.storage.paths import create_train_destination, list_models
from Wav2TextGrid.wav2textgrid import align_dirs
from Wav2TextGrid.wav2textgrid_train import train_aligner

from .api import AlignmentEngine


class TrainerSettings(TypedDict):
    start_from_scratch: bool
    base_model: str = "pkadambi/Wav2TextGrid"
    tokenizer_id: str | None
    epochs: int
    use_gpu: bool

class AlignmentSettings(TypedDict):
    aligner_model: str | None
    use_speaker_adaptation: bool
    file_type: str | None
    use_gpu: bool

class W2TGEngine(AlignmentEngine):
    def run_alignment(
                self, 
                audio_root, 
                output_root, 
                settings: AlignmentSettings        
            ):
        models = list_models("W2TG", True)

        if settings.get('aligner_model') is None or settings.get('aligner_model') not in models.keys():
            print(f"Warning: Aligner model '{settings.get('aligner_model')}' not found. Using default settings.")
            
            align_dirs(
                wavfile_or_dir=audio_root,
                transcriptfile_or_dir=audio_root,
                outfile_or_dir=output_root,
                filetype=settings.get('file_type', "wav"),
                use_speaker_adaptation=False
            )
        else:
            align_dirs(
                wavfile_or_dir=audio_root,
                transcriptfile_or_dir=audio_root,
                outfile_or_dir=output_root,
                aligner_model=models[settings.get('aligner_model')],
                filetype=settings.get('file_type', "wav"),
                use_speaker_adaptation=settings.get('use_speaker_adaptation', False)
            )
        

    def train_aligner(self, audio_root, textgrid_root, model_id, settings: TrainerSettings):
        models = list_models("W2TG", True)
        data_path, model_path, root_path, eval_path = create_train_destination(model_id, 'W2TG')

        train_aligner(
            train_audio_dir=audio_root,
            train_textgrid_dir=textgrid_root,
            tokenizer_name=settings.get('tokenizer_id', "charsiu/tokenizer_en_cmu"),
            model_output_dir=model_path,
            tg_output_dir=model_path,
            model_name=models.get('base_model', "pkadambi/Wav2TextGrid"),
            dataset_dir=data_path,
            words_key="words",
            device="cuda" if settings.get('use_gpu', False) else "cpu",
            ntrain_epochs=settings.get('epochs', 50),
            phone_key="phones",
            has_eval_dataset=False,
            retrain=settings.get('start_from_scratch', False),
            download_nltk=True
        )