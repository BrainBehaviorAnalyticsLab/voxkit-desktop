"""Dataset Alignment Storage Module.

Specialized CRUD operations for managing dataset alignments within the VoxKit storage system.

Directory Structure
-------------------
Each dataset alignment follows a hierarchical structure:

    dataset_id/
    ├── alignments/
    │   ├── alignment_id_1/
    │   │   ├── textgrids/             # Directory for TextGrid files
    │   │   └── voxkit_alignment.json  # Alignment metadata
    │   ├── alignment_id_2/
    │   │   └── ...
    │   └── ...
    └── ...

API
---
- **create_alignment**: Create a new alignment entry in storage
- **create_hand_alignment**: Create a new hand-annotated alignment entry in storage
- **get_alignment_metadata**: Retrieve metadata for a specific alignment
- **update_alignment**: Update the status or details of an existing alignment
- **list_alignments**: List all alignments for a given dataset
- **delete_alignment**: Remove an alignment from storage

Notes
-----
- All paths are managed using pathlib
- Engine-specific branching may be necessary to bridge different alignment formats
- Error handling only exposes user-friendly messages
- Alignment IDs are generated using unique timestamps with microsecond precision
- TextGrid paths depend on whether the dataset is cached locally or not
"""

import json
import os
import shutil
from pathlib import Path
from typing import List, Literal, Tuple, TypedDict

from .config import ALIGNMENTS_ROOT
from .datasets import _get_dataset_root, get_dataset_metadata
from .models import ModelMetadata, get_model_metadata
from .utils import generate_unique_id, readable_from_unique_id

HAND_ALIGNMENT_SENTINEL = "hand"
"""Sentinel value used for engine_id/model id on manually-created (hand) alignments."""

AlignmentStatus = Literal["pending", "completed", "failed"]
"""Status of an alignment operation.

Values:
    pending: Alignment has been created but not yet processed.
    completed: Alignment has been successfully completed.
    failed: Alignment processing failed.
"""


class AlignmentMetadata(TypedDict):
    """Alignment metadata structure.

    Attributes:
        id: Unique identifier (timestamp with microsecond precision).
        engine_id: Identifier of the alignment engine used (e.g., "mfa").
        model_metadata: Metadata of the model used for alignment.
        local: Whether TextGrid files are stored locally (cached) or at original path.
        alignment_date: Human-readable alignment creation timestamp.
        status: Current status of the alignment operation.
        tg_path: Path to the directory containing TextGrid output files.
    """

    id: str
    engine_id: str
    model_metadata: ModelMetadata
    local: bool
    alignment_date: str
    status: AlignmentStatus
    tg_path: str


def _get_alignments_root(dataset_id: str) -> Path | None:
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


def _get_alignment_root(dataset_id: str, alignment_id: str) -> Path | None:
    """Get the root directory for a specific alignment by ID.

    Args:
        dataset_id: Identifier of the dataset containing the alignment
        alignment_id: Identifier of the alignment

    Returns:
        Path to the alignment root directory or None if not found
    """
    alignments_root = _get_alignments_root(dataset_id)
    if alignments_root:
        alignment_root = alignments_root / alignment_id
        if alignment_root.exists():
            return alignment_root
    return None


