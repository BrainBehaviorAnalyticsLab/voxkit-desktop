import os
from pathlib import Path
from typing import Any, Dict, List

from .base import DatasetAnalyzer
from .register import register_analyzer


@register_analyzer(author="Beckett")
class DefaultAnalyzer(DatasetAnalyzer):
    """
    Default analyzer: extracts speaker and audio file counts per speaker.

    The analyzer expects the dataset to be organized as a directory where
    each subdirectory represents a speaker and contains audio files.
    """
    
    @property
    def name(self) -> str:
        return "Default"
    
    @property
    def description(self) -> str:
        return "Speaker count and audio files per speaker"
    
    def analyze(self, dataset_path: str) -> List[Dict[str, Any]]:
        """
        Return a list of rows with speaker id and audio file count.

        Args:
            dataset_path (str): Path to the dataset root directory.

        Returns:
            List[Dict[str, Any]]: Each dict contains ``speaker_id`` and
            ``audio_file_count``.
        """
        results = []
        audio_extensions = {'.wav', '.flac', '.mp3', '.ogg', '.m4a'}
        
        try:
            for entry in os.scandir(dataset_path):
                if entry.is_dir():
                    speaker_name = entry.name
                    audio_files = [
                        f for f in os.scandir(entry.path)
                        if f.is_file() and Path(f.name).suffix.lower() in audio_extensions
                    ]
                    
                    results.append({
                        'speaker_id': speaker_name,
                        'audio_file_count': len(audio_files)
                    })
        except Exception as e:
            print(f"Error analyzing dataset: {e}")
        
        return results
