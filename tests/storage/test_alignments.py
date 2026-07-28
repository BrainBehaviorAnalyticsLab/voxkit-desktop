from pathlib import Path

import pytest

from .test_setup import (
    ENGINE_IDS,
    activate_test_environment,
    deactivate_test_environment,
    mock_get_storage_root,
)


def generate_fake_datasets():
    """Generate a fake dataset for testing purposes."""
    # Create wav/lab file pairs
    dataset_path = mock_get_storage_root() / "fake_datasets" / "valid"
    dataset_path.mkdir(parents=True, exist_ok=True)

    participant_names = ["participant_1", "participant_2"]
    for participant in participant_names:
        wavlab_path = dataset_path / participant
        wavlab_path.mkdir(parents=True, exist_ok=True)

        for i in range(3):
            wav_file = wavlab_path / f"sample_{i}.wav"
            lab_file = wavlab_path / f"sample_{i}.lab"
            wav_file.touch()
            lab_file.touch()

    return dataset_path


@pytest.fixture(autouse=True)
def manage_test_environment():
    # Setup before each test
    activate_test_environment(mock_get_storage_root(), ENGINE_IDS)

    # Generate fake datasets following setup
    generate_fake_datasets()
    yield
    # Cleanup after each test
    deactivate_test_environment(mock_get_storage_root())


@pytest.fixture
def sample_dataset(monkeypatch):
    """Create a sample dataset for testing alignments."""
    from voxkit.storage import datasets
    from voxkit.storage.datasets import create_dataset

    monkeypatch.setattr(datasets, "get_storage_root", mock_get_storage_root)

    dataset_path = mock_get_storage_root() / "fake_datasets" / "valid"

    success, dataset_metadata = create_dataset(
        name="test_dataset",
        description="A test dataset for alignments",
        original_path=str(dataset_path),
        cached=True,
        anonymize=False,
        transcribed=True,
    )

    assert success is True
    assert isinstance(dataset_metadata, dict)
    return dataset_metadata


@pytest.fixture
def sample_model(monkeypatch):
    """Create a sample model for testing alignments."""
    from voxkit.storage import models
    from voxkit.storage.models import create_model

    monkeypatch.setattr(models, "get_storage_root", mock_get_storage_root)

    engine_id = ENGINE_IDS[0]
    success, model_metadata = create_model(
        engine_id=engine_id,
        model_name="test_model",
    )

    assert success is True
    assert isinstance(model_metadata, dict)
    return model_metadata


