"""
Dataset Alignment Storage Module
--------------------------------

    Specialized CRUD operations for managing dataset alignments within the VoxKit storage system.

Directory Structure (None or Many per Dataset)
---------------------------------------
Each dataset alignment follows a hierarchical structure:

    dataset_id/
    ├── alignments/
    │   ├── alignment_id_1/
    │   │   ├── textgrids/             # Directory for TextGrid files
    │   │   └── voxkit_alignment.json  # Alignment metadata
    │   ├── alignment_id_2/
    │   │   ├── ...
    │   └── ...

API
---
- create_alignment: Create a new alignment entry in storage.
- get_alignment_metadata: Retrieve metadata for a specific alignment.
- update_alignment: Update the status or details of an existing alignment.
- list_alignments: List all alignments for a given dataset.
- delete_alignment: Remove an alignment from storage.

Notes
-----
- All paths are managed using pathlib.
- Added branching by engine_id may be neccesary to bridge different alignment formats.
- Error handling only exposes messages.
- Raises FileNotFoundError if alignment or metadata not found.
"""
import json
import os
import shutil
from pathlib import Path
from typing import List, Tuple, TypedDict

from .config import ALIGNMENTS_ROOT
from .datasets import  DatasetMetadata, get_dataset_metadata
from .models import ModelMetadata, get_model_metadata
from .datasets import DatasetMetadata, _get_dataset_root
from .utils import generate_unique_id, readable_from_unique_id


class AlignmentMetadata(TypedDict):
    id: str
    engine_id: str
    model_metadata: ModelMetadata
    local: bool
    alignment_date: str
    status: str
    tg_path: str


def _get_alignments_root(dataset_id: DatasetMetadata["id"]) -> Path | None:
    """Get the root directory for storing alignments for a given dataset.
    
    Args:
        dataset_id: Identifier of the dataset
        
    Returns:
        Path to the alignments root directory or None if dataset not found
    """
    dataset_root = _get_dataset_root(dataset_id)
    if dataset_root:
        alignments_root = dataset_root / ALIGNMENTS_ROOT
        alignments_root.mkdir(parents=False, exist_ok=True)
        return alignments_root
    
    return None


def _get_alignment_root(dataset_id: DatasetMetadata["id"], alignment_id: AlignmentMetadata["id"]) -> Path | None:
    """Get the root directory for a specific alignment by ID.
    
    Args:
        dataset_id: Identifier of the dataset containing the alignment
        alignment_id: Identifier of the alignment
        
    Returns:
        Path to the alignment root directory or None if not found.
    """
    alignments_root = _get_alignments_root(dataset_id)
    if alignments_root:
        alignment_root = alignments_root / alignment_id
        if alignment_root.exists():
            return alignment_root
    return None


def create_alignment(
    dataset_id: DatasetMetadata["id"], engine_id: str, model_id: ModelMetadata["id"]
) -> tuple[True, AlignmentMetadata] | tuple[False, str]:
    """Create a new alignment entry in the storage.

    Args:
        engine_id: Identifier of the alignment engine
        model_id: Identifier of the alignment model to use
        local: Whether the alignment is to be performed locally

    Returns:
        Tuple of (success, message or metadata)
    """
    # Fetch model metadata
    model_metadata = get_model_metadata(engine_id, model_id)
    if not model_metadata:
        return False, f"Model '{model_id}' for engine '{engine_id}' not found"
    
    # Fetch dataset metadata
    dataset_metadata = get_dataset_metadata(dataset_id)
    if not dataset_metadata:
        return False, f"Dataset '{dataset_id}' not found"
    
    # Fetch alignment root
    alignments_root = _get_alignments_root(dataset_id)
    if not alignments_root:
        return False, f"Dataset '{dataset_id}' not found"
    
    # Create alignment directory
    now = generate_unique_id()
    alignment_date = readable_from_unique_id(now)
    alignment_root = alignments_root / now

    alignment_root.mkdir(parents=False, exist_ok=False)

    try:
        tg_path = None
        local = dataset_metadata["cached"]
        if local:
            tg_path = Path(dataset_metadata["original_path"]) / "textgrids"
            tg_path.mkdir(parents=False, exist_ok=True)

        else:
            tg_path = alignment_root / "textgrids"
            tg_path.mkdir(parents=False, exist_ok=True)

        metadata = AlignmentMetadata(
            id=now,
            engine_id=engine_id,
            model_metadata=model_metadata,
            local=local,
            tg_path=str(tg_path),
            alignment_date=alignment_date,
            status="Pending"
        )

        # Fetch model metadata
        metadata_path = alignment_root / "voxkit_alignment.json"

        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=4)
 
        return True, metadata
    
    except Exception as e:
        # Clean up partially created directory
        if os.path.exists(alignment_root):
            shutil.rmtree(alignment_root, ignore_errors=True)
        return False, f"Failed to create alignment metadata: {str(e)}"


