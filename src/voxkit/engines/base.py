"""
Base utilities and abstract interface for alignment engines.

This module defines the :class:`AlignmentEngine` abstract base class which
encapsulates the contract every alignment engine must implement to
integrate with VoxKit. The base class handles settings management.
Concrete engine implementations should subclass this base class and implement the required
methods for training and alignment, as well as specific validation criteria.

-------------
Create a subclass and register it with :mod:`voxkit.engines.register`::

    from voxkit.engines.base import AlignmentEngine
    from voxkit.engines.register import register_engine

    @register_engine(author="alice")
    class MyEngine(AlignmentEngine):
        ...

The package initializer imports engine modules so registration side-effects
execute at import time.
"""

import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Literal

from voxkit.gui.frameworks.settings_modal import SettingsConfig
from voxkit.storage.utils import get_storage_root

"""
A tool is a unit of compatible functionality present in an engine that can be used to perform
a specific task. Each engine can have no more than one of each type of tool, and each engine->tool
has its own settings that are stored in a JSON file.
"""

ToolType = Literal["train", "align"]


class AlignmentEngine(ABC):
    """
    Abstract base class for alignment engines.

    Subclasses must implement at least one ToolType operation and provide
    specific validation criteria.

    Attributes:
        settings_configurations (dict[ToolType, SettingsConfig]): Mapping of
            tool type names ("train"/"align") to their store configuration.
        reference_url (str | None): Optional reference URL for the engine.
        description (str | None): Human-readable description of the engine.
        human_readable_name (str | None): Friendly display name for the engine.
        id (str | None): Unique identifier used for storage and discovery.
    """

    def __init__(
        self,
        settings_configurations: dict[ToolType, SettingsConfig],
        reference_url: str | None = None,
        description: str | None = None,
        human_readable_name: str | None = None,
        id: str | None = None,
    ):
        self.settings_configurations = settings_configurations
        self.reference_url = reference_url
        self.description = description or (
            f"{self.__class__.__name__} is an alignment engine "
            "that can be used to process audio in various ways."
        )
        self.human_readable_name = human_readable_name or self.__class__.__name__
        self.id = id or self.__class__.__name__
        
    @abstractmethod
    def align(self, dataset_id: str, model_id: str) -> None:
        """
        Perform alignment on a dataset using a specified model.

        Implementations should process the dataset identified by
        ``dataset_id`` using the alignment model identified by
        ``model_id``.

        Args:
            dataset_id: Identifier of the dataset to align.
            model_id: Identifier of the alignment model to use.
        """
        raise NotImplementedError()
    
    @abstractmethod
    def train_aligner(
        self, audio_root: Path, textgrid_root: Path, base_model_id: str | None, new_model_id: str
    ) -> None:
        """
        Train or fine-tune an alignment model.

        Implementations should create a new model artifact identified by
        ``new_model_id`` using the training data located under ``audio_root``
        and ``textgrid_root``. If ``base_model_id`` is provided, it may be
        used to initialize weights from a pre-trained model.

        Args:
            audio_root: Directory containing training audio files.
            textgrid_root: Directory containing corresponding TextGrid files.
            base_model_id: Identifier of the base model to use for training,
                or ``None`` to train from scratch.
            new_model_id: Identifier for the new model to be created.
        """
        raise NotImplementedError()

    @abstractmethod
    def _validate_train_settings(self, settings: dict) -> bool:
        """
        Validate training settings for the engine.

        Args:
            settings: Dictionary of training settings loaded from JSON.

        Returns:
            True if the settings are considered valid for this engine,
            otherwise False.
        """
        raise NotImplementedError()

    @abstractmethod
    def _validate_align_settings(self, settings: dict) -> bool:
        """
        Validate alignment settings for the engine.

        Args:
            settings: Dictionary of alignment settings loaded from JSON.

        Returns:
            True if the settings are considered valid for this engine,
            otherwise False.
        """
        raise NotImplementedError()

    def _save_json(self, data: dict, path: Path | str) -> None:
        """
        Persist a dictionary to a JSON file.

        Args:
            data: The dictionary to serialize.
            path: Filesystem path (``Path`` or string) to write the JSON file to.
        """
        if isinstance(path, str):
            path = Path(path)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

    def _load_json(self, path: Path | str) -> dict:
        """
        Load and return JSON data from a file.

        Args:
            path: Filesystem path (``Path`` or string) to the JSON file.

        Returns:
            Parsed JSON as a dictionary.

        Raises:
            FileNotFoundError: If the file does not exist.
            JSONDecodeError: If the file contains invalid JSON.
        """
        if isinstance(path, str):
            path = Path(path)

        if not path.exists():
            raise FileNotFoundError(f"Settings file not found: {path}")

        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def get_settings(self, tool_type: ToolType) -> dict:
        """
        Load and validate settings for a specific tool.

        This method reads the JSON settings file defined by the engine's
        ``settings_configurations`` for the given ``tool_type``, validates the
        settings using the engine-provided validator, and returns the parsed
        settings dictionary.

        Args:
            tool_type: The tool type to retrieve settings for ("train" or
                "align").

        Returns:
            Parsed settings as a dictionary.

        Raises:
            ValueError: If the engine does not provide the requested tool or
                if the settings fail validation.
            FileNotFoundError: If the configured settings file path is missing.
        """
        if not self.has_tool(tool_type):
            raise ValueError(f"Tool type '{tool_type}' is not available in this engine.")

        cfg = self.settings_configurations[tool_type]
        if not cfg.store_file:
            raise FileNotFoundError(
                f"Settings path not given for tool type '{tool_type}' in this engine."
            )
        settings = self._load_json(Path(get_storage_root() + "/" + cfg.store_file))

        if tool_type == "train":
            if not self._validate_train_settings(settings):
                raise ValueError(f"Invalid training settings: {settings}")
            return settings
        elif tool_type == "align":
            if not self._validate_align_settings(settings):
                raise ValueError(f"Invalid alignment settings: {settings}")
            return settings
        else:
            raise ValueError(f"Invalid tool_type: {tool_type}.")

    def get_settings_config(self, tool_type: ToolType) -> SettingsConfig:
        """
        Return the :class:`SettingsConfig` for a tool type.

        Args:
            tool_type: The tool type to query.

        Returns:
            The settings configuration object.

        Raises:
            ValueError: If no configuration exists for the tool type.
        """
        config = self.settings_configurations.get(tool_type, None)
        if config is None:
            raise ValueError(f"No settings configuration found for tool type: {tool_type}")
        return config

    def has_tool(self, tool_type: ToolType) -> bool:
        """Check if the engine has a tool of the specified type."""
        return tool_type in self.settings_configurations

    def source(self) -> str:
        """Return the reference url to pay homage to the engine's source."""
        return self.reference_url or "No source URL provided."

    def name(self) -> str:
        """Return the human-readable name of the engine."""
        return self.human_readable_name

    def __str__(self):
        """Return the engine's description."""
        return f"{self.description}"
