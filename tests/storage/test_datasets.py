import os
import shutil
from pathlib import Path

import pytest

from voxkit.storage.datasets import DatasetMetadata

from .test_setup import (
    activate_test_environment,
    deactivate_test_environment,
    mock_get_storage_root,
)


def generate_fake_datasets():
    """Generate a fake dataset for testing purposes."""
    # Create wav/lab file pairs
    dataset_path = mock_get_storage_root() / "fake_datasets" / "valid"
    dataset_path.mkdir(parents=True, exist_ok=True)

    participant_names = ["participant_1", "participant_2", "participant_3"]
    for participant in participant_names:
        wavlab_path = dataset_path / participant
        wavlab_path.mkdir(parents=True, exist_ok=True)

        for i in range(5):
            wav_file = wavlab_path / f"sample_{i}.wav"
            lab_file = wavlab_path / f"sample_{i}.lab"
            wav_file.touch()
            lab_file.touch()

    # Create an invalid dataset path
    dataset_path = mock_get_storage_root() / "fake_datasets" / "invalid"
    dataset_path.mkdir(parents=True, exist_ok=True)
    for participant in participant_names:
        wavlab_path = dataset_path / participant
        wavlab_path.mkdir(parents=True, exist_ok=True)

        for i in range(5):
            wav_file = wavlab_path / f"sample_{i}.wav"
            wav_file.touch()
            # Missing corresponding .lab files

    # Create entirely empty dataset path
    dataset_path = mock_get_storage_root() / "fake_datasets" / "empty"
    dataset_path.mkdir(parents=True, exist_ok=True)


@pytest.fixture(autouse=True)
def manage_test_environment():
    # Setup before each test
    activate_test_environment(mock_get_storage_root())

    # Generate fake datasets following setup
    generate_fake_datasets()
    yield
    # Cleanup after each test
    deactivate_test_environment(mock_get_storage_root())


valid_dataset_path = mock_get_storage_root() / "fake_datasets" / "valid"
invalid_dataset_path = mock_get_storage_root() / "fake_datasets" / "invalid"
empty_dataset_path = mock_get_storage_root() / "fake_datasets" / "empty"