def get_alignment_metadata(dataset_id: DatasetMetadata["id"], alignment_id: AlignmentMetadata["id"]) -> AlignmentMetadata:
    """Get the metadata for a specific alignment by ID."""
    alignment_root = _get_alignment_root(dataset_id, alignment_id)
    if not alignment_root:
        return None
    
    metadata_path = alignment_root / "voxkit_alignment.json"

    try:
        with open(metadata_path, 'r') as f:
            metadata = json.load(f)
            return metadata
    except Exception as e:
        print(f"Failed to load alignment metadata from '{metadata_path}': {str(e)}")
        raise e


def update_alignment(dataset_id: DatasetMetadata["id"], alignment_id: AlignmentMetadata["id"], updates: dict) -> Tuple[bool, str]:
    """Update the status of an alignment.
    
    Args:
        dataset_id: Identifier of the dataset containing the alignment
        alignment_id: Identifier of the alignment to update
        updates: Dictionary of updates to apply to the alignment metadata
        
    Returns:
        Tuple of (success, message)
    """
    alignment_root = _get_alignment_root(dataset_id, alignment_id)
    if not alignment_root:
        return False, f"Alignment '{alignment_id}' for dataset '{dataset_id}' not found"
    
    metadata_path = alignment_root / "voxkit_alignment.json"

    try:
        with open(metadata_path, 'r') as f:
            metadata = json.load(f)
        
        # Update fields
        for key, value in updates.items():
            if key in metadata:
                metadata[key] = value
        
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=4)
        
        return True, "Alignment metadata updated successfully."
    
    except Exception as e:
        return False, f"Failed to update alignment metadata: {str(e)}"


def list_alignments(dataset_id: DatasetMetadata["id"]) -> List[AlignmentMetadata]:
    """List all alignment metadata for a given dataset.
    
    Args:
        dataset_id: Identifier of the dataset to list alignments

    Returns:
        List of alignment metadata dictionaries
    """
    alignments_root = _get_alignments_root(dataset_id)
    if not alignments_root:
        return []
    
    alignments_found = []
    for dir in alignments_root.iterdir():
        if dir.is_dir():
            metadata_path = dir / "voxkit_alignment.json"
            if metadata_path.exists():
                try:
                    with open(metadata_path, "r") as f:
                        metadata = json.load(f)
                        alignments_found.append(metadata)
                except Exception as e:
                    print(f"Failed to load alignment metadata from '{metadata_path}': {str(e)}")
    
    return alignments_found
    

def delete_alignment(dataset_id: DatasetMetadata["id"], alignment_id: AlignmentMetadata["id"]) -> Tuple[bool, str]:
    """
    Delete an alignment given its dataset ID and alignment ID.

    Args:
        dataset_id: Identifier of the dataset containing the alignment
        alignment_id: Identifier of the alignment to delete

    Returns:
        Tuple of (success, message)
    """
    alignment_root = _get_alignment_root(dataset_id, alignment_id)
    if not alignment_root:
        return False, f"Alignment '{alignment_id}' for dataset '{dataset_id}' not found"
    
    try:
        shutil.rmtree(alignment_root)
        return True, f"Alignment '{alignment_id}' deleted successfully."
    except Exception as e:
        return False, f"Failed to delete alignment '{alignment_id}': {str(e)}"
      