def create_alignment(
    dataset_id: str, engine_id: str, model_id: str
) -> tuple[Literal[True], AlignmentMetadata] | tuple[Literal[False], str]:
    """Create a new alignment entry in the storage.

    Creates an alignment directory, sets up TextGrid output location based on whether
    the dataset is cached, generates metadata, and initializes the alignment with
    "pending" status.

    Args:
        dataset_id: Identifier of the dataset to align
        engine_id: Identifier of the alignment engine
        model_id: Identifier of the alignment model to use

    Returns:
        Tuple of (True, AlignmentMetadata) on success or (False, error_message) on failure

    Raises:
        FileNotFoundError: If model or dataset is not found
        Exception: If directory creation or metadata writing fails

    Notes:
        - For cached datasets, TextGrid output is stored in the alignment directory
        - For non-cached datasets, TextGrid output is stored in the original dataset path
        - Automatically cleans up on failure
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
        if bool(local) is False:
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
            status="pending",
        )

        # Fetch model metadata
        metadata_path = alignment_root / "voxkit_alignment.json"

        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=4)

        return True, metadata

    except Exception as e:
        # Clean up partially created directory
        if os.path.exists(alignment_root):
            shutil.rmtree(alignment_root, ignore_errors=True)
        return False, f"Failed to create alignment metadata: {str(e)}"


_AUDIO_EXTS = (".wav", ".flac", ".mp3", ".ogg", ".m4a")


def validate_hand_alignments(dataset_path: Path, hand_path: Path) -> Tuple[bool, str]:
    """Validate that a hand-alignments directory matches a dataset's speaker/audio layout.

    Expects the hand-alignments directory to mirror the dataset: one subdirectory
    per speaker, containing a ``.TextGrid`` file for every audio file in the
    corresponding dataset speaker directory (matched by stem).

    Args:
        dataset_path: Path to the dataset root (containing speaker subdirectories)
        hand_path: Path to the hand-annotated TextGrid root

    Returns:
        Tuple of (True, "...") if valid, or (False, error_message) if not
    """
    if not isinstance(dataset_path, Path):
        dataset_path = Path(dataset_path)
    if not isinstance(hand_path, Path):
        hand_path = Path(hand_path)

    if not hand_path.exists() or not hand_path.is_dir():
        return False, f"Hand alignments path '{hand_path}' is not an existing directory."

    dataset_speakers = {
        d.name for d in dataset_path.iterdir() if d.is_dir() and not d.name.startswith(".")
    }
    hand_speakers = {
        d.name for d in hand_path.iterdir() if d.is_dir() and not d.name.startswith(".")
    }

    missing_speakers = dataset_speakers - hand_speakers
    if missing_speakers:
        return (
            False,
            f"Hand alignments missing speaker directories: {', '.join(sorted(missing_speakers))}",
        )

    for speaker in sorted(dataset_speakers):
        audio_stems = {
            f.stem for f in (dataset_path / speaker).iterdir() if f.suffix.lower() in _AUDIO_EXTS
        }
        tg_stems = {
            f.stem for f in (hand_path / speaker).iterdir() if f.suffix.lower() == ".textgrid"
        }
        missing = audio_stems - tg_stems
        if missing:
            return (
                False,
                f"Speaker '{speaker}' is missing TextGrid files for: {', '.join(sorted(missing))}",
            )

    return True, "Hand alignments match dataset layout."


def create_hand_alignment(
    dataset_id: str,
    tg_path: str | None = None,
) -> tuple[Literal[True], AlignmentMetadata] | tuple[Literal[False], str]:
    """Create a new hand-annotated alignment entry in storage.

    Mirrors `create_alignment` but skips engine/model lookup — engine_id and the
    model metadata fields are filled with the `HAND_ALIGNMENT_SENTINEL` value.
    Starts in "completed" status since there is no processing step.

    Args:
        dataset_id: Identifier of the dataset to align
        tg_path: Optional existing directory of hand-annotated TextGrids. When
            provided, it is recorded as-is and the alignment is marked non-local.
            When omitted, falls back to the same tg_path resolution used by
            `create_alignment`.

    Returns:
        Tuple of (True, AlignmentMetadata) on success or (False, error_message) on failure
    """
    dataset_metadata = get_dataset_metadata(dataset_id)
    if not dataset_metadata:
        return False, f"Dataset '{dataset_id}' not found"

    alignments_root = _get_alignments_root(dataset_id)
    if not alignments_root:
        return False, f"Dataset '{dataset_id}' not found"

    now = generate_unique_id()
    alignment_date = readable_from_unique_id(now)
    alignment_root = alignments_root / now

    alignment_root.mkdir(parents=False, exist_ok=False)

    try:
        if tg_path is not None:
            local = False
            resolved_tg_path = Path(tg_path)
        else:
            local = dataset_metadata["cached"]
            if bool(local) is False:
                resolved_tg_path = Path(dataset_metadata["original_path"]) / "textgrids"
            else:
                resolved_tg_path = alignment_root / "textgrids"
            resolved_tg_path.mkdir(parents=False, exist_ok=True)

        model_metadata = ModelMetadata(
            name=HAND_ALIGNMENT_SENTINEL,
            engine_id=HAND_ALIGNMENT_SENTINEL,
            model_path="",  # type: ignore[typeddict-item]
            data_path="",  # type: ignore[typeddict-item]
            eval_path="",  # type: ignore[typeddict-item]
            train_path="",  # type: ignore[typeddict-item]
            download_date=alignment_date,
            id=HAND_ALIGNMENT_SENTINEL,
        )

        metadata = AlignmentMetadata(
            id=now,
            engine_id=HAND_ALIGNMENT_SENTINEL,
            model_metadata=model_metadata,
            local=local,
            tg_path=str(resolved_tg_path),
            alignment_date=alignment_date,
            status="completed",
        )

        metadata_path = alignment_root / "voxkit_alignment.json"
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=4)

        return True, metadata

    except Exception as e:
        if os.path.exists(alignment_root):
            shutil.rmtree(alignment_root, ignore_errors=True)
        return False, f"Failed to create hand alignment metadata: {str(e)}"


def get_alignment_metadata(dataset_id: str, alignment_id: str) -> AlignmentMetadata | None:
    """Get the metadata for a specific alignment by ID.

    Retrieves the alignment metadata from the voxkit_alignment.json file in the
    alignment's directory. Normalizes status values to lowercase for consistency.

    Args:
        dataset_id: Identifier of the dataset containing the alignment
        alignment_id: Identifier of the alignment

    Returns:
        AlignmentMetadata dictionary or None if not found

    Raises:
        Exception: If metadata file cannot be loaded or parsed
        JSONDecodeError: If the metadata file is malformed
    """
    alignment_root = _get_alignment_root(dataset_id, alignment_id)
    if not alignment_root:
        return None

    metadata_path = alignment_root / "voxkit_alignment.json"

    try:
        with open(metadata_path, "r") as f:
            metadata: AlignmentMetadata = json.load(f)
            # Normalize status to lowercase for consistency
            if "status" in metadata:
                status_lower = metadata["status"].lower()
                # Cast to the correct literal type
                metadata["status"] = status_lower  # type: ignore[typeddict-item]
            return metadata
    except Exception as e:
        print(f"Failed to load alignment metadata from '{metadata_path}': {str(e)}")
        raise e


def update_alignment(dataset_id: str, alignment_id: str, updates: dict) -> Tuple[bool, str]:
    """Update the status or metadata of an alignment.

    Updates fields in the alignment's metadata file. Only fields present in the
    metadata are updated. Status values are automatically normalized to lowercase.

    Args:
        dataset_id: Identifier of the dataset containing the alignment
        alignment_id: Identifier of the alignment to update
        updates: Dictionary of updates to apply to the alignment metadata

    Returns:
        Tuple of (True, success_message) on success or (False, error_message) on failure

    Raises:
        FileNotFoundError: If the alignment is not found
        Exception: If metadata file cannot be read or written

    Notes:
        - Status values are normalized to lowercase for consistency
        - Commonly updated fields include "status" for tracking progress
    """
    alignment_root = _get_alignment_root(dataset_id, alignment_id)
    if not alignment_root:
        return False, f"Alignment '{alignment_id}' for dataset '{dataset_id}' not found"

    metadata_path = alignment_root / "voxkit_alignment.json"

    try:
        with open(metadata_path, "r") as f:
            metadata = json.load(f)

        # Update fields
        for key, value in updates.items():
            if key in metadata:
                # Normalize status values to lowercase
                if key == "status" and isinstance(value, str):
                    value = value.lower()
                metadata[key] = value

        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=4)

        return True, "Alignment metadata updated successfully."

    except Exception as e:
        return False, f"Failed to update alignment metadata: {str(e)}"


def list_alignments(dataset_id: str) -> List[AlignmentMetadata]:
    """List all alignment metadata for a given dataset.

    Scans the dataset's alignments directory and collects metadata from all
    subdirectories containing valid voxkit_alignment.json files. Normalizes
    status values to lowercase for consistency.

    Args:
        dataset_id: Identifier of the dataset to list alignments for

    Returns:
        List of AlignmentMetadata dictionaries (empty list if none found)

    Notes:
        - Skips directories with invalid or missing metadata files
        - Returns empty list if dataset not found
        - Status values are normalized to lowercase
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
                        # Normalize status to lowercase for consistency
                        if "status" in metadata:
                            metadata["status"] = metadata["status"].lower()
                        alignments_found.append(metadata)
                except Exception as e:
                    print(f"Failed to load alignment metadata from '{metadata_path}': {str(e)}")

    return alignments_found


def delete_alignment(dataset_id: str, alignment_id: str) -> Tuple[bool, str]:
    """Delete an alignment given its dataset ID and alignment ID.

    Permanently removes the alignment directory and all its contents, including
    metadata and TextGrid files (if stored locally).

    Args:
        dataset_id: Identifier of the dataset containing the alignment
        alignment_id: Identifier of the alignment to delete

    Returns:
        Tuple of (True, success_message) on success or (False, error_message) on failure

    Raises:
        Exception: If the directory cannot be removed

    Notes:
        - This operation is irreversible
        - Only removes TextGrid files if they are stored locally (cached datasets)
        - TextGrid files in the original dataset path are not removed
    """
    alignment_root = _get_alignment_root(dataset_id, alignment_id)
    if not alignment_root:
        return False, f"Alignment '{alignment_id}' for dataset '{dataset_id}' not found"

    try:
        shutil.rmtree(alignment_root)
        return True, f"Alignment '{alignment_id}' deleted successfully."
    except Exception as e:
        return False, f"Failed to delete alignment '{alignment_id}': {str(e)}"
