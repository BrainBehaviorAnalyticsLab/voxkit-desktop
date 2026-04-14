"""Dataset Management Module.

Specialized CRUD operations for managing datasets within the VoxKit storage system.

Directory Structure
-------------------
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
---
- **create_dataset**: Create a new dataset with metadata and directories
- **get_dataset_metadata**: Retrieve metadata for a specific dataset
- **list_datasets_metadata**: List all existing datasets
- **update_dataset_metadata**: Update metadata fields for a specific dataset
- **delete_dataset**: Delete a registered dataset and its metadata
- **export_dataset**: Export a dataset to a specified output path
- **import_dataset**: Import an existing dataset into VoxKit storage
- **validate_dataset**: Validate dataset structure and organization

Notes
-----
- All dataset IDs are unique timestamps with microsecond precision
- Failed operations automatically clean up partial changes
- Dataset validation occurs before creation to prevent invalid data
- Cached datasets are copied for faster access during operations
- The `transcribed` flag indicates presence of transcription files
- Importing datasets adjusts metadata and validates structure
"""

import csv
import json
import os
import shutil
from pathlib import Path
from typing import Any, List, Literal, Tuple, TypedDict

from voxkit.storage.config import ALIGNMENTS_ROOT, DATASETS_ROOT
from voxkit.storage.utils import generate_unique_id, get_storage_root, readable_from_unique_id


class DatasetMetadata(TypedDict):
    """Dataset metadata structure.

    Attributes:
        name: Human-readable name of the dataset.
        id: Unique identifier (timestamp with microsecond precision).
        description: Description of the dataset contents and purpose.
        original_path: Original file system path to the dataset.
        cached: Whether the dataset is cached in VoxKit storage.
        anonymize: Whether speaker identities should be anonymized.
        transcribed: Whether the dataset includes transcription files.
        registration_date: Human-readable registration timestamp.
    """

    name: str
    id: str
    description: str
    original_path: str
    cached: bool
    anonymize: bool
    transcribed: bool
    registration_date: str


def _get_datasets_root() -> Path:
    """Get the root directory for datasets storage.

    Returns:
        Path to datasets storage root directory
    """
    root = get_storage_root() / DATASETS_ROOT
    root.mkdir(parents=False, exist_ok=True)
    return root


def _get_dataset_root(dataset_id: str) -> Path | None:
    """Get the root directory for a specific dataset by ID.

    Args:
        dataset_id: Identifier of the dataset

    Returns:
        Path to dataset root directory or None if not found
    """
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

    Returns:
        Dataset metadata dictionary or None if not found or invalid
    """
    try:
        metadata_path = dataset_root / "voxkit_dataset.json"
        if not metadata_path.exists():
            return None
        with open(metadata_path, "r") as f:
            result: DatasetMetadata = json.load(f)
            return result
    except Exception:
        return None


def create_dataset(
    name: str,
    description: str,
    original_path: str,
    cached: bool,
    anonymize: bool,
    transcribed: bool = False,
    analysis_data: list[dict[str, Any]] | None = None,
    analysis_method: str | None = None,
) -> tuple[Literal[True], DatasetMetadata] | tuple[Literal[False], str]:
    """Create a dataset metadata dictionary and create necessary directories.

    Validates the dataset structure, creates a unique ID, sets up the directory
    hierarchy (dataset root and alignments subdirectory), writes metadata to JSON,
    optionally caches the dataset, and optionally saves analysis results to CSV.

    Args:
        name: Name of the dataset
        description: Description of the dataset
        original_path: Original path to the dataset
        cached: Whether to copy the dataset into VoxKit storage
        anonymize: Whether the dataset should be anonymized
        transcribed: Whether the dataset includes transcription files
        analysis_data: Optional list of analysis result dictionaries to save as CSV
        analysis_method: Optional name of the analysis method (used for CSV filename)

    Returns:
        Tuple of (True, DatasetMetadata) on success or (False, error_message) on failure

    Raises:
        FileExistsError: If a dataset with the generated ID already exists
        Exception: If directory creation, metadata writing, or caching fails

    Notes:
        - Automatically validates dataset structure before creation
        - Cleans up partially created directories on failure
        - Cached datasets are copied with shutil.copytree
        - If analysis_data is provided, saves to {analysis_method}_summary.csv
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

        # Save analysis results if provided
        if analysis_data is not None and analysis_method is not None:
            csv_path = dataset_dir / f"{analysis_method.lower()}_summary.csv"
            _save_analysis_csv(analysis_data, csv_path)

        return True, metadata

    except Exception as e:
        # Clean up on failure
        dataset_dir = _get_datasets_root() / now
        if dataset_dir.exists():
            shutil.rmtree(dataset_dir, ignore_errors=False)

        print("Error during dataset creation:", str(e))
        return False, f"Failed to create dataset metadata: {str(e)}"


