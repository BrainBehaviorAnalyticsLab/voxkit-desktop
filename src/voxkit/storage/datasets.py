"""
Dataset management module for registering, validating, and managing speech datasets.
Supports Kaldi-style dataset organization with speaker subdirectories.
"""

import datetime
import json
import os
import shutil
from typing import List, Optional, Tuple, TypedDict

from .config import DATASETS_ROOT
from .utils import get_storage_root


class DatasetMetadata(TypedDict):
    """Metadata structure for datasets"""
    name: str
    description: str
    original_path: str
    cached: bool
    anonymize: bool
    transcribed: bool
    registration_date: str


def create_dataset(
    name: str,
    description: str,
    original_path: str,
    cached: bool,
    anonymize: bool,
    transcribed: bool = False,
) -> tuple[bool, str]:
    """Create a dataset metadata dictionary

    Args:
        name: Name of the dataset
        description: Description of the dataset
        original_path: Original path to the dataset
        cached: Whether the dataset is cached in storage
        anonymize: Whether the dataset should be anonymized during inference/training
    """
    try:
        now = datetime.datetime.now().isoformat()
        metadata = DatasetMetadata(
            name=name,
            description=description,
            original_path=original_path,
            cached=cached,
            anonymize=anonymize,
            transcribed=transcribed,
            registration_date=now,
        )
    
        # save to json file in the datasets directory
        dataset_dir = os.path.join(get_datasets_root(), name)
        os.makedirs(dataset_dir, exist_ok=True)
        metadata_path = os.path.join(dataset_dir, "voxkit_dataset.json")
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        return True, "Dataset metadata created successfully"
    except Exception as e:
        return False, f"Failed to create dataset metadata: {str(e)}"
    

def get_datasets_root() -> str:
    """Get the root directory for storing dataset metadata and cached datasets."""
    root = os.path.join(get_storage_root(), DATASETS_ROOT)
    os.makedirs(root, exist_ok=True)
    return root


def get_dataset_metadata_path(dataset_name: str) -> str:
    """Get the path to a dataset's metadata file."""
    dataset_dir = os.path.join(get_datasets_root(), dataset_name)
    return os.path.join(dataset_dir, "voxkit_dataset.json")


def list_datasets() -> List[DatasetMetadata]:
    """
    List all registered datasets.
    
    Returns:
        List of dataset metadata dictionaries
    """
    datasets = []
    datasets_root = get_datasets_root()
    
    if not os.path.exists(datasets_root):
        return datasets
    
    try:
        for entry in os.scandir(datasets_root):
            if entry.is_dir():
                metadata_path = get_dataset_metadata_path(entry.name)
                if os.path.exists(metadata_path):
                    try:
                        with open(metadata_path, 'r') as f:
                            metadata = json.load(f)
                            datasets.append(metadata)
                    except (json.JSONDecodeError, IOError) as e:
                        print(f"Warning: Failed to read metadata for dataset '{entry.name}': {e}")
                        continue
    except Exception as e:
        print(f"Error listing datasets: {e}")
    
    return datasets


