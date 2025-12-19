from pathlib import Path
import pytest
from .test_setup import activate_test_environment, deactivate_test_environment, mock_get_storage_root, ENGINE_IDS


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
    from ..datasets import create_dataset
    from .. import datasets
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
    return dataset_metadata


@pytest.fixture
def sample_model(monkeypatch):
    """Create a sample model for testing alignments."""
    from ..models import create_model
    from .. import models
    monkeypatch.setattr(models, "get_storage_root", mock_get_storage_root)
    
    engine_id = ENGINE_IDS[0]
    success, model_metadata = create_model(
        engine_id=engine_id,
        model_name="test_model",
    )
    
    assert success is True
    return model_metadata


class TestAlignments:
    class TestCreateAlignment:
        def test_create_alignment_success(self, monkeypatch, sample_dataset, sample_model):
            from ..alignments import AlignmentMetadata, create_alignment
            from .. import models
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
            required_keys = set(AlignmentMetadata.__annotations__.keys())
            assert required_keys.issubset(set(result.keys()))
            
            # Verify field values
            assert result["engine_id"] == engine_id
            assert result["status"] == "Pending"
            assert "id" in result
            assert "alignment_date" in result
            assert "tg_path" in result

    def test_create_alignment_invalid_model(self, monkeypatch, sample_dataset):
        from ..alignments import create_alignment
        from .. import models
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
        from ..alignments import create_alignment
        from .. import models
        monkeypatch.setattr(models, "get_storage_root", mock_get_storage_root)
        
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
        assert "Dataset" in result

    def test_create_alignment_non_cached_dataset(self, monkeypatch, sample_model):
        from ..datasets import create_dataset
        from ..alignments import create_alignment, AlignmentMetadata
        from .. import datasets, models
        monkeypatch.setattr(datasets, "get_storage_root", mock_get_storage_root)
        monkeypatch.setattr(models, "get_storage_root", mock_get_storage_root)
        
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
        required_keys = set(AlignmentMetadata.__annotations__.keys())
        assert required_keys.issubset(set(result.keys()))
        
        # Verify field values
        assert result["engine_id"] == engine_id
        assert result["status"] == "Pending"
        assert "id" in result
        assert "alignment_date" in result
        assert "tg_path" in result

        # Verify tg_path is within alignment directory for non-cached dataset
        tg_path = Path(result["tg_path"])
        alignment_root = tg_path.parent.parent
        assert alignment_root in tg_path.parents


    class TestGetAlignmentMetadata:        
        
        def test_get_alignment_metadata_success(self, monkeypatch, sample_dataset, sample_model):
            from ..alignments import create_alignment, get_alignment_metadata
            from .. import models
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
            
            alignment_id = alignment_metadata["id"]
            
            fetched_metadata = get_alignment_metadata(
                dataset_id=dataset_id,
                alignment_id=alignment_id,
            )
            
            assert fetched_metadata is not None
            assert fetched_metadata["id"] == alignment_id
            assert fetched_metadata["engine_id"] == engine_id

        def test_get_alignment_metadata_invalid_id(self, monkeypatch, sample_dataset, sample_model):
            from ..alignments import create_alignment, get_alignment_metadata
            
            dataset_id = sample_dataset["id"]
            engine_id = sample_model["engine_id"]
            model_id = sample_model["id"]
            
            success, alignment_metadata = create_alignment(
                dataset_id=dataset_id,
                engine_id=engine_id,
                model_id=model_id,
            )
            
            assert success is True
            
            invalid_alignment_id = "NON_EXISTENT_ALIGNMENT"
            
            fetched_metadata = get_alignment_metadata(
                dataset_id=dataset_id,
                alignment_id=invalid_alignment_id,
            )
            
            assert fetched_metadata is None


        def test_get_alignment_metadata_invalid_dataset(self, monkeypatch, sample_model):
            from ..alignments import get_alignment_metadata
            
            invalid_dataset_id = "NON_EXISTENT_DATASET"
            alignment_id = "ANY_ALIGNMENT_ID"
            
            fetched_metadata = get_alignment_metadata(
                dataset_id=invalid_dataset_id,
                alignment_id=alignment_id,
            )
            
            assert fetched_metadata is None

    class TestListAlignments:

        def test_list_alignments_invalid_dataset(self, monkeypatch):
            from ..alignments import list_alignments
            
            invalid_dataset_id = "NON_EXISTENT_DATASET"
            
            alignments_list = list_alignments(dataset_id=invalid_dataset_id)
            
            assert alignments_list == []

        def test_list_alignments_success(self, monkeypatch, sample_dataset, sample_model):
            from ..alignments import create_alignment, list_alignments
            from .. import models
            monkeypatch.setattr(models, "get_storage_root", mock_get_storage_root)
            
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
                created_alignment_ids.add(alignment_metadata["id"])
            
            alignments_list = list_alignments(dataset_id=dataset_id)
            
            assert len(alignments_list) == num_alignments
            fetched_alignment_ids = {alignment["id"] for alignment in alignments_list}
            assert created_alignment_ids == fetched_alignment_ids
    
        def test_list_alignments_empty(self, monkeypatch, sample_dataset):
            from ..alignments import list_alignments
            
            dataset_id = sample_dataset["id"]
            
            alignments_list = list_alignments(dataset_id=dataset_id)
            
            assert alignments_list == []

    class TestDeleteAlignment:

        def test_delete_alignment_success(self,sample_dataset, sample_model):
            from ..alignments import create_alignment, delete_alignment, get_alignment_metadata
            
            dataset_id = sample_dataset["id"]
            engine_id = sample_model["engine_id"]
            model_id = sample_model["id"]
            
            success, alignment_metadata = create_alignment(
                dataset_id=dataset_id,
                engine_id=engine_id,
                model_id=model_id,
            )
            
            assert success is True
            
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
            from ..alignments import delete_alignment
            
            dataset_id = sample_dataset["id"]
            invalid_alignment_id = "NON_EXISTENT_ALIGNMENT"
            
            delete_success, delete_msg = delete_alignment(
                dataset_id=dataset_id,
                alignment_id=invalid_alignment_id,
            )
            
            assert delete_success is False
            assert "not found" in delete_msg

        def test_delete_alignment_invalid_dataset(self):
            from ..alignments import delete_alignment
            
            invalid_dataset_id = "NON_EXISTENT_DATASET"
            alignment_id = "ANY_ALIGNMENT_ID"
            
            delete_success, delete_msg = delete_alignment(
                dataset_id=invalid_dataset_id,
                alignment_id=alignment_id,
            )
            
            assert delete_success is False
            assert "not found" in delete_msg
