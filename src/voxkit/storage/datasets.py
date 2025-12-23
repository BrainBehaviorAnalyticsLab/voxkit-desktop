"""
Dataset Management Module
-------------------------

    Specialized CRUD operations for managing datasets within the VoxKit storage system.

Directory Structure (Many per Environment)
-------------------------------
Each dataset follows a hierarchical structure:

    my_dataset/
    ├── voxkit_dataset.json       # Dataset metadata
    ├── alignments/               # Alignment outputs storage
    └── cache/                    # Optional cached copy of dataset
        ├── speaker_001/
        │   ├── audio_001.wav
        │   ├── audio_001.lab
        │   └── ...
        └── speaker_002/
            └── ...

API
-----
- create_dataset: Create a new dataset metadata and directories.
- get_dataset_metadata: Retrieve metadata for a specific dataset.
- list_datasets_metadata: List all existing datasets.
- update_dataset_metadata: Update metadata fields for a specific dataset.
- delete_dataset: Delete a registered dataset and its metadata.
- export_dataset: Export a dataset to a specified output path.
- import_dataset: Import an existing dataset into VoxKit storage.

Notes
-----
- All dataset IDs are unique timestamps with microsecond precision
- Failed operations automatically clean up partial changes
- Dataset validation occurs before creation to prevent invalid data
- Cached datasets are copied for faster access
- transcribed flag indicates presence of transcriptions
- Importing datasets adjusts metadata and validates structure
"""

import json
import os
import shutil
from pathlib import Path
from typing import Any, List, Literal, Tuple, TypedDict

from voxkit.storage.config import ALIGNMENTS_ROOT, DATASETS_ROOT
from voxkit.storage.utils import generate_unique_id, get_storage_root, readable_from_unique_id


class DatasetMetadata(TypedDict):
    name: str
    id: str
    description: str
    original_path: str
    cached: bool
    anonymize: bool
    transcribed: bool
    registration_date: str


def _get_datasets_root() -> Path:
    """Get the root directory for storage relative to voxkit storage root.

    Returns:
        Path to datasets storage root
    """
    root = get_storage_root() / DATASETS_ROOT
    root.mkdir(parents=False, exist_ok=True)
    return root


def _get_dataset_root(dataset_id: str) -> Path | None:
    """Get the root directory for a specific dataset by ID.

    Args:
        dataset_id: Identifier of the dataset

    Returns:"""
    datasets_root = _get_datasets_root()
    if datasets_root and dataset_id:
        dataset_root = datasets_root / dataset_id
        if dataset_root.exists():
            return dataset_root
    return None


def _get_dataset_metadata(dataset_root: Path) -> DatasetMetadata | None:
    """Load dataset metadata from the given dataset root directory.

    Args:
        dataset_root: Path to the dataset root directory
    """
    try:
        metadata_path = dataset_root / "voxkit_dataset.json"
        if not metadata_path.exists():
            return None
        with open(metadata_path, "r") as f:
            return json.load(f)
    except Exception:
        return None


def create_dataset(
    name: str,
    description: str,
    original_path: str,
    cached: bool,
    anonymize: bool,
    transcribed: bool = False,
) -> tuple[Literal[True], DatasetMetadata] | tuple[Literal[False], str]:
    """Create a dataset metadata dictionary and create necessary directories.

    Args:
        name: Name of the dataset
        description: Description of the dataset
        original_path: Original path to the dataset
        cached: Whether the dataset is cached in storage
        anonymize: Whether the dataset should be anonymized

    Returns:
        Tuple of (success, message)
    """
    # Validate dataset structure
    valid, msg = validate_dataset(Path(original_path))
    if not valid:
        return False, msg

    now = generate_unique_id()

    try:
        humannow = readable_from_unique_id(now)
        metadata = DatasetMetadata(
            name=name,
            id=now,
            description=description,
            original_path=str(original_path),
            cached=cached,
            anonymize=anonymize,
            transcribed=transcribed,
            registration_date=humannow,
        )

        # Create dataset directory
        dataset_dir = _get_datasets_root() / metadata["id"]
        if dataset_dir.exists():
            raise FileExistsError(f"Dataset with ID '{metadata['id']}' already exists.")
        dataset_dir.mkdir(parents=False, exist_ok=False)

        # Create dataset/alignments directory
        alignments_dir = dataset_dir / ALIGNMENTS_ROOT
        alignments_dir.mkdir(parents=False, exist_ok=False)
        metadata_path = dataset_dir / "voxkit_dataset.json"
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)

        # Cache the dataset if requested
        if cached:
            cache_dir = dataset_dir / "cache"
            cache_dir.mkdir(parents=False, exist_ok=False)
            shutil.copytree(original_path, cache_dir, dirs_exist_ok=True)

        return True, metadata

    except Exception as e:
        # Clean up on failure
        dataset_dir = _get_datasets_root() / now
        if dataset_dir.exists():
            shutil.rmtree(dataset_dir, ignore_errors=False)

        print("Error during dataset creation:", str(e))
        return False, f"Failed to create dataset metadata: {str(e)}"


