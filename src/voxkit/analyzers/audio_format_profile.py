"""Audio Format Profile Analyzer.

Reads audio metadata (no decode) to surface sample rate and channel count
per speaker. Flags speakers with inconsistent formats across their files.

Output Columns
--------------
- **speaker_id**: Name of the speaker subdirectory
- **file_count**: Number of audio files scanned
- **dominant_sample_rate_hz**: Most common sample rate across the speaker's files
- **dominant_channels**: Most common channel count (1 = mono, 2 = stereo)
- **inconsistent_files**: Number of files that differ from the dominant sample rate
"""

import logging
import os
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List

from .base import DatasetAnalyzer

logger = logging.getLogger(__name__)


class AudioFormatProfileAnalyzer(DatasetAnalyzer):
    """Per-speaker audio format profile: sample rate, channels, and consistency."""

    @property
    def name(self) -> str:
        return "Audio Format Profile"

    @property
    def description(self) -> str:
        return "Sample rate, channel count, and format consistency per speaker"

    def analyze(self, dataset_path: str) -> List[Dict[str, Any]]:
        import torchaudio

        results = []
        audio_extensions = {".wav", ".flac", ".mp3", ".ogg", ".m4a"}

        try:
            for entry in os.scandir(dataset_path):
                if not entry.is_dir():
                    continue

                sample_rates: List[int] = []
                channels: List[int] = []
                for f in os.scandir(entry.path):
                    if not f.is_file() or Path(f.name).suffix.lower() not in audio_extensions:
                        continue
                    try:
                        info = torchaudio.info(f.path)
                        if info.sample_rate > 0:
                            sample_rates.append(info.sample_rate)
                            channels.append(info.num_channels)
                        else:
                            waveform, sr = torchaudio.load(f.path)
                            sample_rates.append(sr)
                            channels.append(waveform.shape[0])
                    except Exception as e:
                        logger.warning("Skipping %s: %s", f.path, e)

                if not sample_rates:
                    continue

                dominant_sr = Counter(sample_rates).most_common(1)[0][0]
                dominant_ch = Counter(channels).most_common(1)[0][0]
                inconsistent = sum(1 for sr in sample_rates if sr != dominant_sr)

                results.append(
                    {
                        "speaker_id": entry.name,
                        "file_count": len(sample_rates),
                        "dominant_sample_rate_hz": dominant_sr,
                        "dominant_channels": dominant_ch,
                        "inconsistent_files": inconsistent,
                    }
                )
        except Exception as e:
            print(f"Error analyzing dataset: {e}")

        return results