class TestDatasets:
    class TestValidateDataset:
        def test_validate_dataset_valid(self, monkeypatch):
            from voxkit.storage import models
            from voxkit.storage.datasets import validate_dataset

            monkeypatch.setattr(models, "get_storage_root", mock_get_storage_root)

            is_valid, _ = validate_dataset(valid_dataset_path)
            assert is_valid is True

    class TestCreateDataset:
        def test_create_dataset_success_no_cache(self, monkeypatch):
            from voxkit.storage import datasets
            from voxkit.storage.datasets import DatasetMetadata, create_dataset

            monkeypatch.setattr(datasets, "get_storage_root", mock_get_storage_root)

            success, message = create_dataset(
                name="test_dataset",
                description="A test dataset",
                original_path=valid_dataset_path,
                cached=False,
                anonymize=False,
                transcribed=True,
            )

            assert success is True
            assert isinstance(message, dict)
            for key in DatasetMetadata.__annotations__.keys():
                assert key in message

            assert message["cached"] is False
            assert message["transcribed"] is True
            assert message["anonymize"] is False

            assert message["description"] == "A test dataset"

        def test_create_dataset_success_with_cache(self, monkeypatch):
            from voxkit.storage import datasets
            from voxkit.storage.datasets import DatasetMetadata, create_dataset

            monkeypatch.setattr(datasets, "get_storage_root", mock_get_storage_root)

            success, message = create_dataset(
                name="test_dataset_cached",
                description="A test dataset with caching",
                original_path=valid_dataset_path,
                cached=True,
                anonymize=True,
                transcribed=False,
            )

            assert success is True
            assert isinstance(message, dict)
            for key in DatasetMetadata.__annotations__.keys():
                assert key in message

            assert message["cached"] is True
            assert message["transcribed"] is False
            assert message["anonymize"] is True
            assert message["description"] == "A test dataset with caching"

        def test_create_dataset_invalid_path(self, monkeypatch):
            from voxkit.storage import datasets
            from voxkit.storage.datasets import create_dataset

            monkeypatch.setattr(datasets, "get_storage_root", mock_get_storage_root)

            success, message = create_dataset(
                name="test_dataset_invalid",
                description="A test dataset with invalid path",
                original_path=invalid_dataset_path,
                cached=False,
                anonymize=False,
                transcribed=True,
            )

            assert success is False
            assert isinstance(message, str)
            assert "No label files found" in message
            assert invalid_dataset_path.exists() is True

    class TestListDatasets:
        def test_list_datasets_metadata(self, monkeypatch):
            from voxkit.storage import datasets
            from voxkit.storage.datasets import create_dataset, list_datasets_metadata

            monkeypatch.setattr(datasets, "get_storage_root", mock_get_storage_root)

            # Create two datasets
            create_dataset(
                name="dataset_one",
                description="First test dataset",
                original_path=valid_dataset_path,
                cached=False,
                anonymize=False,
                transcribed=True,
            )
            create_dataset(
                name="dataset_two",
                description="Second test dataset",
                original_path=valid_dataset_path,
                cached=True,
                anonymize=True,
                transcribed=False,
            )

            dataset_list = list_datasets_metadata()
            assert len(dataset_list) >= 2  # At least the two we just created

            names = [ds["name"] for ds in dataset_list]
            assert "dataset_one" in names
            assert "dataset_two" in names

        def test_list_datasets_output_format(self, monkeypatch):
            from voxkit.storage import datasets
            from voxkit.storage.datasets import create_dataset, list_datasets_metadata

            monkeypatch.setattr(datasets, "get_storage_root", mock_get_storage_root)

            # Create a dataset
            create_dataset(
                name="dataset_format_test",
                description="Testing output format",
                original_path=valid_dataset_path,
                cached=False,
                anonymize=False,
                transcribed=True,
            )

            dataset_list = list_datasets_metadata()

            # Check that each dataset has all required fields
            for i in range(len(dataset_list)):
                for key in DatasetMetadata.__annotations__.keys():
                    assert key in dataset_list[i].keys()

        def test_list_datasets_empty(self, monkeypatch):
            from voxkit.storage import datasets
            from voxkit.storage.datasets import list_datasets_metadata

            monkeypatch.setattr(datasets, "get_storage_root", mock_get_storage_root)

            # Ensure no datasets exist
            deactivate_test_environment(mock_get_storage_root())
            activate_test_environment(mock_get_storage_root())

            dataset_list = list_datasets_metadata()
            assert isinstance(dataset_list, list)
            assert len(dataset_list) == 0

    class TestGetDatasetMetadata:
        def test_get_dataset_metadata_success(self, monkeypatch):
            from voxkit.storage import datasets
            from voxkit.storage.datasets import create_dataset, get_dataset_metadata

            monkeypatch.setattr(datasets, "get_storage_root", mock_get_storage_root)

            # Create a dataset
            success, message = create_dataset(
                name="dataset_metadata_test",
                description="Testing get_dataset_metadata",
                original_path=valid_dataset_path,
                cached=False,
                anonymize=False,
                transcribed=True,
            )
            assert success is True
            assert isinstance(message, dict)
            dataset_id = message["id"]

            metadata = get_dataset_metadata(dataset_id)
            assert metadata is not None

            for key in DatasetMetadata.__annotations__.keys():
                assert key in metadata

            assert metadata == message

        def test_get_dataset_metadata_nonexistent(self, monkeypatch):
            from voxkit.storage import datasets
            from voxkit.storage.datasets import get_dataset_metadata

            monkeypatch.setattr(datasets, "get_storage_root", mock_get_storage_root)

            # Attempt to retrieve metadata for a non-existent dataset
            metadata = get_dataset_metadata("nonexistent_id_12345")
            assert metadata is None

        def test_get_dataset_metadata_invalid_id(self, monkeypatch):
            from voxkit.storage import datasets
            from voxkit.storage.datasets import get_dataset_metadata

            monkeypatch.setattr(datasets, "get_storage_root", mock_get_storage_root)

            # Attempt to retrieve metadata with an invalid ID format
            metadata = get_dataset_metadata("")
            assert metadata is None

    class TestDeleteDataset:
        def test_delete_dataset_success(self, monkeypatch):
            from voxkit.storage import datasets
            from voxkit.storage.datasets import create_dataset, delete_dataset, get_dataset_metadata

            monkeypatch.setattr(datasets, "get_storage_root", mock_get_storage_root)

            # Create a dataset
            success, message = create_dataset(
                name="dataset_delete_test",
                description="Testing delete_dataset",
                original_path=valid_dataset_path,
                cached=False,
                anonymize=False,
                transcribed=True,
            )
            assert success is True
            assert isinstance(message, dict)
            dataset_id = message["id"]

            # Delete the dataset
            del_success, del_message = delete_dataset(dataset_id)
            assert del_success is True

            # Verify deletion
            metadata = get_dataset_metadata(dataset_id)
            assert metadata is None

        def test_delete_dataset_nonexistent(self, monkeypatch):
            from voxkit.storage import datasets
            from voxkit.storage.datasets import delete_dataset

            monkeypatch.setattr(datasets, "get_storage_root", mock_get_storage_root)

            # Attempt to delete a non-existent dataset
            del_success, del_message = delete_dataset("nonexistent_id_12345")
            assert del_success is False
            assert "not found" in del_message

        def test_delete_dataset_invalid_id(self, monkeypatch):
            from voxkit.storage import datasets
            from voxkit.storage.datasets import delete_dataset

            monkeypatch.setattr(datasets, "get_storage_root", mock_get_storage_root)

            # Attempt to delete with an invalid ID format
            del_success, del_message = delete_dataset("")
            assert del_success is False
            assert "cannot be empty" in del_message

        def test_delete_dataset_twice(self, monkeypatch):
            from voxkit.storage import datasets
            from voxkit.storage.datasets import create_dataset, delete_dataset

            monkeypatch.setattr(datasets, "get_storage_root", mock_get_storage_root)

            # Create a dataset
            success, message = create_dataset(
                name="dataset_delete_twice_test",
                description="Testing delete_dataset twice",
                original_path=valid_dataset_path,
                cached=False,
                anonymize=False,
                transcribed=True,
            )
            assert success is True
            assert isinstance(message, dict)
            dataset_id = message["id"]

            # First deletion
            del_success, del_message = delete_dataset(dataset_id)
            assert del_success is True

            # Second deletion attempt
            del_success, del_message = delete_dataset(dataset_id)
            assert del_success is False
            assert "not found" in del_message

        def test_delete_dataset_invalid_id_format(self, monkeypatch):
            from voxkit.storage import datasets
            from voxkit.storage.datasets import delete_dataset

            monkeypatch.setattr(datasets, "get_storage_root", mock_get_storage_root)

            # Attempt to delete with an invalid ID format
            del_success, del_message = delete_dataset("!@#$%^&*()")
            assert del_success is False
            assert "not found" in del_message

    class TestExportDataset:
        def test_export_dataset_success(self, monkeypatch, tmp_path):
            from voxkit.storage import datasets
            from voxkit.storage.datasets import create_dataset, export_dataset

            monkeypatch.setattr(datasets, "get_storage_root", mock_get_storage_root)

            # Create a dataset
            success, message = create_dataset(
                name="dataset_export_test",
                description="Testing export_dataset",
                original_path=valid_dataset_path,
                cached=False,
                anonymize=False,
                transcribed=True,
            )
            assert success is True
            assert isinstance(message, dict)
            dataset_id = message["id"]

            export_path = mock_get_storage_root()
            exp_success, exp_message = export_dataset(dataset_id, export_path)

            assert exp_success is True
            assert "exported successfully" in exp_message

        def test_export_equal(self, monkeypatch):
            from voxkit.storage import datasets
            from voxkit.storage.datasets import _get_datasets_root, create_dataset, export_dataset

            monkeypatch.setattr(datasets, "get_storage_root", mock_get_storage_root)

            # Create a dataset
            success, message = create_dataset(
                name="dataset_export_equal_test",
                description="Testing export_dataset equality",
                original_path=valid_dataset_path,
                cached=False,
                anonymize=False,
                transcribed=True,
            )
            assert success is True
            assert isinstance(message, dict)
            dataset_id = message["id"]

            export_path = mock_get_storage_root()
            exp_success, exp_message = export_dataset(dataset_id, export_path)

            assert exp_success is True
            assert "exported successfully" in exp_message

            # Dataset metadata
            original_metadata = datasets.get_dataset_metadata(dataset_id)
            assert original_metadata is not None

            # Verify exported files match original files
            original_dataset_path = _get_datasets_root() / dataset_id
            destination_path = export_path / Path(original_metadata["name"] + "_" + str(dataset_id))

            # Check that all files exist in the exported location
            for root, _, files in os.walk(original_dataset_path):
                rel_root = Path(root).relative_to(original_dataset_path)
                for file in files:
                    original_file = Path(root) / file
                    exported_file = destination_path / rel_root / file
                    assert exported_file.exists() is True
                    assert original_file.stat().st_size == exported_file.stat().st_size

    class TestImportDataset:
        def test_import_dataset_success(self, monkeypatch):
            from voxkit.storage import datasets
            from voxkit.storage.datasets import create_dataset, import_dataset, validate_dataset

            monkeypatch.setattr(datasets, "get_storage_root", mock_get_storage_root)

            # Create a dataset to export and then import
            success, message = create_dataset(
                name="dataset_import_test",
                description="Testing import_dataset",
                original_path=valid_dataset_path,
                cached=True,
                anonymize=False,
                transcribed=True,
            )
            assert success is True
            assert isinstance(message, dict)
            dataset_id = message["id"]

            export_path = mock_get_storage_root()
            datasets.export_dataset(dataset_id, export_path)

            assert (
                Path(export_path / Path(message["name"] + "_" + str(dataset_id)) / "cache").exists()
                is True
            )

            assert (
                validate_dataset(
                    export_path / Path(message["name"] + "_" + str(dataset_id)) / "cache"
                )[0]
                is True
            )

            imp_success, imp_message = import_dataset(
                export_path / Path(message["name"] + "_" + str(dataset_id)),
            )

            assert imp_success is True
            assert "imported successfully" in imp_message

        def test_import_dataset_nonexistent(self, monkeypatch):
            from voxkit.storage import datasets
            from voxkit.storage.datasets import import_dataset

            monkeypatch.setattr(datasets, "get_storage_root", mock_get_storage_root)

            # Attempt to import from a non-existent path
            imp_success, imp_message = import_dataset(
                mock_get_storage_root() / "nonexistent_path_12345",
            )

            assert imp_success is False
            assert "does not exist" in imp_message

        def test_import_dataset_empty_cache_true(self, monkeypatch):
            from voxkit.storage import datasets
            from voxkit.storage.datasets import _get_datasets_root, create_dataset, import_dataset

            monkeypatch.setattr(datasets, "get_storage_root", mock_get_storage_root)

            # Create a dataset to export and then import
            success, message = create_dataset(
                name="dataset_import_test",
                description="Testing import_dataset",
                original_path=valid_dataset_path,
                cached=True,
                anonymize=False,
                transcribed=True,
            )
            assert success is True
            assert isinstance(message, dict)

            # empty cache directory
            dataset_id = message["id"]

            dataset_path = _get_datasets_root() / dataset_id / "cache"

            shutil.rmtree(dataset_path)
            dataset_path.mkdir(parents=True, exist_ok=True)

            export_path = mock_get_storage_root()
            datasets.export_dataset(dataset_id, export_path)

            imp_success, msg = import_dataset(
                empty_dataset_path,
            )

            assert imp_success is False
            assert "file not found" in msg

    class TestUpdateDatasetMetadata:
        def test_update_dataset_metadata_success(self, monkeypatch):
            from voxkit.storage import datasets
            from voxkit.storage.datasets import (
                create_dataset,
                get_dataset_metadata,
                update_dataset_metadata,
            )

            monkeypatch.setattr(datasets, "get_storage_root", mock_get_storage_root)

            # Create a dataset
            success, message = create_dataset(
                name="dataset_update_test",
                description="Original description",
                original_path=valid_dataset_path,
                cached=False,
                anonymize=False,
                transcribed=False,
            )
            assert success is True
            assert isinstance(message, dict)
            dataset_id = message["id"]

            # Update the dataset metadata
            updates = {
                "description": "Updated description",
                "cached": None,
                "anonymize": True,
                "transcribed": True,
            }
            update_success, update_msg = update_dataset_metadata(dataset_id, updates)

            assert update_success is True
            assert "updated successfully" in update_msg

            # Verify the updates
            metadata = get_dataset_metadata(dataset_id)
            assert metadata is not None
            assert metadata["description"] == "Updated description"
            assert metadata["anonymize"] is True
            assert metadata["transcribed"] is True
            # cached should remain unchanged since we passed None
            assert metadata["cached"] is False

        def test_update_dataset_metadata_nonexistent(self, monkeypatch):
            from voxkit.storage import datasets
            from voxkit.storage.datasets import update_dataset_metadata

            monkeypatch.setattr(datasets, "get_storage_root", mock_get_storage_root)

            updates = {
                "description": "New description",
                "cached": None,
                "anonymize": None,
                "transcribed": None,
            }
            update_success, update_msg = update_dataset_metadata("nonexistent_id_12345", updates)

            assert update_success is False
            assert "not found" in update_msg

        def test_update_dataset_metadata_partial(self, monkeypatch):
            from voxkit.storage import datasets
            from voxkit.storage.datasets import (
                create_dataset,
                get_dataset_metadata,
                update_dataset_metadata,
            )

            monkeypatch.setattr(datasets, "get_storage_root", mock_get_storage_root)

            # Create a dataset
            success, message = create_dataset(
                name="dataset_partial_update_test",
                description="Original description",
                original_path=valid_dataset_path,
                cached=True,
                anonymize=True,
                transcribed=True,
            )
            assert success is True
            assert isinstance(message, dict)
            dataset_id = message["id"]

            # Update only description
            updates = {
                "description": "Only description updated",
                "cached": None,
                "anonymize": None,
                "transcribed": None,
            }
            update_success, _ = update_dataset_metadata(dataset_id, updates)
            assert update_success is True

            # Verify only description changed
            metadata = get_dataset_metadata(dataset_id)
            assert metadata is not None
            assert metadata["description"] == "Only description updated"
            assert metadata["cached"] is True
            assert metadata["anonymize"] is True
            assert metadata["transcribed"] is True

        def test_update_dataset_metadata_missing_keys(self, monkeypatch):
            from voxkit.storage import datasets
            from voxkit.storage.datasets import (
                create_dataset,
                get_dataset_metadata,
                update_dataset_metadata,
            )

            monkeypatch.setattr(datasets, "get_storage_root", mock_get_storage_root)

            # Create a dataset
            success, message = create_dataset(
                name="dataset_missing_keys_test",
                description="Original description",
                original_path=valid_dataset_path,
                cached=True,
                anonymize=True,
                transcribed=True,
            )
            assert success is True
            assert isinstance(message, dict)
            dataset_id = message["id"]

            # Pass a partial dict with only one key — no KeyError should be raised
            update_success, update_msg = update_dataset_metadata(
                dataset_id, {"description": "Partial update"}
            )
            assert update_success is True

            # Only description should change; other fields stay untouched
            metadata = get_dataset_metadata(dataset_id)
            assert metadata is not None
            assert metadata["description"] == "Partial update"
            assert metadata["cached"] is True
            assert metadata["anonymize"] is True
            assert metadata["transcribed"] is True

    class TestCreateDatasetWithAnalysis:
        def test_create_dataset_with_analysis_data(self, monkeypatch):
            from voxkit.storage import datasets
            from voxkit.storage.datasets import _get_datasets_root, create_dataset

            monkeypatch.setattr(datasets, "get_storage_root", mock_get_storage_root)

            analysis_data = [
                {"speaker": "speaker_1", "duration": 10.5, "files": 3},
                {"speaker": "speaker_2", "duration": 15.2, "files": 5},
            ]

            success, message = create_dataset(
                name="dataset_with_analysis",
                description="A dataset with analysis data",
                original_path=valid_dataset_path,
                cached=False,
                anonymize=False,
                transcribed=True,
                analysis_data=analysis_data,
                analysis_method="test_analysis",
            )

            assert success is True
            assert isinstance(message, dict)
            dataset_id = message["id"]

            # Verify CSV file was created
            csv_path = _get_datasets_root() / dataset_id / "test_analysis_summary.csv"
            assert csv_path.exists() is True

            # Verify CSV content
            import csv

            with open(csv_path, "r") as f:
                reader = csv.DictReader(f)
                rows = list(reader)

            assert len(rows) == 2
            assert rows[0]["speaker"] == "speaker_1"
            assert rows[1]["speaker"] == "speaker_2"

        def test_create_dataset_without_analysis_data(self, monkeypatch):
            from voxkit.storage import datasets
            from voxkit.storage.datasets import _get_datasets_root, create_dataset

            monkeypatch.setattr(datasets, "get_storage_root", mock_get_storage_root)

            success, message = create_dataset(
                name="dataset_no_analysis",
                description="A dataset without analysis data",
                original_path=valid_dataset_path,
                cached=False,
                anonymize=False,
                transcribed=True,
            )

            assert success is True
            assert isinstance(message, dict)
            dataset_id = message["id"]

            # Verify no CSV file was created
            dataset_dir = _get_datasets_root() / dataset_id
            csv_files = list(dataset_dir.glob("*_summary.csv"))
            assert len(csv_files) == 0

    class TestValidateDatasetNegativeCases:
        def test_validate_dataset_nonexistent_path(self, monkeypatch):
            from voxkit.storage.datasets import validate_dataset

            nonexistent_path = mock_get_storage_root() / "does_not_exist"
            is_valid, msg = validate_dataset(nonexistent_path)

            assert is_valid is False
            assert "does not exist" in msg

        def test_validate_dataset_file_not_directory(self, monkeypatch):
            from voxkit.storage.datasets import validate_dataset

            # Create a file instead of directory
            file_path = mock_get_storage_root() / "not_a_directory.txt"
            file_path.touch()

            is_valid, msg = validate_dataset(file_path)

            assert is_valid is False
            assert "not a directory" in msg

        def test_validate_dataset_empty_directory(self, monkeypatch):
            from voxkit.storage.datasets import validate_dataset

            is_valid, msg = validate_dataset(empty_dataset_path)

            assert is_valid is False
            assert "empty" in msg

        def test_validate_dataset_files_at_root(self, monkeypatch):
            from voxkit.storage.datasets import validate_dataset

            # Create a dataset with files at root level
            files_at_root_path = mock_get_storage_root() / "fake_datasets" / "files_at_root"
            files_at_root_path.mkdir(parents=True, exist_ok=True)
            (files_at_root_path / "sample.wav").touch()

            is_valid, msg = validate_dataset(files_at_root_path)

            assert is_valid is False
            assert "Expected speaker directories" in msg

        def test_validate_dataset_empty_speaker_directory(self, monkeypatch):
            from voxkit.storage.datasets import validate_dataset

            # Create a dataset with empty speaker directory
            empty_speaker_path = mock_get_storage_root() / "fake_datasets" / "empty_speaker"
            empty_speaker_path.mkdir(parents=True, exist_ok=True)
            (empty_speaker_path / "speaker_1").mkdir(parents=True, exist_ok=True)

            is_valid, msg = validate_dataset(empty_speaker_path)

            assert is_valid is False
            assert "empty" in msg

        def test_validate_dataset_missing_audio_files(self, monkeypatch):
            from voxkit.storage.datasets import validate_dataset

            # Create a dataset with only label files
            no_audio_path = mock_get_storage_root() / "fake_datasets" / "no_audio"
            speaker_path = no_audio_path / "speaker_1"
            speaker_path.mkdir(parents=True, exist_ok=True)
            (speaker_path / "sample.lab").touch()

            is_valid, msg = validate_dataset(no_audio_path)

            assert is_valid is False
            assert "No audio files" in msg

        def test_validate_dataset_missing_label_files(self, monkeypatch):
            from voxkit.storage.datasets import validate_dataset

            is_valid, msg = validate_dataset(invalid_dataset_path)

            assert is_valid is False
            assert "No label files" in msg

        def test_validate_dataset_mismatched_counts(self, monkeypatch):
            from voxkit.storage.datasets import validate_dataset

            # Create a dataset with mismatched audio/label counts
            mismatched_path = mock_get_storage_root() / "fake_datasets" / "mismatched"
            speaker_path = mismatched_path / "speaker_1"
            speaker_path.mkdir(parents=True, exist_ok=True)
            (speaker_path / "sample_1.wav").touch()
            (speaker_path / "sample_2.wav").touch()
            (speaker_path / "sample_1.lab").touch()
            # Missing sample_2.lab

            is_valid, msg = validate_dataset(mismatched_path)

            assert is_valid is False
            assert "Mismatch" in msg
