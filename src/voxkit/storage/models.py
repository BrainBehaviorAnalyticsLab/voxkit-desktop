import json
import os
import shutil
from pathlib import Path
from typing import Tuple, TypedDict

from .config import MODELS_ROOT
from .utils import generate_unique_id, get_storage_root, readable_from_unique_id


class ModelMetadata(TypedDict):
    name: str
    engine_id: str
    model_path: Path
    data_path: Path
    eval_path: Path
    train_path: Path
    download_date: str
    id: str


def _get_model_root(engine_id: str, model_id: str) -> str:
    """Get the root directory for storing models for a given engine.
    """
    model_root = Path(f"{get_storage_root()}/{engine_id}/{MODELS_ROOT}/{model_id}")
    if model_root.exists():
        return model_root
    return None


def create_model(
    engine_id: str,
    model_name: str
) -> Tuple[True, ModelMetadata] | Tuple[False, str]:
    now = generate_unique_id()
    model_root = Path(f"{get_storage_root()}/{engine_id}/{MODELS_ROOT}/{now}")
    print(f"Creating model at: {model_root}")
    try:
        model_path = model_root / "entrypoint.model"
        print(f"Model path will be: {model_path}")
        data_path = model_root / "data"
        eval_path = model_root / "eval"
        train_path = model_root / "train"
        humandate = readable_from_unique_id(now)
        model_metadata = ModelMetadata(
            name=model_name or f"Model_{now}",
            engine_id=engine_id,
            model_path=str(model_path),
            data_path=str(data_path),
            eval_path=str(eval_path),
            train_path=str(train_path),
            download_date=humandate,
            id=now
        )
        # Create model directories
        model_path.mkdir(parents=True, exist_ok=False)
        data_path.mkdir(parents=True, exist_ok=False)
        eval_path.mkdir(parents=True, exist_ok=False)
        train_path.mkdir(parents=True, exist_ok=False)
        metadata_path = model_root / "voxkit_model.json"

        print(f"Metadata path will be: {metadata_path}")
        # Create metadata file and write metadata
        
        with open(metadata_path, "w") as f:
            json.dump(model_metadata, f, indent=4)

        return True, model_metadata
    
    except Exception as e:
        print("Exception occurred during model creation.")
        print(e)
        # Clean up partially created model directory
        if model_root and model_root.exists():
            shutil.rmtree(model_root)
        return False, "Failed to create model metadata."


def update_model_metadata(
    engine_id: str,
    model_id: ModelMetadata["id"],
    updates: dict
) -> Tuple[bool, str]:
    """Update metadata for an existing model.

    Args:
        engine_id: Identifier of the engine the model belongs to.
        model_id: Identifier of the model to update.
        updates: Dictionary of fields to update in the model metadata.

    Returns:
        Tuple of (success, message)
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
                metadata[key] = value
        
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=4)
        
        return True, "Model metadata updated successfully."
    
    except Exception as e:
        return False, f"Failed to update model metadata: {str(e)}"


def list_models(engine_id: str) -> list[ModelMetadata]:
    """List available model names for the given engine."""
    try:
        models_root = Path(f"{get_storage_root()}/{engine_id}/{MODELS_ROOT}")
        if not models_root.exists():
            raise FileNotFoundError(f"Models root does not exist: {models_root}")
        
        models_found = []
        for dir in models_root.iterdir():
            if dir.is_dir():
                metadata_path = dir / "voxkit_model.json"
                if metadata_path.exists():
                    with open(metadata_path, "r") as f:
                        metadata = json.load(f)
                        models_found.append(metadata)
        return models_found
    
    except Exception as e:
        print(f"Error listing models: {e}")
        return []
                    

def get_model_metadata(engine_id, model_id: ModelMetadata["id"]) -> ModelMetadata:
    """Get metadata for a specific model by its ID."""
    model_root = _get_model_root(engine_id, model_id)
    if not model_root:
        raise FileNotFoundError(f"Model '{model_id}' for engine '{engine_id}' not found")
    metadata_path = Path(model_root) / "voxkit_model.json"
    if not metadata_path.exists():
        raise FileNotFoundError(f"Metadata file not found for model '{model_id}'")
    with open(metadata_path, "r") as f:
        metadata = json.load(f)
        return metadata
    

def delete_model(engine_id, model_id: ModelMetadata["id"]):
    """Delete a model given its engine ID and model ID."""
    model_path = _get_model_root(engine_id, model_id)
    if os.path.exists(model_path):
        shutil.rmtree(model_path)
    else:
        raise FileNotFoundError(f"Model path does not exist: {model_path}")
