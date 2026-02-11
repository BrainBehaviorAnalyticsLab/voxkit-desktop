import pytest

from voxkit.config.pipeline_config import (
    PipelineConfig,
    PipelineStep,
    UIConfig,
    get_pipeline_config,
)


class TestPipelineStep:
    def test_from_dict_basic(self):
        data = {
            "id": "step1",
            "label": "First Step",
            "stacker_class": "FirstStacker",
        }
        step = PipelineStep.from_dict(data)

        assert step.id == "step1"
        assert step.label == "First Step"
        assert step.stacker_class == "FirstStacker"
        assert step.enabled is True
        assert step.collapsible_sections is None
        assert step.markdown_content is None

    def test_from_dict_with_all_fields(self):
        data = {
            "id": "step2",
            "label": "Second Step",
            "stacker_class": "SecondStacker",
            "enabled": False,
            "collapsible_sections": {"Header": "Content"},
            "markdown_content": "# Markdown",
        }
        step = PipelineStep.from_dict(data)

        assert step.id == "step2"
        assert step.enabled is False
        assert step.collapsible_sections == {"Header": "Content"}
        assert step.markdown_content == "# Markdown"

    def test_from_dict_backwards_compatibility_description(self):
        data = {
            "id": "legacy_step",
            "label": "Legacy Step",
            "stacker_class": "LegacyStacker",
            "description": "Step description here",
        }
        step = PipelineStep.from_dict(data)

        assert step.collapsible_sections == {"Step Instructions": "Step description here"}

    def test_from_dict_backwards_compatibility_info(self):
        data = {
            "id": "legacy_step",
            "label": "Legacy Step",
            "stacker_class": "LegacyStacker",
            "info": "Additional info here",
        }
        step = PipelineStep.from_dict(data)

        assert step.collapsible_sections == {"Additional Info": "Additional info here"}

    def test_from_dict_backwards_compatibility_both(self):
        data = {
            "id": "legacy_step",
            "label": "Legacy Step",
            "stacker_class": "LegacyStacker",
            "description": "Step description",
            "info": "Additional info",
        }
        step = PipelineStep.from_dict(data)

        assert step.collapsible_sections == {
            "Step Instructions": "Step description",
            "Additional Info": "Additional info",
        }

    def test_from_dict_new_format_takes_precedence(self):
        data = {
            "id": "step",
            "label": "Step",
            "stacker_class": "Stacker",
            "collapsible_sections": {"Custom": "Custom content"},
            "description": "This should be ignored",
        }
        step = PipelineStep.from_dict(data)

        assert step.collapsible_sections == {"Custom": "Custom content"}


class TestUIConfig:
    def test_from_dict_none(self):
        config = UIConfig.from_dict(None)

        assert config.menu_max_width == 500
        assert config.animation_duration == 300
        assert config.content_spacing == 20

    def test_from_dict_empty(self):
        config = UIConfig.from_dict({})

        assert config.menu_max_width == 500
        assert config.animation_duration == 300
        assert config.content_spacing == 20

    def test_from_dict_custom_values(self):
        data = {
            "menu_max_width": 600,
            "animation_duration": 200,
            "content_spacing": 30,
        }
        config = UIConfig.from_dict(data)

        assert config.menu_max_width == 600
        assert config.animation_duration == 200
        assert config.content_spacing == 30

    def test_from_dict_partial_values(self):
        data = {"menu_max_width": 400}
        config = UIConfig.from_dict(data)

        assert config.menu_max_width == 400
        assert config.animation_duration == 300
        assert config.content_spacing == 20


