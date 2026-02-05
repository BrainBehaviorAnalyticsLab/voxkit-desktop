"""Pipeline configuration management.

This module provides functionality for loading and accessing pipeline
configuration from the pipeline_definitions.yaml file.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


@dataclass
class PipelineStep:
    """Represents a single step in the pipeline."""

    id: str
    label: str
    stacker_class: str
    enabled: bool = True
    collapsible_sections: Optional[Dict[str, str]] = None  # {header: content} pairs
    markdown_content: Optional[str] = None  # For MarkdownStacker

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PipelineStep":
        """Create a PipelineStep from a dictionary.

        Args:
            data: Dictionary containing step configuration

        Returns:
            PipelineStep instance
        """
        # Handle both old format (description/info) and new format (collapsible_sections)
        collapsible_sections = data.get("collapsible_sections")

        # Backwards compatibility: convert old description/info fields to collapsible_sections
        if collapsible_sections is None and ("description" in data or "info" in data):
            collapsible_sections = {}
            if "description" in data and data["description"]:
                collapsible_sections["Step Instructions"] = data["description"]
            if "info" in data and data["info"]:
                collapsible_sections["Additional Info"] = data["info"]

        return cls(
            id=data["id"],
            label=data["label"],
            stacker_class=data["stacker_class"],
            enabled=data.get("enabled", True),
            collapsible_sections=collapsible_sections,
            markdown_content=data.get("markdown_content"),
        )


@dataclass
class UIConfig:
    """UI-related configuration."""

    menu_max_width: int = 500
    animation_duration: int = 300
    content_spacing: int = 20

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> "UIConfig":
        """Create a UIConfig from a dictionary.

        Args:
            data: Dictionary containing UI configuration or None

        Returns:
            UIConfig instance with values from dict or defaults
        """
        if data is None:
            return cls()

        return cls(
            menu_max_width=data.get("menu_max_width", 500),
            animation_duration=data.get("animation_duration", 300),
            content_spacing=data.get("content_spacing", 20),
        )


@dataclass
class PipelineConfig:
    """Pipeline configuration data class."""

    steps: List[PipelineStep]
    ui_config: UIConfig

    @property
    def enabled_steps(self) -> List[PipelineStep]:
        """Get only the enabled pipeline steps.

        Returns:
            List of enabled PipelineStep instances
        """
        return [step for step in self.steps if step.enabled]

    @classmethod
    def from_yaml(cls, config_path: Path) -> "PipelineConfig":
        """Load pipeline configuration from YAML file.

        Args:
            config_path: Path to the pipeline_definitions.yaml file

        Returns:
            PipelineConfig instance with loaded configuration

        Raises:
            FileNotFoundError: If config file doesn't exist
            yaml.YAMLError: If YAML parsing fails
        """
        if not config_path.exists():
            raise FileNotFoundError(f"Pipeline config file not found: {config_path}")

        with open(config_path, "r") as f:
            data = yaml.safe_load(f)

        # Parse pipeline steps
        steps = []
        for step_data in data.get("pipeline", []):
            steps.append(PipelineStep.from_dict(step_data))

        # Parse UI config
        ui_config = UIConfig.from_dict(data.get("ui"))

        return cls(steps=steps, ui_config=ui_config)

    @classmethod
    def load_default(cls) -> "PipelineConfig":
        """Load the default pipeline configuration.

        Looks for config/pipeline_definitions.yaml relative to the project root.

        Returns:
            PipelineConfig instance
        """
        # Get the project root (3 levels up from this file)
        project_root = Path(__file__).parent.parent.parent.parent
        config_path = project_root / "config" / "pipeline_definitions.yaml"

        return cls.from_yaml(config_path)


def get_pipeline_config() -> PipelineConfig:
    """Get the pipeline configuration.

    Convenience function to load the default configuration.

    Returns:
        PipelineConfig instance
    """
    return PipelineConfig.load_default()
