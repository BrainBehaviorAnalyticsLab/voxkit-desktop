import csv

import pytest

from voxkit.config.app_config import AppConfig
from voxkit.config.pipeline_config import PipelineConfig, PipelineStep, UIConfig


@pytest.fixture
def app_config():
    """Minimal AppConfig for GUI tests that don't need real config files."""
    return AppConfig(
        app_name="VoxKit Test",
        version="0.0.0-test",
        description="Test instance",
        introduction="Test intro",
        help_url="https://example.com/help",
    )


@pytest.fixture
def pipeline_config():
    """Minimal PipelineConfig with no steps (avoids loading real stackers)."""
    return PipelineConfig(steps=[], ui_config=UIConfig())


@pytest.fixture
def pipeline_config_with_steps():
    """PipelineConfig with a single markdown step for integration tests."""
    step = PipelineStep(
        id="test_step",
        label="Test Step",
        stacker_class="MarkdownStacker",
        enabled=True,
        markdown_content="# Hello\nTest content.",
    )
    return PipelineConfig(steps=[step], ui_config=UIConfig())


@pytest.fixture
def sample_csv(tmp_path):
    """Create a temporary CSV file and return its path."""
    csv_path = tmp_path / "test_data.csv"
    rows = [
        {"name": "Alice", "age": "30", "city": "New York"},
        {"name": "Bob", "age": "25", "city": "Los Angeles"},
        {"name": "Charlie", "age": "35", "city": "Chicago"},
    ]
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["name", "age", "city"])
        writer.writeheader()
        writer.writerows(rows)
    return str(csv_path)


@pytest.fixture
def empty_csv(tmp_path):
    """Create an empty CSV file and return its path."""
    csv_path = tmp_path / "empty.csv"
    csv_path.touch()
    return str(csv_path)


@pytest.fixture
def missing_csv(tmp_path):
    """Return a path to a CSV file that does not exist."""
    return str(tmp_path / "does_not_exist.csv")
