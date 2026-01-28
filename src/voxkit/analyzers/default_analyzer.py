"""Default Analyzer Module.

Built-in analyzer that extracts speaker and audio file counts from datasets.

Output Columns
--------------
- **speaker_id**: Name of the speaker subdirectory
- **audio_file_count**: Number of audio files in that speaker's directory

Notes
-----
- Expects MFA-style directory structure with speaker subdirectories
- Supported audio formats: .wav, .flac, .mp3, .ogg, .m4a
"""

import os
from pathlib import Path
from typing import Any, Dict, List

from .base import DatasetAnalyzer


class DefaultAnalyzer(DatasetAnalyzer):
    """Default analyzer extracting speaker and audio file counts per speaker."""

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
        audio_extensions = {".wav", ".flac", ".mp3", ".ogg", ".m4a"}

        try:
            for entry in os.scandir(dataset_path):
                if entry.is_dir():
                    speaker_name = entry.name
                    audio_files = [
                        f
                        for f in os.scandir(entry.path)
                        if f.is_file() and Path(f.name).suffix.lower() in audio_extensions
                    ]

                    results.append(
                        {"speaker_id": speaker_name, "audio_file_count": len(audio_files)}
                    )
        except Exception as e:
            print(f"Error analyzing dataset: {e}")

        return results
