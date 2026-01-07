"""Model Management Module.

Specialized CRUD operations for managing models within the VoxKit storage system.

Directory Structure
-------------------
Each model follows a hierarchical structure:

    chosen_engine/
    ├── train/
    │   ├── model_id_1/
    │   │   ├── entrypoint.model      # Model file
    │   │   ├── data/                 # Data directory
    │   │   ├── eval/                 # Evaluation directory
    │   │   ├── train/                # Training directory
    │   │   └── voxkit_model.json     # Model metadata
    │   ├── model_id_2/
    │   │   └── ...
    │   └── ...

API
---
- **create_model**: Create a new model entry in storage
- **get_model_metadata**: Retrieve metadata for a specific model
- **update_model_metadata**: Update the status or details of an existing model
- **list_models**: List all models for a given engine
- **delete_model**: Remove a model from storage
- **import_models**: Import models from an external directory

Notes
-----
- All paths are managed using pathlib
- Engine-specific branching may be necessary to bridge different model formats
- Error handling only exposes user-friendly messages
- Model IDs are generated using unique timestamps with microsecond precision
"""

import json
import shutil
from pathlib import Path
from typing import Literal, Tuple, TypedDict

from voxkit.storage.utils import generate_unique_id, get_storage_root, readable_from_unique_id

from .config import MODELS_ROOT


class ModelMetadata(TypedDict):
    name: str
    engine_id: str
    model_path: Path
    data_path: Path
    eval_path: Path
    train_path: Path
    download_date: str
    id: str


def _get_model_root(engine_id: str, model_id: str) -> Path | None:
    """Get the root directory for a specific model.

    Args:
        engine_id: Identifier of the engine the model belongs to
        model_id: Identifier of the model

    Returns:
        Path to the model root directory or None if not found
    """
    model_root = Path(f"{get_storage_root()}/{engine_id}/{MODELS_ROOT}/{model_id}")
    if model_root.exists():
        return model_root
    return None


def _get_models_root(engine_id: str) -> Path | None:
    """Get the root directory for storing models for a given engine.

    Args:
        engine_id: Identifier of the engine

    Returns:
        Path to the models root directory or None if not found
    """
    models_root = Path(f"{get_storage_root()}/{engine_id}/{MODELS_ROOT}")
    if models_root.exists():
        return models_root
    return None


def create_model(
    engine_id: str, model_name: str
) -> tuple[Literal[True], ModelMetadata] | tuple[Literal[False], str]:
    """Create a new model entry in the storage.

    Args:
        engine_id: Identifier of the engine the model belongs to
        model_name: Human-readable name for the model

    Returns:
        Tuple of (True, ModelMetadata) on success or (False, error_message) on failure
    """

    engine_models_root = Path(f"{get_storage_root()}/{engine_id}/{MODELS_ROOT}")
    if not engine_models_root.exists():
        return False, f"Unsupported engine_id: {engine_id}"

    now = generate_unique_id()
    model_root = Path(f"{engine_models_root}/{now}")
    print(f"Creating model at: {model_root}")

    try:
        model_path = model_root / "entrypoint.model"
        data_path = model_root / "data"
        eval_path = model_root / "eval"
        train_path = model_root / "train"

        humandate = readable_from_unique_id(now)
        model_metadata = ModelMetadata(
            name=model_name or f"Model_{now}",
            engine_id=engine_id,
            model_path=model_path.with_suffix(".model"),
            data_path=data_path,
            eval_path=eval_path,
            train_path=train_path,
            download_date=humandate,
            id=now,
        )

        # Create model directories
        model_path.mkdir(parents=True, exist_ok=False)
        data_path.mkdir(parents=True, exist_ok=False)
        eval_path.mkdir(parents=True, exist_ok=False)
        train_path.mkdir(parents=True, exist_ok=False)
        metadata_path = model_root / "voxkit_model.json"

        # Convert Path objects to strings for JSON serialization
        json_metadata = {k: str(v) if isinstance(v, Path) else v for k, v in model_metadata.items()}

        # Create metadata file and write metadata
        with open(metadata_path, "w") as f:
            json.dump(json_metadata, f, indent=4)

        return True, model_metadata

    except Exception as e:
        print(f"Exception occurred during model creation: {e}")
        # Clean up partially created model directory
        if model_root and model_root.exists():
            shutil.rmtree(model_root)

        return False, "Failed to create model metadata."


def update_model_metadata(engine_id: str, model_id: str, updates: dict) -> Tuple[bool, str]:
    """Update metadata for an existing model.

    Args:
        engine_id: Identifier of the engine the model belongs to
        model_id: Identifier of the model to update
        updates: Dictionary of fields to update in the model metadata

    Returns:
        Tuple of (True, success_message) on success or (False, error_message) on failure
    """
    model_root = _get_model_root(engine_id, model_id)
    if not model_root:
        return False, f"Model '{model_id}' for engine '{engine_id}' not found"

    metadata_path = Path(model_root) / "voxkit_model.json"
    try:
        with open(metadata_path, "r") as f:
            metadata = json.load(f)

        # Update fields
        for key, value in updates.items():
            if key in metadata:
                metadata[key] = str(value)

        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=4)

        return True, "Model metadata updated successfully."

    except Exception as e:
        print(f"Exception occurred during model metadata update: {e}")
        return False, "Failed to update model metadata."