def get_dataset_metadata(dataset_id: str) -> DatasetMetadata | None:
    """Get the metadata for a specific dataset.

    Args:
        dataset_id: ID of the dataset to retrieve

    Returns:
        Dataset metadata dictionary or None if not found
    """
    try:
        dataset_dir = _get_datasets_root() / dataset_id
        metadata = _get_dataset_metadata(dataset_dir)
        if metadata is None:
            raise FileNotFoundError(f"Metadata for dataset '{dataset_id}' not found.")
        return metadata

    except Exception as e:
        print(f"Error retrieving dataset metadata: {str(e)}")
        return None


def list_datasets_metadata() -> List[DatasetMetadata]:
    """List all existing datasets.

    Returns:
        List of dataset metadata dictionaries
    """
    datasets = []
    datasets_root = _get_datasets_root()

    try:
        for entry in os.scandir(datasets_root):
            if entry.is_dir():
                metadata_path = os.path.join(entry.path, "voxkit_dataset.json")
                if os.path.exists(metadata_path):
                    with open(metadata_path, "r") as f:
                        metadata = json.load(f)
                        datasets.append(metadata)
        return datasets

    except Exception as e:
        print(f"Error listing datasets: {str(e)}")
        return []


def update_dataset_metadata(
    dataset_id: str,
    updates: dict,
) -> Tuple[bool, str]:
    """Update the metadata for a specific dataset.

    Args:
        dataset_id: ID of the dataset to update
        updates: Dictionary of metadata fields to update

    Returns:
        Tuple of (success, message)
    """
    try:
        metadata = get_dataset_metadata(dataset_id)

        if not metadata:
            return False, f"Dataset {dataset_id} not found"

        if updates["description"] is not None:
            metadata["description"] = updates["description"]
        if updates["cached"] is not None:
            metadata["cached"] = updates["cached"]
        if updates["anonymize"] is not None:
            metadata["anonymize"] = updates["anonymize"]
        if updates["transcribed"] is not None:
            metadata["transcribed"] = updates["transcribed"]

        # Save the updated metadata
        metadata_path = _get_datasets_root() / dataset_id / "voxkit_dataset.json"
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)

        return True, "Dataset metadata updated successfully"

    except KeyError as e:
        return False, f"Invalid metadata key: {str(e)}"
    except FileNotFoundError as e:
        return False, str(e)
    except Exception as e:
        return False, f"Failed to update dataset metadata: {str(e)}"


def delete_dataset(dataset_id: str) -> Tuple[bool, str]:
    """Delete a registered dataset.

    Args:
        dataset_id: ID of the dataset to delete

    Returns:
        Tuple of (success, message)
    """
    if not dataset_id:
        return False, "Dataset ID cannot be empty."

    dataset_path = _get_datasets_root() / dataset_id

    if dataset_path is None:
        return False, f"Dataset '{dataset_id}' not found"

    if not dataset_path.exists():
        return False, f"Dataset '{dataset_id}' not found"

    try:
        shutil.rmtree(dataset_path)
        return True, f"Dataset '{dataset_id}' metadata deleted successfully"

    except Exception as e:
        return False, f"Failed to delete dataset: {str(e)}"


def export_dataset(dataset_id: str, output_root: Path) -> Tuple[bool, str]:
    """Export an existing dataset to a specified output path.

    Args:
        dataset_id: Identifier of the dataset to export.
        output_root: Path to the output directory where the dataset will be copied.

    Returns:
        Tuple of (success, message)
    """

    if not output_root.exists():
        return False, f"Output path '{output_root}' does not exist."
    else:
        dataset_path = _get_datasets_root() / dataset_id

        if not dataset_path.exists():
            return False, f"Dataset '{dataset_id}' not found."

        dataset_meta = get_dataset_metadata(dataset_id)
        if not dataset_meta:
            return False, f"Metadata for dataset '{dataset_id}' not found."

        dest_path = output_root / (dataset_meta["name"] + "_" + dataset_id)
        try:
            shutil.copytree(dataset_path, dest_path, dirs_exist_ok=False)
            return True, f"Dataset '{dataset_id}' exported successfully to '{dest_path}'."
        except Exception as e:
            return False, f"Failed to export dataset: {str(e)}"


