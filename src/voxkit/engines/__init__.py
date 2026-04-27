"""Engines are speech toolkit backends. Each engine provides one or more tools
where each tool is a unit of functionality (e.g. alignment, training, transcription).

API
---
- **EngineManager.list_engines**: List registered engine IDs
- **EngineManager.get_engine**: Retrieve engine instance by ID
- **EngineManager.get_tool_providers**: Get engines providing a specific tool type
- **ToolType**: Literal type for compatible tool types

Available Engines
-----------------
**MFAEngine**
    Montreal Forced Aligner integration. Provides alignment using pretrained
    acoustic models and training via model adaptation.
    Tools: ``alignment``, ``training``

**W2TGEngine**
    Wav2TextGrid integration using Wav2Vec 2.0 models.
    Tools: ``alignment``, ``training``

**FasterWhisperEngine**
    Faster-Whisper integration for transcription. Produces .lab transcript files
    from audio using CTranslate2 backend.
    Tools: ``transcription``

Storage Structure
-----------------
Engine settings and models are stored under the engine's directory::

    ~/.voxkit/{engine_id}/
    ├── aligner/
    │   └── aligner_settings.json
    ├── train/
    │   ├── trainer_settings.json
    │   └── {model_id}/
    └── transcribe/
        └── transcriber_settings.json

Notes
-----
- Each engine's ``id`` property serves as its unique identifier
- Tools are configured via ``SettingsConfig`` objects with UI field definitions
- Settings are persisted to JSON and validated before use
"""

from __future__ import annotations

from typing import List

from .base import AlignmentEngine, ToolType
from .faster_whisper_engine import FasterWhisperEngine
from .mfa_engine import MFAEngine
from .w2tg_engine import W2TGEngine


class EngineManager:
    """
    Manager class for registered engines.

    Provides a unified interface to list and retrieve engines.

    Methods:
        list_engines(): Return a list of registered engine IDs.
        get_engine(engine_id): Retrieve an engine by ID.
        get_tool_providers(tool): Return a list of engines that provide the specified tool type.
    """

    def __init__(self, engines: dict[str, AlignmentEngine]):
        self._engines = engines

    def list_engines(self) -> List[str]:
        """Return a list of registered engine IDs."""
        keys = list(self._engines.keys())
        print(f"[engines.__init__] Registered engines: {keys}")
        return keys

    def get_engine(self, engine_id: str) -> AlignmentEngine:
        """Return the registered engine instance for the given ID."""
        try:
            return self._engines[engine_id]
        except KeyError:
            raise ValueError(f"No engine with id: {engine_id}")

    def get_tool_providers(self, tool: ToolType) -> dict[str, AlignmentEngine]:
        """Return a list of engines that provide the specified tool type."""
        engines = {}
        for _, engine in self._engines.items():
            if engine.has_tool(tool):
                engines[engine.id] = engine
        return engines


# Singleton instance for unified export/interface
w2tg = W2TGEngine(id="W2TGENGINE")
mfa = MFAEngine(id="MFAENGINE")
faster_whisper = FasterWhisperEngine(id="FASTERWHISPERENGINE")
engines = EngineManager({mfa.id: mfa, faster_whisper.id: faster_whisper, w2tg.id: w2tg})

__all__ = ["engines", "ToolType"]
