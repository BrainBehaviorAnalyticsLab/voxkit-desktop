"""
voxkit.engines.base
===================

Base utilities and abstract interface for alignment engines.

This module provides a single abstract base class, AlignmentEngine, which
defines the contract that all alignment engines must implement.

Classes
-------
AlignmentEngine
    Abstract base class defining the required methods and common attributes.
"""

import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Literal

from voxkit.gui.frameworks.modal.generic import SettingsConfig

"""
A speech tool is a unit of compatible functionality present in an engine that can be used to perform
a specific task. Each engine can have no more than one of each type of tool, and each engine->tool 
has its own settings that are stored in a JSON file.
"""

ToolType = Literal["train", "align"]

class AlignmentEngine(ABC):
    """
    Abstract base class for alignment engines.

    Summary
    -------
    Defines the interface and common attributes for alignment engines. Subclasses
    must implement alignment, training, and settings update methods.

    Attributes
    ----------
    settings_configurations : dict[ToolType, SettingsConfig]
        A dictionary mapping tool types to their respective settings configurations.
    name : str
        Name of the engine, derived from the class name.
    reference_url : str | None
        Optional URL for reference documentation or resources.
    description : str | None
        Optional description of the engine's functionality.
    human_readable_name : str | None
        Optional human-readable name for the engine, defaults to the class name.
    id : str | None
        Optional unique identifier for the engine, defaults to the class name, use as folder name.
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

    class AlignmentEngineError(Exception):
        """Custom exception for alignment engine errors."""
        pass

    @abstractmethod
    def train_aligner(
        self,
        audio_root: Path,
        textgrid_root: Path, 
        base_model_id: str | None, 
        new_model_id: str
    ) -> None:
        """
        Train or fine-tune an alignment model.

        Parameters
        ----------
        audio_root : Path
            Directory containing training audio files.
        textgrid_root : Path
            Directory containing corresponding TextGrid files for training.
        base_model_id : str | None
            Identifier of the base model to use for training (e.g., a pre-trained model).
        new_model_id : str
            Identifier for the new model to be created after training.

        Returns
        -------
        None
        """
        pass
    
    
    @abstractmethod
    def _validate_train_settings(self, settings: dict) -> bool:
        """
        Validate the training settings.

        Parameters
        ----------
        settings : dict
            The training settings to validate.

        Returns
        -------
        bool
            True if the settings are valid, False otherwise.
        """
        pass


    @abstractmethod
    def _validate_align_settings(self, settings: dict) -> bool:
        """
        Validate the alignment settings.

        Parameters
        ----------
        settings : dict
            The alignment settings to validate.

        Returns
        -------
        bool
            True if the settings are valid, False otherwise.
        """
        pass

    
    def _save_json(self, data: dict, path: Path | str) -> None:
        """
        Save a dictionary as a JSON file to the specified path.

        Parameters
        ----------
        data : dict
            The data to save as JSON.
        path : Path | str
            The path where the JSON file will be saved.

        Returns
        -------
        None
        """
        if isinstance(path, str):
            path = Path(path)
        with open(path, "w") as f:
            json.dump(data, f, indent=4)
            

    def _load_json(self, path: Path | str) -> dict:
        """
        Load a JSON file from the specified path.

        Parameters
        ----------
        path : Path | str
            The path to the JSON file to load.

        Returns
        -------
        dict
            The contents of the JSON file as a dictionary.
        """
        if isinstance(path, str):
            path = Path(path)

        if not path.exists():
            raise FileNotFoundError(f"Settings file not found: {path}")
        
        with open(path, "r") as f:
            return json.load(f)
    
    
    def get_settings(self, tool_type: ToolType) -> dict: 
        """
        Retrieve the current settings from the respective tools json file.
        """
        if not self.has_tool(tool_type):
            raise ValueError(f"Tool type '{tool_type}' is not available in this engine.")
        if not self.settings_configurations[tool_type].store_path:
            raise FileNotFoundError(f"Settings path not given for tool type '{tool_type}' "
                                    f"in this engine.")
        if tool_type == "train":
            settings = self._load_json(self.settings_configurations[tool_type].store_path)
            if not self._validate_train_settings(settings):
                raise ValueError(f"Invalid training settings: {settings}")
            return settings
        elif tool_type == "align":
            settings = self._load_json(self.settings_configurations[tool_type].store_path)
            if not self._validate_align_settings(settings):
                raise ValueError(f"Invalid alignment settings: {settings}")
            return settings
        else:
            raise ValueError(f"Invalid tool_type: {tool_type}.")
    

    def get_settings_config(self, tool_type: ToolType) -> SettingsConfig:
        """
        Retrieve the settings configuration for the specified tool type.

        Parameters
        ----------
        tool_type : ToolType
            The type of tool for which to retrieve the settings configuration.

        Returns
        -------
        SettingsConfig
            The settings configuration for the specified tool type.
        """
        config = self.settings_configurations.get(tool_type, None)
        if config is None:
            raise ValueError(f"No settings configuration found for tool type: {tool_type}")
        return config
    
    def has_tool(self, tool_type: ToolType) -> bool:
        """
        Check if the engine has a tool of the specified type.
        """
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
    