def list_models(engine_id: str) -> list[ModelMetadata]:
    """List available models for the given engine.

    Args:
        engine_id: Identifier of the engine to list models for

    Returns:
        List of ModelMetadata dictionaries
    """
    try:
        models_root = Path(f"{get_storage_root()}/{engine_id}/{MODELS_ROOT}")
        if not models_root.exists():
            models_root.mkdir(parents=True, exist_ok=True)
            return []

        models_found = []
        for dir in models_root.iterdir():
            if dir.is_dir():
                metadata_path = dir / "voxkit_model.json"
                if metadata_path.exists():
                    try:
                        with open(metadata_path, "r") as f:
                            metadata = json.load(f)
                            models_found.append(metadata)
                    except json.JSONDecodeError as e:
                        print(f"Skipping invalid JSON in {metadata_path}: {e}")
                        continue
        return models_found

    except Exception as e:
        print(f"Error listing models: {e}")
        return []


def get_model_metadata(engine_id: str, model_id: str) -> ModelMetadata:
    """Get metadata for a specific model by its ID.

    Args:
        engine_id: Identifier of the engine the model belongs to
        model_id: Identifier of the model

    Returns:
        ModelMetadata dictionary

    Raises:
        FileNotFoundError: If the model or metadata file is not found
    """
    model_root = _get_model_root(engine_id, model_id)
    if not model_root:
        raise FileNotFoundError(f"Model '{model_id}' for engine '{engine_id}' not found")
    metadata_path = Path(model_root) / "voxkit_model.json"
    if not metadata_path.exists():
        raise FileNotFoundError(f"Metadata file not found for model '{model_id}'")
    with open(metadata_path, "r") as f:
        metadata = json.load(f)
        return metadata


def delete_model(engine_id: str, model_id: str) -> Tuple[bool, str]:
    """Delete a model given its engine ID and model ID.

    Args:
        engine_id: Identifier of the engine the model belongs to
        model_id: Identifier of the model to delete

    Returns:
        Tuple of (True, success_message) on success or (False, error_message) on failure
    """

    print(f"Attempting to delete model: engine_id={engine_id}, model_id={model_id}")
    model_path = _get_model_root(engine_id, model_id)

    if not model_path:
        return False, f"Model {model_id} not found"

    print(f"Deleting model at path: {model_path}")
    shutil.rmtree(model_path)
    return True, "Model deleted successfully."


def import_models(engine_id, new_models_root: Path) -> Tuple[bool, str]:
    """Import models into the storage system.

    Args:
        engine_id: Identifier of the engine
        new_models_root: Source directory containing models to import

    Returns:
        Tuple of (True, success_message) on success or (False, error_message) on failure
    """
    try:
        for new_model_path in new_models_root.iterdir():
            if new_model_path.is_dir():
                try:
                    # Check for voxkit_model.json file
                    metadata_path = Path(new_model_path / "voxkit_model.json")
                    if not metadata_path.exists():
                        return False, f"{new_model_path.name} (missing metadata file)"

                    metadata = None
                    # Read json metadata

                    with open(metadata_path, "r") as f:
                        metadata = json.load(f)

                    if metadata is None:
                        return False, f"{new_model_path.name} (invalid metadata file)"

                    engine_models_root = get_storage_root() / engine_id
                    if not engine_models_root.exists():
                        engine_models_root.mkdir(parents=True, exist_ok=False)

                    model_id = generate_unique_id()

                    if engine_id != metadata["engine_id"]:
                        return False, f"{new_model_path.name} (engine_id mismatch)"

                    parts = metadata["model_path"].split(MODELS_ROOT)
                    if len(parts) != 2:
                        return False, f"{new_model_path.name} (invalid model_path in metadata)"

                    # Retain the model path don't assume it's the same for all models
                    path_after_root = parts[1]

                    new_model_path = (
                        engine_models_root / MODELS_ROOT / model_id / path_after_root.split("/")[-1]
                    )
                    new_metadata = ModelMetadata(
                        name=metadata["name"],
                        engine_id=metadata["engine_id"],
                        model_path=Path(new_model_path),
                        data_path=Path(engine_models_root / MODELS_ROOT / model_id / "data"),
                        eval_path=Path(engine_models_root / MODELS_ROOT / model_id / "eval"),
                        train_path=Path(engine_models_root / MODELS_ROOT / model_id / "train"),
                        download_date=readable_from_unique_id(model_id),
                        id=model_id,
                    )

                    # Copy model directory to storage
                    dest_path = engine_models_root / MODELS_ROOT / model_id

                    shutil.copytree(new_model_path, dest_path, dirs_exist_ok=True)

                    # Convert Path objects to strings for JSON serialization
                    json_metadata = {
                        k: str(v) if isinstance(v, Path) else v for k, v in new_metadata.items()
                    }

                    # Overwrite metadata file with new IDs and paths
                    new_metadata_path = dest_path / "voxkit_model.json"

                    with open(new_metadata_path, "w") as f:
                        json.dump(json_metadata, f, indent=4)

                except Exception as e:
                    return False, f"{new_model_path.name} (error: {str(e)})"

        return True, f"Models imported successfully from: {new_models_root}"

    except Exception as e:
        return False, f"Failed to import model: {str(e)}"