class TestPipelineConfig:
    def test_enabled_steps_all_enabled(self):
        steps = [
            PipelineStep(id="s1", label="Step 1", stacker_class="S1", enabled=True),
            PipelineStep(id="s2", label="Step 2", stacker_class="S2", enabled=True),
        ]
        config = PipelineConfig(steps=steps, ui_config=UIConfig())

        assert len(config.enabled_steps) == 2

    def test_enabled_steps_some_disabled(self):
        steps = [
            PipelineStep(id="s1", label="Step 1", stacker_class="S1", enabled=True),
            PipelineStep(id="s2", label="Step 2", stacker_class="S2", enabled=False),
            PipelineStep(id="s3", label="Step 3", stacker_class="S3", enabled=True),
        ]
        config = PipelineConfig(steps=steps, ui_config=UIConfig())

        enabled = config.enabled_steps
        assert len(enabled) == 2
        assert enabled[0].id == "s1"
        assert enabled[1].id == "s3"

    def test_enabled_steps_none_enabled(self):
        steps = [
            PipelineStep(id="s1", label="Step 1", stacker_class="S1", enabled=False),
            PipelineStep(id="s2", label="Step 2", stacker_class="S2", enabled=False),
        ]
        config = PipelineConfig(steps=steps, ui_config=UIConfig())

        assert len(config.enabled_steps) == 0


class TestPipelineConfigFromYaml:
    def test_from_yaml_success(self, tmp_path):
        yaml_content = """
pipeline:
  - id: step1
    label: First Step
    stacker_class: FirstStacker
    enabled: true
  - id: step2
    label: Second Step
    stacker_class: SecondStacker
    enabled: false

ui:
  menu_max_width: 450
  animation_duration: 250
  content_spacing: 15
"""
        config_file = tmp_path / "pipeline.yaml"
        config_file.write_text(yaml_content)

        config = PipelineConfig.from_yaml(config_file)

        assert len(config.steps) == 2
        assert config.steps[0].id == "step1"
        assert config.steps[0].enabled is True
        assert config.steps[1].id == "step2"
        assert config.steps[1].enabled is False

        assert config.ui_config.menu_max_width == 450
        assert config.ui_config.animation_duration == 250
        assert config.ui_config.content_spacing == 15

    def test_from_yaml_empty_pipeline(self, tmp_path):
        yaml_content = """
pipeline: []
"""
        config_file = tmp_path / "pipeline.yaml"
        config_file.write_text(yaml_content)

        config = PipelineConfig.from_yaml(config_file)

        assert len(config.steps) == 0
        assert config.ui_config.menu_max_width == 500

    def test_from_yaml_no_ui_config(self, tmp_path):
        yaml_content = """
pipeline:
  - id: step1
    label: Step 1
    stacker_class: Stacker1
"""
        config_file = tmp_path / "pipeline.yaml"
        config_file.write_text(yaml_content)

        config = PipelineConfig.from_yaml(config_file)

        assert len(config.steps) == 1
        assert config.ui_config.menu_max_width == 500
        assert config.ui_config.animation_duration == 300

    def test_from_yaml_file_not_found(self, tmp_path):
        nonexistent = tmp_path / "nonexistent.yaml"

        with pytest.raises(FileNotFoundError) as exc_info:
            PipelineConfig.from_yaml(nonexistent)

        assert "not found" in str(exc_info.value)

    def test_from_yaml_with_collapsible_sections(self, tmp_path):
        yaml_content = """
pipeline:
  - id: step1
    label: Step 1
    stacker_class: Stacker1
    collapsible_sections:
      Instructions: "Do this first"
      Notes: "Important note"
"""
        config_file = tmp_path / "pipeline.yaml"
        config_file.write_text(yaml_content)

        config = PipelineConfig.from_yaml(config_file)

        assert config.steps[0].collapsible_sections == {
            "Instructions": "Do this first",
            "Notes": "Important note",
        }


class TestPipelineConfigLoadDefault:
    def test_load_default_returns_config(self):
        config = PipelineConfig.load_default()
        assert isinstance(config, PipelineConfig)
        assert isinstance(config.steps, list)
        assert isinstance(config.ui_config, UIConfig)

    def test_get_pipeline_config_returns_config(self):
        config = get_pipeline_config()
        assert isinstance(config, PipelineConfig)