def get_dataset(dataset_name: str) -> Optional[DatasetMetadata]:
    """
    Get metadata for a specific dataset.
    
    Args:
        dataset_name: Name of the dataset
        
    Returns:
        Dataset metadata or None if not found
    """
    metadata_path = get_dataset_metadata_path(dataset_name)
    
    if not os.path.exists(metadata_path):
        return None
    
    try:
        with open(metadata_path, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return None


def update_dataset(
    dataset_name: str,
    description: Optional[str] = None,
    anonymize: Optional[bool] = None
) -> Tuple[bool, str]:
    """
    Update dataset metadata.
    
    Args:
        dataset_name: Name of the dataset to update
        description: New description (if provided)
        anonymize: New anonymize flag (if provided)
        
    Returns:
        Tuple of (success, message)
    """
    metadata = get_dataset(dataset_name)
    
    if not metadata:
        return False, f"Dataset '{dataset_name}' not found"
    
    try:
        if description is not None:
            metadata["description"] = description
        if anonymize is not None:
            metadata["anonymize"] = anonymize
        
        metadata_path = get_dataset_metadata_path(dataset_name)
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        return True, f"Dataset '{dataset_name}' updated successfully"
        
    except Exception as e:
        return False, f"Failed to update dataset: {str(e)}"


def delete_dataset(dataset_name: str, remove_cached_files: bool = True) -> Tuple[bool, str]:
    """
    Delete a registered dataset.
    
    Args:
        dataset_name: Name of the dataset to delete
        remove_cached_files: If True, also delete cached files (if any)
        
    Returns:
        Tuple of (success, message)
    """
    dataset_path = os.path.join(get_datasets_root(), dataset_name)
    
    if not os.path.exists(dataset_path):
        return False, f"Dataset '{dataset_name}' not found"
    
    try:
        if remove_cached_files:
            shutil.rmtree(dataset_path)
            return True, f"Dataset '{dataset_name}' and all cached files deleted successfully"
        else:
            # Only delete metadata, keep cached files if they exist
            metadata_path = get_dataset_metadata_path(dataset_name)
            if os.path.exists(metadata_path):
                os.remove(metadata_path)
            return True, f"Dataset '{dataset_name}' metadata deleted successfully"
            
    except Exception as e:
        return False, f"Failed to delete dataset: {str(e)}"


def get_dataset_path(dataset_name: str) -> Optional[str]:
    """
    Get the actual path to use for a dataset (cached or original).
    
    Args:
        dataset_name: Name of the dataset
        
    Returns:
        Path to the dataset directory (cached if available, otherwise original)
    """
    metadata = get_dataset(dataset_name)
    
    if not metadata:
        return None
    
    if metadata["cached"]:
        cached_path = os.path.join(get_datasets_root(), dataset_name, "data")
        if os.path.exists(cached_path):
            return cached_path
    
    # Fall back to original path
    if os.path.exists(metadata["original_path"]):
        return metadata["original_path"]
    
    return None


def export_dataset_config(dataset_name: str, output_path: str) -> Tuple[bool, str]:
    """
    Export dataset configuration to a JSON file.
    
    Args:
        dataset_name: Name of the dataset to export
        output_path: Path where to save the configuration
        
    Returns:
        Tuple of (success, message)
    """
    metadata = get_dataset(dataset_name)
    
    if not metadata:
        return False, f"Dataset '{dataset_name}' not found"
    
    try:
        with open(output_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        return True, f"Dataset configuration exported to {output_path}"
    except Exception as e:
        return False, f"Failed to export dataset configuration: {str(e)}"


def validate_kaldi_dataset(
    dataset_path: str
) -> Tuple[bool, str, dict]:
    """
    Validate if a dataset follows Kaldi organization pattern.
    
    Expected structure:
        dataset_root/
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
        Tuple of (is_valid, message, stats_dict) where:
            is_valid: True if dataset is valid, False otherwise
            message: Description of validation result or issues found
    """
    if not os.path.exists(dataset_path):
        return False
    if not os.path.isdir(dataset_path):
        return False
    
    speaker_dirs = [d for d in os.listdir(dataset_path) if os.path.isdir(os.path.join(dataset_path, d))]
    if not speaker_dirs:
        return False
    
    for speaker in speaker_dirs:
        speaker_path = os.path.join(dataset_path, speaker)
        audio_files = [f for f in os.listdir(speaker_path) if f.endswith('.wav') or f.endswith('.flac') or f.endswith('.mp3') or f.endswith('.ogg') or f.endswith('.m4a')]
        label_files = [f for f in os.listdir(speaker_path) if f.endswith('.lab') or f.endswith('.txt')]
        
        if not audio_files:
            return False
        
        if not label_files:
            return False
        
        if len(audio_files) != len(label_files):
            return False
        
    return True

# def register_dataset(
#     dataset_path: str,
#     dataset_name: str,
#     description: str,
#     cache: bool = False,
#     anonymize: bool = False
# ) -> Tuple[bool, str]:
#     """
#     Register a new dataset.
    
#     Args:
#         dataset_path: Path to the dataset root directory
#         dataset_name: Name for the dataset (used as directory name)
#         description: Semantic description of the dataset
#         cache: If True, copy entire dataset to storage; if False, only store metadata
#         anonymize: If True, mark dataset for anonymization during inference/training
        
#     Returns:
#         Tuple of (success, message)
#     """

#     # Validate dataset structure first
#     is_valid = validate_kaldi_dataset(dataset_path)

#     if not is_valid:
#         return False, "Dataset structure is invalid. Please ensure it follows the Kaldi organization pattern."

#     # Create dataset directory in storage
#     dataset_storage_path = os.path.join(get_datasets_root(), dataset_name)
    
#     if os.path.exists(dataset_storage_path):
#         return False, f"Dataset '{dataset_name}' already exists. Use a different name or delete the existing dataset."
    
#     try:
#         os.makedirs(dataset_storage_path, exist_ok=True)
        
#         # Create metadata. Use validation stats (list of per-speaker dicts).
#         # analyzer.analyze could provide additional info, but prefer validation results
#         # for speaker-level breakdown.
#         try:
#             stats = analyzer.analyze(dataset_path)
#         except Exception:
#             stats = None
        

#         speakers = stats if isinstance(stats, list) else []

#         metadata: DatasetMetadata = {
#             "name": dataset_name,
#             "description": description,
#             "original_path": os.path.abspath(dataset_path),
#             "cached": cache,
#             "anonymize": anonymize,
#             "speakers": speakers,
#             "speaker_count": len(speakers),
#             "audio_file_count": sum(s.get("audio_file_count", 0) for s in speakers),
#         }
        
#         # Save metadata
#         metadata_path = get_dataset_metadata_path(dataset_name)
#         with open(metadata_path, 'w') as f:
#             json.dump(metadata, f, indent=2)
        
#         # Cache dataset if requested
#         if cache:
#             cache_dir = os.path.join(dataset_storage_path, "data")
#             os.makedirs(cache_dir, exist_ok=True)
            
#             # Copy dataset files
#             print(f"Caching dataset to {cache_dir}...")
#             shutil.copytree(dataset_path, cache_dir, dirs_exist_ok=True)
#             print("Dataset cached successfully")
        
#         return True, f"Dataset '{dataset_name}' registered successfully."
        
#     except Exception as e:
#         # Clean up on failure
#         if os.path.exists(dataset_storage_path):
#             shutil.rmtree(dataset_storage_path, ignore_errors=True)
#         return False, f"Failed to register dataset: {str(e)}"