def _save_analysis_csv(data: list[dict[str, Any]], path: Path) -> None:
    """Save analysis data to a CSV file.

    Args:
        data: List of dictionaries where each dictionary represents a row
        path: Output path for the CSV file

    Raises:
        ValueError: If data is empty
    """
    if not data:
        raise ValueError("No data to write to CSV.")

    fieldnames = data[0].keys()
    with open(path, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for row in data:
            writer.writerow(row)


def get_dataset_metadata(dataset_id: str) -> DatasetMetadata | None:
    """Get the metadata for a specific dataset.

    Retrieves the dataset metadata from the voxkit_dataset.json file in the
    dataset's directory.

    Args:
        dataset_id: ID of the dataset to retrieve

    Returns:
        Dataset metadata dictionary or None if not found

    Raises:
        Exception: If metadata file exists but cannot be read or parsed
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

    Scans the datasets root directory and collects metadata from all subdirectories
    containing valid voxkit_dataset.json files.

    Returns:
        List of dataset metadata dictionaries (empty list if none found)

    Notes:
        - Silently skips directories without metadata files
        - Returns empty list on error
        - Does not guarantee ordering
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

    Updates specific fields in the dataset metadata file. Only updates fields that
    are present in the updates dictionary and not None. Supported fields:
    description, cached, anonymize, transcribed.

    Args:
        dataset_id: ID of the dataset to update
        updates: Dictionary of metadata fields to update (only non-None values are applied)

    Returns:
        Tuple of (True, success_message) on success or (False, error_message) on failure

    Raises:
        FileNotFoundError: If the dataset is not found
        Exception: If metadata file cannot be written
    """
    try:
        metadata = get_dataset_metadata(dataset_id)

        if not metadata:
            return False, f"Dataset {dataset_id} not found"

        for field in ("description", "cached", "anonymize", "transcribed"):
            if field in updates and updates[field] is not None:
                metadata[field] = updates[field]

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

    Permanently removes the dataset directory and all its contents, including
    metadata, alignments, and cached data.

    Args:
        dataset_id: ID of the dataset to delete

    Returns:
        Tuple of (True, success_message) on success or (False, error_message) on failure

    Raises:
        Exception: If the directory cannot be removed

    Notes:
        - This operation is irreversible
        - Removes the entire dataset directory tree
        - Validates that dataset_id is not empty before proceeding
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

    Copies the entire dataset directory (including metadata, alignments, and cache)
    to the specified output location. The exported directory is named using the
    pattern: {dataset_name}_{dataset_id}

    Args:
        dataset_id: Identifier of the dataset to export
        output_root: Path to the output directory where the dataset will be copied

    Returns:
        Tuple of (True, success_message) on success or (False, error_message) on failure

    Raises:
        FileExistsError: If destination path already exists
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


def _rewrite_imported_alignments(new_dataset_path: Path) -> None:
    """Rewrite alignment metadata paths after importing a dataset to a new location.

    When a dataset is imported, its directory is copied to a new location under a
    new dataset id. Any ``local`` alignment has a ``tg_path`` that lives inside
    the dataset directory and still references the source location. For each such
    alignment, rewrite ``tg_path`` to ``<new_dataset>/alignments/<alignment_id>/
    textgrids``. Non-local alignments (``local == False``) store TextGrids at the
    dataset's ``original_path``, which is unchanged by import, so they are left
    alone.
    """
    alignments_dir = new_dataset_path / ALIGNMENTS_ROOT
    if not alignments_dir.is_dir():
        return

    for alignment_dir in alignments_dir.iterdir():
        if not alignment_dir.is_dir():
            continue
        metadata_file = alignment_dir / "voxkit_alignment.json"
        if not metadata_file.exists():
            continue
        try:
            with open(metadata_file, "r") as f:
                alignment_metadata = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            print(f"Skipping alignment metadata rewrite for '{metadata_file}': {e}")
            continue

        if not alignment_metadata.get("local"):
            continue

        alignment_metadata["tg_path"] = str(alignment_dir / "textgrids")
        try:
            with open(metadata_file, "w") as f:
                json.dump(alignment_metadata, f, indent=4)
        except OSError as e:
            print(f"Failed to rewrite alignment metadata '{metadata_file}': {e}")


def import_dataset(dataset_path: Path) -> Tuple[bool, str]:
    """Import an existing dataset into VoxKit storage.

    Imports a previously exported dataset or a dataset with valid VoxKit metadata.
    Generates a new ID, updates metadata with new registration date, validates
    cached datasets, and verifies original path accessibility for non-cached datasets.

    Args:
        dataset_path: Path to the dataset to import (must contain voxkit_dataset.json)

    Returns:
        Tuple of (True, success_message) on success or (False, error_message) on failure

    Raises:
        Exception: If dataset structure is invalid or copy operations fail

    Notes:
        - For cached datasets, validates the cache directory structure
        - For non-cached datasets, verifies the original_path is accessible
        - Automatically cleans up on failure
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

        _rewrite_imported_alignments(dataset_dest)

        return True, "Dataset imported successfully."

    except Exception as e:
        # Cleanup on failure
        if dataset_dest.exists():
            shutil.rmtree(dataset_dest, ignore_errors=True)
        print("Error during dataset import:", str(e))
        return False, f"Failed to import dataset: {str(e)}"


def validate_dataset(dataset_path: Path) -> Tuple[bool, str]:
    """Validate if a dataset follows the expected organization pattern.

    Validation checks:
    - Dataset path exists and is a directory
    - Dataset is not empty
    - Contains speaker subdirectories (not files at root level)
    - Each speaker directory is not empty
    - Each speaker directory contains audio files (.wav, .flac, .mp3, .ogg, .m4a)
    - Each speaker directory contains label files (.lab, .txt)
    - Number of audio files matches number of label files per speaker

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
        Tuple of (True, validation_message) if valid or (False, error_description) if invalid
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