class TestAlignments:
    class TestCreateAlignment:
        def test_create_alignment_success(self, monkeypatch, sample_dataset, sample_model):
            from voxkit.storage import models
            from voxkit.storage.alignments import AlignmentMetadata, create_alignment

            monkeypatch.setattr(models, "get_storage_root", mock_get_storage_root)

            dataset_id = sample_dataset["id"]
            engine_id = sample_model["engine_id"]
            model_id = sample_model["id"]

            success, result = create_alignment(
                dataset_id=dataset_id,
                engine_id=engine_id,
                model_id=model_id,
            )

            assert success is True
            assert isinstance(result, dict)

            # Verify all required keys are present
            required_keys = set(AlignmentMetadata.__required_keys__)
            assert required_keys.issubset(set(result.keys()))

            # Verify field values
            assert result["engine_id"] == engine_id
            assert result["status"] == "pending"
            assert "id" in result
            assert "alignment_date" in result
            assert "tg_path" in result

    def test_create_alignment_invalid_model(self, monkeypatch, sample_dataset):
        from voxkit.storage import models
        from voxkit.storage.alignments import create_alignment

        monkeypatch.setattr(models, "get_storage_root", mock_get_storage_root)

        dataset_id = sample_dataset["id"]
        engine_id = "INVALID_ENGINE"
        model_id = "NON_EXISTENT_MODEL"

        # Assert error raised for invalid model
        with pytest.raises(FileNotFoundError) as _:
            create_alignment(
                dataset_id=dataset_id,
                engine_id=engine_id,
                model_id=model_id,
            )

    def test_create_alignment_invalid_dataset(self, monkeypatch, sample_model):
        from voxkit.storage import datasets
        from voxkit.storage.alignments import create_alignment

        monkeypatch.setattr(datasets, "get_storage_root", mock_get_storage_root)

        dataset_id = "NON_EXISTENT_DATASET"
        engine_id = sample_model["engine_id"]
        model_id = sample_model["id"]

        # Assert error raised for invalid dataset
        msg, result = create_alignment(
            dataset_id=dataset_id,
            engine_id=engine_id,
            model_id=model_id,
        )

        assert msg is False
        assert isinstance(result, str)
        assert "Dataset" in result

    def test_create_alignment_non_cached_dataset(self, monkeypatch, sample_model):
        from voxkit.storage import datasets
        from voxkit.storage.alignments import AlignmentMetadata, create_alignment
        from voxkit.storage.datasets import create_dataset

        monkeypatch.setattr(datasets, "get_storage_root", mock_get_storage_root)

        # Create a non-cached dataset
        dataset_path = mock_get_storage_root() / "fake_datasets" / "valid"

        success, dataset_metadata = create_dataset(
            name="test_dataset_non_cached",
            description="A test non-cached dataset for alignments",
            original_path=str(dataset_path),
            cached=False,
            anonymize=False,
            transcribed=True,
        )

        assert success is True
        assert isinstance(dataset_metadata, dict)

        dataset_id = dataset_metadata["id"]
        engine_id = sample_model["engine_id"]
        model_id = sample_model["id"]

        success, result = create_alignment(
            dataset_id=dataset_id,
            engine_id=engine_id,
            model_id=model_id,
        )

        assert success is True
        assert isinstance(result, dict)

        # Verify all required keys are present
        required_keys = set(AlignmentMetadata.__required_keys__)
        assert required_keys.issubset(set(result.keys()))

        # Verify field values
        assert result["engine_id"] == engine_id
        assert result["status"] == "pending"
        assert "id" in result
        assert "alignment_date" in result
        assert "tg_path" in result

        # Verify tg_path is within alignment directory for non-cached dataset
        tg_path = Path(result["tg_path"])
        alignment_root = tg_path.parent.parent
        assert alignment_root in tg_path.parents

    class TestCreateCorrectedAlignment:
        def test_create_corrected_alignment_cached_source(
            self, monkeypatch, sample_dataset, sample_model
        ):
            from voxkit.storage import models
            from voxkit.storage.alignments import (
                AlignmentMetadata,
                create_alignment,
                create_corrected_alignment,
            )

            monkeypatch.setattr(models, "get_storage_root", mock_get_storage_root)

            dataset_id = sample_dataset["id"]
            engine_id = sample_model["engine_id"]
            model_id = sample_model["id"]

            success, source_metadata = create_alignment(
                dataset_id=dataset_id, engine_id=engine_id, model_id=model_id
            )
            assert success is True

            # Put a fake TextGrid in the source alignment's tg_path so the
            # baseline copy has something real to carry over.
            source_tg_path = Path(source_metadata["tg_path"])
            (source_tg_path / "participant_1").mkdir(parents=True, exist_ok=True)
            source_file = source_tg_path / "participant_1" / "sample_0.TextGrid"
            source_file.write_text("fake textgrid contents")

            corrected_success, corrected_metadata = create_corrected_alignment(
                dataset_id=dataset_id, source_alignment_id=source_metadata["id"]
            )

            assert corrected_success is True
            assert isinstance(corrected_metadata, dict)

            required_keys = set(AlignmentMetadata.__required_keys__)
            assert required_keys.issubset(set(corrected_metadata.keys()))

            assert corrected_metadata["local"] is True
            assert corrected_metadata["source_alignment_id"] == source_metadata["id"]
            assert corrected_metadata["id"] != source_metadata["id"]
            assert corrected_metadata["alignment_type"] == "corrected"
            # Real engine/model identity is preserved from the source (not
            # replaced with a "corrected" placeholder), so dropdowns keep
            # showing which engine actually produced the TextGrids.
            assert corrected_metadata["engine_id"] == source_metadata["engine_id"]
            assert (
                corrected_metadata["model_metadata"]["name"]
                == source_metadata["model_metadata"]["name"]
            )

            # tg_path must live inside THIS alignment's own directory, never
            # the source alignment's or the original dataset's directory.
            corrected_tg_path = Path(corrected_metadata["tg_path"])
            corrected_alignment_root = corrected_tg_path.parent
            assert corrected_alignment_root.name == corrected_metadata["id"]
            assert source_tg_path not in corrected_tg_path.parents
            assert corrected_tg_path != source_tg_path

            # Baseline copy landed and is byte-identical to the source.
            copied_file = corrected_tg_path / "participant_1" / "sample_0.TextGrid"
            assert copied_file.exists()
            assert copied_file.read_text() == source_file.read_text()

            # Source alignment's own TextGrids must be untouched.
            assert source_file.read_text() == "fake textgrid contents"

        def test_create_corrected_alignment_non_cached_source(self, monkeypatch, sample_model):
            from voxkit.storage import datasets, models
            from voxkit.storage.alignments import create_alignment, create_corrected_alignment
            from voxkit.storage.datasets import create_dataset

            monkeypatch.setattr(datasets, "get_storage_root", mock_get_storage_root)
            monkeypatch.setattr(models, "get_storage_root", mock_get_storage_root)

            dataset_path = mock_get_storage_root() / "fake_datasets" / "valid"
            success, dataset_metadata = create_dataset(
                name="test_dataset_non_cached_corrected",
                description="A non-cached dataset for corrected-alignment tests",
                original_path=str(dataset_path),
                cached=False,
                anonymize=False,
                transcribed=True,
            )
            assert success is True

            dataset_id = dataset_metadata["id"]
            engine_id = sample_model["engine_id"]
            model_id = sample_model["id"]

            success, source_metadata = create_alignment(
                dataset_id=dataset_id, engine_id=engine_id, model_id=model_id
            )
            assert success is True
            # Non-cached source alignments point tg_path at the *original*
            # dataset directory -- exactly the trap this function must avoid
            # inheriting.
            source_tg_path = Path(source_metadata["tg_path"])
            source_tg_path.mkdir(parents=True, exist_ok=True)

            corrected_success, corrected_metadata = create_corrected_alignment(
                dataset_id=dataset_id, source_alignment_id=source_metadata["id"]
            )

            assert corrected_success is True
            assert corrected_metadata["local"] is True

            corrected_tg_path = Path(corrected_metadata["tg_path"])
            assert corrected_tg_path != source_tg_path
            assert dataset_path not in corrected_tg_path.parents
            assert corrected_metadata["id"] in str(corrected_tg_path)

        def test_create_corrected_alignment_invalid_source(self, monkeypatch, sample_dataset):
            from voxkit.storage import datasets
            from voxkit.storage.alignments import create_corrected_alignment

            monkeypatch.setattr(datasets, "get_storage_root", mock_get_storage_root)

            dataset_id = sample_dataset["id"]

            success, result = create_corrected_alignment(
                dataset_id=dataset_id, source_alignment_id="NON_EXISTENT_ALIGNMENT"
            )

            assert success is False
            assert isinstance(result, str)
            assert "not found" in result

        def test_create_corrected_alignment_invalid_dataset(self, monkeypatch):
            from voxkit.storage import datasets
            from voxkit.storage.alignments import create_corrected_alignment

            monkeypatch.setattr(datasets, "get_storage_root", mock_get_storage_root)

            success, result = create_corrected_alignment(
                dataset_id="NON_EXISTENT_DATASET", source_alignment_id="ANY_ALIGNMENT_ID"
            )

            assert success is False
            assert isinstance(result, str)
            assert "Dataset" in result

        def test_create_corrected_alignment_defaults_engine_and_type(
            self, monkeypatch, sample_dataset, sample_model
        ):
            from voxkit.storage import models
            from voxkit.storage.alignments import create_alignment, create_corrected_alignment

            monkeypatch.setattr(models, "get_storage_root", mock_get_storage_root)

            dataset_id = sample_dataset["id"]
            success, source_metadata = create_alignment(
                dataset_id=dataset_id,
                engine_id=sample_model["engine_id"],
                model_id=sample_model["id"],
            )
            assert success is True

            success, corrected_metadata = create_corrected_alignment(
                dataset_id=dataset_id, source_alignment_id=source_metadata["id"]
            )

            assert success is True
            # With no overrides, engine_id falls back to the source's, and
            # alignment_type defaults to "corrected".
            assert corrected_metadata["engine_id"] == source_metadata["engine_id"]
            assert corrected_metadata["alignment_type"] == "corrected"
            assert (
                corrected_metadata["model_metadata"]["name"]
                == source_metadata["model_metadata"]["name"]
            )

        def test_create_corrected_alignment_custom_engine_and_type(
            self, monkeypatch, sample_dataset, sample_model
        ):
            from voxkit.storage import models
            from voxkit.storage.alignments import create_alignment, create_corrected_alignment

            monkeypatch.setattr(models, "get_storage_root", mock_get_storage_root)

            dataset_id = sample_dataset["id"]
            success, source_metadata = create_alignment(
                dataset_id=dataset_id,
                engine_id=sample_model["engine_id"],
                model_id=sample_model["id"],
            )
            assert success is True

            success, corrected_metadata = create_corrected_alignment(
                dataset_id=dataset_id,
                source_alignment_id=source_metadata["id"],
                engine_id="MFA (Nina)",
                alignment_type="corrected-v2",
            )

            assert success is True
            assert corrected_metadata["engine_id"] == "MFA (Nina)"
            assert corrected_metadata["alignment_type"] == "corrected-v2"
            # Overriding engine/type doesn't touch the preserved model name.
            assert (
                corrected_metadata["model_metadata"]["name"]
                == source_metadata["model_metadata"]["name"]
            )

    class TestGetAlignmentType:
        def test_returns_stored_alignment_type(self):
            from voxkit.storage.alignments import get_alignment_type

            for t in ("automatic", "hand", "corrected"):
                meta = {"engine_id": "mfa", "alignment_type": t}
                assert get_alignment_type(meta) == t

        def test_infers_hand_from_engine_id_when_field_missing(self):
            from voxkit.storage.alignments import HAND_ALIGNMENT_SENTINEL, get_alignment_type

            meta = {"engine_id": HAND_ALIGNMENT_SENTINEL}
            assert get_alignment_type(meta) == "hand"

        def test_infers_corrected_from_engine_id_when_field_missing(self):
            from voxkit.storage.alignments import (
                CORRECTED_ALIGNMENT_SENTINEL,
                get_alignment_type,
            )

            meta = {"engine_id": CORRECTED_ALIGNMENT_SENTINEL}
            assert get_alignment_type(meta) == "corrected"

        def test_defaults_to_automatic_when_field_missing(self):
            from voxkit.storage.alignments import get_alignment_type

            meta = {"engine_id": "mfa"}
            assert get_alignment_type(meta) == "automatic"

    class TestGetAlignmentMetadata:
        def test_get_alignment_metadata_success(self, monkeypatch, sample_dataset, sample_model):
            from voxkit.storage import models
            from voxkit.storage.alignments import create_alignment, get_alignment_metadata

            monkeypatch.setattr(models, "get_storage_root", mock_get_storage_root)

            dataset_id = sample_dataset["id"]
            engine_id = sample_model["engine_id"]
            model_id = sample_model["id"]

            success, alignment_metadata = create_alignment(
                dataset_id=dataset_id,
                engine_id=engine_id,
                model_id=model_id,
            )

            assert success is True
            assert isinstance(alignment_metadata, dict)

            alignment_id = alignment_metadata["id"]

            fetched_metadata = get_alignment_metadata(
                dataset_id=dataset_id,
                alignment_id=alignment_id,
            )

            assert fetched_metadata is not None
            assert fetched_metadata["id"] == alignment_id
            assert fetched_metadata["engine_id"] == engine_id

        def test_get_alignment_metadata_invalid_id(self, monkeypatch, sample_dataset, sample_model):
            from voxkit.storage.alignments import create_alignment, get_alignment_metadata

            dataset_id = sample_dataset["id"]
            engine_id = sample_model["engine_id"]
            model_id = sample_model["id"]

            success, alignment_metadata = create_alignment(
                dataset_id=dataset_id,
                engine_id=engine_id,
                model_id=model_id,
            )

            assert success is True
            assert isinstance(alignment_metadata, dict)

            invalid_alignment_id = "NON_EXISTENT_ALIGNMENT"

            fetched_metadata = get_alignment_metadata(
                dataset_id=dataset_id,
                alignment_id=invalid_alignment_id,
            )

            assert fetched_metadata is None

        def test_get_alignment_metadata_invalid_dataset(self, monkeypatch, sample_model):
            from voxkit.storage import datasets
            from voxkit.storage.alignments import get_alignment_metadata

            monkeypatch.setattr(datasets, "get_storage_root", mock_get_storage_root)

            invalid_dataset_id = "NON_EXISTENT_DATASET"
            alignment_id = "ANY_ALIGNMENT_ID"

            fetched_metadata = get_alignment_metadata(
                dataset_id=invalid_dataset_id,
                alignment_id=alignment_id,
            )

            assert fetched_metadata is None

    class TestListAlignments:
        def test_list_alignments_invalid_dataset(self, monkeypatch):
            from voxkit.storage import datasets
            from voxkit.storage.alignments import list_alignments

            monkeypatch.setattr(datasets, "get_storage_root", mock_get_storage_root)
            invalid_dataset_id = "NON_EXISTENT_DATASET"

            alignments_list = list_alignments(dataset_id=invalid_dataset_id)

            assert alignments_list == []

        def test_list_alignments_success(self, monkeypatch, sample_dataset, sample_model):
            from voxkit.storage import datasets
            from voxkit.storage.alignments import create_alignment, list_alignments

            monkeypatch.setattr(datasets, "get_storage_root", mock_get_storage_root)

            dataset_id = sample_dataset["id"]
            engine_id = sample_model["engine_id"]
            model_id = sample_model["id"]

            # Create multiple alignments
            num_alignments = 3
            created_alignment_ids = set()
            for _ in range(num_alignments):
                success, alignment_metadata = create_alignment(
                    dataset_id=dataset_id,
                    engine_id=engine_id,
                    model_id=model_id,
                )
                assert success is True
                assert isinstance(alignment_metadata, dict)
                created_alignment_ids.add(alignment_metadata["id"])

            alignments_list = list_alignments(dataset_id=dataset_id)

            assert len(alignments_list) == num_alignments
            fetched_alignment_ids = {alignment["id"] for alignment in alignments_list}
            assert created_alignment_ids == fetched_alignment_ids

        def test_list_alignments_empty(self, monkeypatch, sample_dataset):
            from voxkit.storage.alignments import list_alignments

            dataset_id = sample_dataset["id"]

            alignments_list = list_alignments(dataset_id=dataset_id)

            assert alignments_list == []

    class TestDeleteAlignment:
        def test_delete_alignment_success(self, sample_dataset, sample_model):
            from voxkit.storage.alignments import (
                create_alignment,
                delete_alignment,
                get_alignment_metadata,
            )

            dataset_id = sample_dataset["id"]
            engine_id = sample_model["engine_id"]
            model_id = sample_model["id"]

            success, alignment_metadata = create_alignment(
                dataset_id=dataset_id,
                engine_id=engine_id,
                model_id=model_id,
            )

            assert success is True
            assert isinstance(alignment_metadata, dict)

            alignment_id = alignment_metadata["id"]

            delete_success, delete_msh = delete_alignment(
                dataset_id=dataset_id,
                alignment_id=alignment_id,
            )

            assert delete_success is True
            assert "deleted successfully" in delete_msh

            # Verify alignment metadata no longer exists
            fetched_metadata = get_alignment_metadata(
                dataset_id=dataset_id,
                alignment_id=alignment_id,
            )

            assert fetched_metadata is None

        def test_delete_alignment_invalid_id(self, sample_dataset):
            from voxkit.storage.alignments import delete_alignment

            dataset_id = sample_dataset["id"]
            invalid_alignment_id = "NON_EXISTENT_ALIGNMENT"

            delete_success, delete_msg = delete_alignment(
                dataset_id=dataset_id,
                alignment_id=invalid_alignment_id,
            )

            assert delete_success is False
            assert "not found" in delete_msg

        def test_delete_alignment_invalid_dataset(self, monkeypatch):
            from voxkit.storage import datasets
            from voxkit.storage.alignments import delete_alignment

            monkeypatch.setattr(datasets, "get_storage_root", mock_get_storage_root)

            invalid_dataset_id = "NON_EXISTENT_DATASET"
            alignment_id = "ANY_ALIGNMENT_ID"

            delete_success, delete_msg = delete_alignment(
                dataset_id=invalid_dataset_id,
                alignment_id=alignment_id,
            )

            assert delete_success is False
            assert "not found" in delete_msg

    class TestUpdateAlignment:
        def test_update_alignment_success(self, sample_dataset, sample_model):
            from voxkit.storage.alignments import (
                create_alignment,
                get_alignment_metadata,
                update_alignment,
            )

            dataset_id = sample_dataset["id"]
            engine_id = sample_model["engine_id"]
            model_id = sample_model["id"]

            success, alignment_metadata = create_alignment(
                dataset_id=dataset_id,
                engine_id=engine_id,
                model_id=model_id,
            )

            assert success is True
            assert isinstance(alignment_metadata, dict)

            alignment_id = alignment_metadata["id"]

            # Update status to completed
            update_success, update_msg = update_alignment(
                dataset_id=dataset_id,
                alignment_id=alignment_id,
                updates={"status": "completed"},
            )

            assert update_success is True

            # Verify status was updated
            fetched_metadata = get_alignment_metadata(
                dataset_id=dataset_id,
                alignment_id=alignment_id,
            )

            assert fetched_metadata is not None
            assert fetched_metadata["status"] == "completed"

        def test_update_alignment_status_case_insensitive(self, sample_dataset, sample_model):
            """Test that status values are normalized to lowercase."""
            from voxkit.storage.alignments import (
                create_alignment,
                get_alignment_metadata,
                update_alignment,
            )

            dataset_id = sample_dataset["id"]
            engine_id = sample_model["engine_id"]
            model_id = sample_model["id"]

            success, alignment_metadata = create_alignment(
                dataset_id=dataset_id,
                engine_id=engine_id,
                model_id=model_id,
            )

            assert success is True
            assert isinstance(alignment_metadata, dict)

            alignment_id = alignment_metadata["id"]

            # Update status with capital letters
            update_success, update_msg = update_alignment(
                dataset_id=dataset_id,
                alignment_id=alignment_id,
                updates={"status": "Completed"},
            )

            assert update_success is True

            # Verify status was normalized to lowercase
            fetched_metadata = get_alignment_metadata(
                dataset_id=dataset_id,
                alignment_id=alignment_id,
            )

            assert fetched_metadata is not None
            assert fetched_metadata["status"] == "completed"

        def test_update_alignment_invalid_id(self, sample_dataset):
            from voxkit.storage.alignments import update_alignment

            dataset_id = sample_dataset["id"]
            invalid_alignment_id = "NON_EXISTENT_ALIGNMENT"

            update_success, update_msg = update_alignment(
                dataset_id=dataset_id,
                alignment_id=invalid_alignment_id,
                updates={"status": "completed"},
            )

            assert update_success is False
            assert "not found" in update_msg

    class TestStatusNormalization:
        def test_list_alignments_normalizes_status(self, monkeypatch, sample_dataset, sample_model):
            """Test that list_alignments normalizes status values to lowercase."""
            import json

            from voxkit.storage import datasets
            from voxkit.storage.alignments import create_alignment, list_alignments

            monkeypatch.setattr(datasets, "get_storage_root", mock_get_storage_root)

            dataset_id = sample_dataset["id"]
            engine_id = sample_model["engine_id"]
            model_id = sample_model["id"]

            # Create an alignment
            success, alignment_metadata = create_alignment(
                dataset_id=dataset_id,
                engine_id=engine_id,
                model_id=model_id,
            )

            assert success is True
            assert isinstance(alignment_metadata, dict)

            alignment_id = alignment_metadata["id"]

            # Manually update the JSON file with capital status
            from voxkit.storage.datasets import _get_dataset_root

            dataset_root = _get_dataset_root(dataset_id)
            alignment_path = dataset_root / "alignments" / alignment_id / "voxkit_alignment.json"

            with open(alignment_path, "r") as f:
                metadata = json.load(f)

            metadata["status"] = "Completed"  # Capital C

            with open(alignment_path, "w") as f:
                json.dump(metadata, f, indent=4)

            # List alignments and check status is normalized
            alignments_list = list_alignments(dataset_id=dataset_id)

            assert len(alignments_list) == 1
            assert alignments_list[0]["status"] == "completed"  # Should be lowercase

        def test_get_alignment_metadata_normalizes_status(
            self, monkeypatch, sample_dataset, sample_model
        ):
            """Test that get_alignment_metadata normalizes status values to lowercase."""
            import json

            from voxkit.storage import datasets
            from voxkit.storage.alignments import create_alignment, get_alignment_metadata

            monkeypatch.setattr(datasets, "get_storage_root", mock_get_storage_root)

            dataset_id = sample_dataset["id"]
            engine_id = sample_model["engine_id"]
            model_id = sample_model["id"]

            # Create an alignment
            success, alignment_metadata = create_alignment(
                dataset_id=dataset_id,
                engine_id=engine_id,
                model_id=model_id,
            )

            assert success is True
            assert isinstance(alignment_metadata, dict)

            alignment_id = alignment_metadata["id"]

            # Manually update the JSON file with capital status
            from voxkit.storage.datasets import _get_dataset_root

            dataset_root = _get_dataset_root(dataset_id)
            alignment_path = dataset_root / "alignments" / alignment_id / "voxkit_alignment.json"

            with open(alignment_path, "r") as f:
                metadata = json.load(f)

            metadata["status"] = "Failed"  # Capital F

            with open(alignment_path, "w") as f:
                json.dump(metadata, f, indent=4)

            # Get alignment metadata and check status is normalized
            fetched_metadata = get_alignment_metadata(
                dataset_id=dataset_id,
                alignment_id=alignment_id,
            )

            assert fetched_metadata is not None
            assert fetched_metadata["status"] == "failed"  # Should be lowercase


class TestGetAlignmentType:
    """get_alignment_type() must read the recorded field, and infer for legacy data
    that predates the alignment_type field entirely."""

    def test_returns_recorded_type(self):
        from voxkit.storage.alignments import get_alignment_type

        meta = {"engine_id": "MFAENGINE", "alignment_type": "corrected"}
        assert get_alignment_type(meta) == "corrected"

    def test_infers_hand_from_legacy_sentinel(self):
        from voxkit.storage.alignments import HAND_ALIGNMENT_SENTINEL, get_alignment_type

        meta = {"engine_id": HAND_ALIGNMENT_SENTINEL}
        assert get_alignment_type(meta) == "hand"

    def test_defaults_to_automatic_for_legacy_data(self):
        from voxkit.storage.alignments import get_alignment_type

        meta = {"engine_id": "MFAENGINE"}
        assert get_alignment_type(meta) == "automatic"