def import_dataset(dataset_path: Path) -> Tuple[bool, str]:
    """Import an existing dataset into VoxKit storage.

    Args:
        dataset_path: Path to the dataset to import.

    Returns:
        Tuple of (success, message)
    """
    # Validate dataset structure

    if not isinstance(dataset_path, Path):
        dataset_path = Path(dataset_path)
    if not dataset_path.exists():
        return False, f"Dataset path '{dataset_path}' does not exist."
    if not dataset_path.is_dir():
        return False, f"Dataset path '{dataset_path}' is not a directory."
    valid, valid_msg = validate_dataset(dataset_path / "cache")

    now = generate_unique_id()

    print(now)
    dataset_dest = _get_datasets_root() / now
    try:
        dataset_metadata_typed = _get_dataset_metadata(dataset_path)
        if dataset_metadata_typed is None:
            return False, "Dataset metadata file not found in the provided dataset path."

        # Change metadata accordingly
        dataset_metadata: dict[str, Any] = dict(dataset_metadata_typed)  # Make a copy to modify
        dataset_metadata["id"] = now
        humannow = readable_from_unique_id(now)
        dataset_metadata["registration_date"] = humannow

        # Check cache consistency
        if not dataset_metadata["cached"]:
            original_location_exists = Path(dataset_metadata["original_path"]).exists()
            if not original_location_exists:
                return (
                    False,
                    f"Original dataset path {dataset_metadata['original_path']} "
                    "does not exist; cannot import non-cached dataset.",
                )

        # Validate dataset
        elif not valid:
            return False, f"Dataset validation failed: {valid_msg}"

        metadata_path = dataset_dest / "voxkit_dataset.json"

        if not dataset_dest.exists():
            dataset_dest.mkdir(parents=False, exist_ok=False)

        shutil.copytree(dataset_path, dataset_dest, dirs_exist_ok=True)

        with open(metadata_path, "w") as f:
            json.dump(dataset_metadata, f, indent=2)

        return True, "Dataset imported successfully."

    except Exception as e:
        # Cleanup on failure
        if dataset_dest.exists():
            shutil.rmtree(dataset_dest, ignore_errors=True)
        print("Error during dataset import:", str(e))
        return False, f"Failed to import dataset: {str(e)}"


def validate_dataset(dataset_path: Path) -> Tuple[bool, str]:
    """Validate if a dataset follows the organization pattern.

    Expected structure:

        dataset_path/
        ├── speaker_001/
        │   ├── audio_001.wav
        │   ├── audio_001.lab
        │   ├── audio_002.wav
        │   └── audio_002.lab
        └── speaker_002/
            ├── audio_001.wav
            └── audio_001.lab

    Args:
        dataset_path: Path to dataset root directory

    Returns:
        Tuple of (is_valid, message) where:
            is_valid: True if dataset is valid, False otherwise
            message: Description of validation result or issues found
    """
    if not isinstance(dataset_path, Path):
        dataset_path = Path(dataset_path)
    if not dataset_path.exists():
        return False, f"Dataset path '{dataset_path}' does not exist."
    if not dataset_path.is_dir():
        return False, f"Dataset path '{dataset_path}' is not a directory."
    if not os.listdir(dataset_path):
        return False, f"Dataset path '{dataset_path}' is empty."
    for subdir in os.listdir(dataset_path):
        if subdir.startswith("."):
            continue  # Skip hidden files/directories
        subdir_path = os.path.join(dataset_path, subdir)
        if not os.path.isdir(subdir_path):
            return (
                False,
                f"Expected speaker directories in dataset path '{dataset_path}', "
                f"found file '{subdir_path}'.",
            )
        if not os.listdir(subdir_path):
            return False, f"Speaker directory '{subdir_path}' is empty."

    speaker_dirs = [
        d for d in os.listdir(dataset_path) if os.path.isdir(os.path.join(dataset_path, d))
    ]

    if not speaker_dirs:
        return False, "No speaker directories found in the dataset path."

    for speaker in speaker_dirs:
        speaker_path = os.path.join(dataset_path, speaker)
        audio_files = [
            f
            for f in os.listdir(speaker_path)
            if f.endswith(".wav")
            or f.endswith(".flac")
            or f.endswith(".mp3")
            or f.endswith(".ogg")
            or f.endswith(".m4a")
        ]
        label_files = [
            f for f in os.listdir(speaker_path) if f.endswith(".lab") or f.endswith(".txt")
        ]

        if not audio_files:
            return False, f"No audio files found in speaker directory '{speaker_path}'."

        if not label_files:
            return False, f"No label files found in speaker directory '{speaker_path}'."

        if len(audio_files) != len(label_files):
            return (
                False,
                f"Mismatch between number of audio and label files in speaker "
                f"directory '{speaker_path}'.",
            )

    return True, "Dataset is valid."
