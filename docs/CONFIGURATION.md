# VoxKit Configuration Guide

## Overview

VoxKit now supports flexible configuration through YAML files, allowing you to customize:
- Application metadata (name, version, description)
- Pipeline steps (which stackers to include and their order)
- UI settings (menu width, animation duration, spacing)

## Configuration Files

### 1. Application Configuration (`config/app_info.yaml`)

Defines application metadata and introduction text:

```yaml
app_name: "VoxKit"
version: "0.1.0"
description: "AI/ML Research -> Clinical Applications (Speech Pathology)"

introduction: |
  VoxKit is a comprehensive speech alignment and analysis toolkit...

release_date: "2026-01-14"
release_notes: |
  - Initial configurable release
  - Support for custom pipeline configurations
```

**Fields:**
- `app_name` (required): Name displayed in window title
- `version` (required): Version string
- `description` (required): Short description
- `introduction` (required): Multi-line introduction text for users
- `release_date` (optional): Release date
- `release_notes` (optional): Release notes

### 2. Pipeline Configuration (`config/pipeline_definitions.yaml`)

Defines pipeline steps and UI settings:

```yaml
pipeline:
  - id: "training"
    label: "Ⓐ  Train Aligners"
    stacker_class: "TrainingStacker"
    description: "Train custom alignment models on your datasets"
    enabled: true
    
  - id: "prediction"
    label: "Ⓑ  Predict Alignments"
    stacker_class: "PredictionStacker"
    description: "Generate forced alignments using trained models"
    enabled: true
    
  - id: "pllr"
    label: "Ⓒ  Extract GOP Scoring"
    stacker_class: "PLLRStacker"
    description: "Compute Goodness of Pronunciation scores"
    enabled: true

ui:
  menu_max_width: 500
  animation_duration: 300
  content_spacing: 20
```

**Pipeline Step Fields:**
- `id` (required): Unique identifier for the step
- `label` (required): Display text in navigation menu
- `stacker_class` (required): Class name from STACKER_REGISTRY
- `description` (required): Description of the step's purpose
- `enabled` (required): Whether to include this step (true/false)

**UI Fields:**
- `menu_max_width`: Maximum width of navigation menu in pixels
- `animation_duration`: Page transition animation duration in milliseconds
- `content_spacing`: Spacing between menu and content in pixels

## Available Stacker Classes

Currently registered stackers (defined in `src/voxkit/gui/pages/pipeline/__init__.py`):

```python
STACKER_REGISTRY = {
    "TrainingStacker": TrainingStacker,
    "PredictionStacker": PredictionStacker,
    "PLLRStacker": PLLRStacker,
}
```

To add a new stacker:
1. Create the stacker class in `src/voxkit/gui/pages/pipeline/`
2. Add it to `STACKER_REGISTRY`
3. Add a new step in `config/pipeline_definitions.yaml`

## Creating Custom Configurations

### Example: Research Version (No Training)

Create a version focused only on alignment and analysis:

```yaml
# config/pipeline_definitions.yaml
pipeline:
  - id: "prediction"
    label: "Generate Alignments"
    stacker_class: "PredictionStacker"
    description: "Generate forced alignments"
    enabled: true
    
  - id: "pllr"
    label: "Analyze Speech"
    stacker_class: "PLLRStacker"
    description: "Compute GOP scores"
    enabled: true
```

```yaml
# config/app_info.yaml
app_name: "VoxKit Research"
version: "0.1.0-research"
description: "Speech Analysis Research Tool"

introduction: |
  VoxKit Research Edition - Focused on alignment generation and 
  speech analysis for research applications.
```

### Example: Clinical Version (Full Pipeline)

For clinical applications with custom training:

```yaml
# config/pipeline_definitions.yaml
pipeline:
  - id: "training"
    label: "Train Models"
    stacker_class: "TrainingStacker"
    description: "Train on clinical speech data"
    enabled: true
    
  - id: "prediction"
    label: "Generate Alignments"
    stacker_class: "PredictionStacker"
    description: "Align clinical recordings"
    enabled: true
    
  - id: "pllr"
    label: "Clinical Assessment"
    stacker_class: "PLLRStacker"
    description: "Generate assessment reports"
    enabled: true
```

## Programmatic Usage

### Loading Configurations

```python
from voxkit.config import get_app_config, get_pipeline_config

# Load configurations
app_config = get_app_config()
pipeline_config = get_pipeline_config()

# Access app info
print(f"{app_config.app_name} v{app_config.version}")
print(app_config.introduction)

# Access pipeline steps
for step in pipeline_config.enabled_steps:
    print(f"{step.label}: {step.description}")

# Access UI settings
print(f"Menu width: {pipeline_config.ui_config.menu_max_width}px")
```

### Using in GUI Components

The `AlignmentGUI` class automatically loads and uses these configurations:

```python
class AlignmentGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Configurations are loaded automatically
        self.app_config = get_app_config()
        self.pipeline_config = get_pipeline_config()
        
        # Window title from config
        self.setWindowTitle(self.app_config.app_name)
        
        # Pipeline container uses config
        self.pipeline_container = PipelineContainer(
            self, 
            config=self.pipeline_config
        )
```

### Custom Configuration Paths

Load from custom locations:

```python
from pathlib import Path
from voxkit.config.app_config import AppConfig
from voxkit.config.pipeline_config import PipelineConfig

# Load from custom paths
app_config = AppConfig.from_yaml(Path("/path/to/app_info.yaml"))
pipeline_config = PipelineConfig.from_yaml(Path("/path/to/pipeline.yaml"))
```

## Architecture

### Configuration Flow

```
config/*.yaml
    ↓
voxkit.config.*_config.py (parse YAML)
    ↓
dataclass objects (AppConfig, PipelineConfig)
    ↓
gui.py (AlignmentGUI)
    ↓
PipelineFormStack (dynamic stacker creation)
```

### Key Classes

**`AppConfig`** (`src/voxkit/config/app_config.py`):
- Dataclass holding app metadata
- `from_yaml()` - Load from file
- `load_default()` - Load default config

**`PipelineConfig`** (`src/voxkit/config/pipeline_config.py`):
- Dataclass holding pipeline steps and UI config
- `enabled_steps` property - Filters enabled steps
- `from_yaml()` - Load from file
- `load_default()` - Load default config

**`PipelineStep`**:
- Dataclass for individual pipeline steps
- Maps to STACKER_REGISTRY entries

**`UIConfig`**:
- Dataclass for UI-related settings
- Provides defaults if not specified

## Validation

The system validates:
- YAML syntax errors (raises `yaml.YAMLError`)
- Missing configuration files (raises `FileNotFoundError`)
- Unknown stacker classes (raises `ValueError` with available options)
- Missing required fields in dataclasses (raises `TypeError`)

## Best Practices

1. **Version Control**: Keep separate config files for different deployments
2. **Documentation**: Document custom stacker classes in `STACKER_REGISTRY`
3. **Testing**: Test configuration changes before deployment
4. **Defaults**: Use `enabled: false` instead of removing steps (easier to re-enable)
5. **Descriptions**: Write clear descriptions for user-facing labels

## Troubleshooting

**Error: "Unknown stacker class 'XYZ'"**
- Check that the stacker class is registered in `STACKER_REGISTRY`
- Verify spelling matches exactly

**Error: "Pipeline config file not found"**
- Ensure `config/pipeline_definitions.yaml` exists in project root
- Check file path if using custom location

**Configuration not updating:**
- Restart the application (configs load at startup)
- Clear any cached `__pycache__` directories

## Future Enhancements

Potential additions to the configuration system:
- Environment-specific configs (dev, staging, production)
- Per-stacker configuration sections
- Plugin system for loading external stackers
- Configuration validation schemas
- Hot-reload without restart
