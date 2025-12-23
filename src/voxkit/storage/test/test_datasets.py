import os
import shutil
from pathlib import Path

import pytest

from ..datasets import DatasetMetadata
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


def mock_get_storage_root():
    return Path("./temp_test_storage_datasets")


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
            from .. import models
            from ..datasets import validate_dataset

            monkeypatch.setattr(models, "get_storage_root", mock_get_storage_root)

            is_valid, _ = validate_dataset(valid_dataset_path)
            assert is_valid is True

    class TestCreateDataset:
        def test_create_dataset_success_no_cache(self, monkeypatch):
            from .. import models
            from ..datasets import DatasetMetadata, create_dataset

            monkeypatch.setattr(models, "get_storage_root", mock_get_storage_root)

            success, message = create_dataset(
                name="test_dataset",
                description="A test dataset",
                original_path=valid_dataset_path,
                cached=False,
                anonymize=False,
                transcribed=True,
            )

            assert success is True
            for key in DatasetMetadata.__annotations__.keys():
                assert key in message

            assert message["cached"] is False
            assert message["transcribed"] is True
            assert message["anonymize"] is False

            assert message["description"] == "A test dataset"

        def test_create_dataset_success_with_cache(self, monkeypatch):
            from .. import models
            from ..datasets import DatasetMetadata, create_dataset

            monkeypatch.setattr(models, "get_storage_root", mock_get_storage_root)

            success, message = create_dataset(
                name="test_dataset_cached",
                description="A test dataset with caching",
                original_path=valid_dataset_path,
                cached=True,
                anonymize=True,
                transcribed=False,
            )

            assert success is True
            for key in DatasetMetadata.__annotations__.keys():
                assert key in message

            assert message["cached"] is True
            assert message["transcribed"] is False
            assert message["anonymize"] is True
            assert message["description"] == "A test dataset with caching"

        def test_create_dataset_invalid_path(self, monkeypatch):
            from .. import datasets
            from ..datasets import create_dataset

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
            assert "No label files found" in message
            assert invalid_dataset_path.exists() is True

    class TestListDatasets:
        def test_list_datasets_metadata(self, monkeypatch):
            from .. import datasets
            from ..datasets import create_dataset, list_datasets_metadata

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

            datasets = list_datasets_metadata()
            assert len(datasets) >= 2  # At least the two we just created

            names = [ds["name"] for ds in datasets]
            assert "dataset_one" in names
            assert "dataset_two" in names

        def test_list_datasets_output_format(self, monkeypatch):
            from .. import datasets
            from ..datasets import create_dataset, list_datasets_metadata

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

            datasets = list_datasets_metadata()

            # Check that each dataset has all required fields
            for i in range(len(datasets)):
                for key in DatasetMetadata.__annotations__.keys():
                    assert key in datasets[i].keys()

        def test_list_datasets_empty(self, monkeypatch):
            from .. import datasets
            from ..datasets import list_datasets_metadata

            monkeypatch.setattr(datasets, "get_storage_root", mock_get_storage_root)

            # Ensure no datasets exist
            deactivate_test_environment(mock_get_storage_root())
            activate_test_environment(mock_get_storage_root())

            datasets = list_datasets_metadata()
            assert isinstance(datasets, list)
            assert len(datasets) == 0

    class TestGetDatasetMetadata:
        def test_get_dataset_metadata_success(self, monkeypatch):
            from .. import datasets
            from ..datasets import create_dataset, get_dataset_metadata

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
            dataset_id = message["id"]

            metadata = get_dataset_metadata(dataset_id)
            assert success is not None

            for key in DatasetMetadata.__annotations__.keys():
                assert key in metadata

            assert metadata == message

        def test_get_dataset_metadata_nonexistent(self, monkeypatch):
            from .. import datasets
            from ..datasets import get_dataset_metadata

            monkeypatch.setattr(datasets, "get_storage_root", mock_get_storage_root)

            # Attempt to retrieve metadata for a non-existent dataset
            metadata = get_dataset_metadata("nonexistent_id_12345")
            assert metadata is None

        def test_get_dataset_metadata_invalid_id(self, monkeypatch):
            from .. import datasets
            from ..datasets import get_dataset_metadata

            monkeypatch.setattr(datasets, "get_storage_root", mock_get_storage_root)

            # Attempt to retrieve metadata with an invalid ID format
            metadata = get_dataset_metadata("")
            assert metadata is None

    class TestDeleteDataset:
        def test_delete_dataset_success(self, monkeypatch):
            from .. import datasets
            from ..datasets import create_dataset, delete_dataset, get_dataset_metadata

            monkeypatch.setattr(datasets, "get_storage_root", mock_get_storage_root)

            # Create a dataset
            _, message = create_dataset(
                name="dataset_delete_test",
                description="Testing delete_dataset",
                original_path=valid_dataset_path,
                cached=False,
                anonymize=False,
                transcribed=True,
            )
            dataset_id = message["id"]

            # Delete the dataset
            del_success, del_message = delete_dataset(dataset_id)
            assert del_success is True

            # Verify deletion
            metadata = get_dataset_metadata(dataset_id)
            assert metadata is None

        def test_delete_dataset_nonexistent(self, monkeypatch):
            from .. import datasets
            from ..datasets import delete_dataset

            monkeypatch.setattr(datasets, "get_storage_root", mock_get_storage_root)

            # Attempt to delete a non-existent dataset
            del_success, del_message = delete_dataset("nonexistent_id_12345")
            assert del_success is False
            assert "not found" in del_message

        def test_delete_dataset_invalid_id(self, monkeypatch):
            from .. import datasets
            from ..datasets import delete_dataset

            monkeypatch.setattr(datasets, "get_storage_root", mock_get_storage_root)

            # Attempt to delete with an invalid ID format
            del_success, del_message = delete_dataset("")
            assert del_success is False
            assert "cannot be empty" in del_message

        def test_delete_dataset_twice(self, monkeypatch):
            from .. import datasets
            from ..datasets import create_dataset, delete_dataset

            monkeypatch.setattr(datasets, "get_storage_root", mock_get_storage_root)

            # Create a dataset
            _, message = create_dataset(
                name="dataset_delete_twice_test",
                description="Testing delete_dataset twice",
                original_path=valid_dataset_path,
                cached=False,
                anonymize=False,
                transcribed=True,
            )
            dataset_id = message["id"]

            # First deletion
            del_success, del_message = delete_dataset(dataset_id)
            assert del_success is True

            # Second deletion attempt
            del_success, del_message = delete_dataset(dataset_id)
            assert del_success is False
            assert "not found" in del_message

        def test_delete_dataset_invalid_id_format(self, monkeypatch):
            from .. import datasets
            from ..datasets import delete_dataset

            monkeypatch.setattr(datasets, "get_storage_root", mock_get_storage_root)

            # Attempt to delete with an invalid ID format
            del_success, del_message = delete_dataset("!@#$%^&*()")
            assert del_success is False
            assert "not found" in del_message

    class TestExportDataset:
        def test_export_dataset_success(self, monkeypatch, tmp_path):
            from .. import datasets
            from ..datasets import create_dataset, export_dataset

            monkeypatch.setattr(datasets, "get_storage_root", mock_get_storage_root)

            # Create a dataset
            _, message = create_dataset(
                name="dataset_export_test",
                description="Testing export_dataset",
                original_path=valid_dataset_path,
                cached=False,
                anonymize=False,
                transcribed=True,
            )
            dataset_id = message["id"]

            export_path = mock_get_storage_root()
            exp_success, exp_message = export_dataset(dataset_id, export_path)

            assert exp_success is True
            assert "exported successfully" in exp_message

        def test_export_equal(self, monkeypatch):
            from .. import datasets
            from ..datasets import _get_datasets_root, create_dataset, export_dataset

            monkeypatch.setattr(datasets, "get_storage_root", mock_get_storage_root)

            # Create a dataset
            _, message = create_dataset(
                name="dataset_export_equal_test",
                description="Testing export_dataset equality",
                original_path=valid_dataset_path,
                cached=False,
                anonymize=False,
                transcribed=True,
            )
            dataset_id = message["id"]

            export_path = mock_get_storage_root()
            exp_success, exp_message = export_dataset(dataset_id, export_path)

            assert exp_success is True
            assert "exported successfully" in exp_message

            # Dataset metadata
            original_metadata = datasets.get_dataset_metadata(dataset_id)

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
            from .. import datasets
            from ..datasets import create_dataset, import_dataset, validate_dataset

            monkeypatch.setattr(datasets, "get_storage_root", mock_get_storage_root)

            # Create a dataset to export and then import
            _, message = create_dataset(
                name="dataset_import_test",
                description="Testing import_dataset",
                original_path=valid_dataset_path,
                cached=True,
                anonymize=False,
                transcribed=True,
            )
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
            from .. import datasets
            from ..datasets import import_dataset

            monkeypatch.setattr(datasets, "get_storage_root", mock_get_storage_root)

            # Attempt to import from a non-existent path
            imp_success, imp_message = import_dataset(
                mock_get_storage_root() / "nonexistent_path_12345",
            )

            assert imp_success is False
            assert "does not exist" in imp_message

        def test_import_dataset_empty_cache_true(self, monkeypatch):
            from .. import datasets
            from ..datasets import _get_datasets_root, create_dataset, import_dataset

            monkeypatch.setattr(datasets, "get_storage_root", mock_get_storage_root)

            # Create a dataset to export and then import
            _, message = create_dataset(
                name="dataset_import_test",
                description="Testing import_dataset",
                original_path=valid_dataset_path,
                cached=True,
                anonymize=False,
                transcribed=True,
            )

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
