from pathlib import Path
import pytest
from .test_setup import activate_test_environment, deactivate_test_environment, mock_get_storage_root, ENGINE_IDS
from ..utils import get_storage_root


@pytest.fixture(autouse=True)
def manage_test_environment():
    # Setup before each test
    activate_test_environment(mock_get_storage_root(), ENGINE_IDS)
    yield
    # Cleanup after each test
    deactivate_test_environment(mock_get_storage_root())


class TestModels:
    class TestCreateModel:
        def test_create_model_success(self, monkeypatch):
            from ..models import ModelMetadata, create_model
            from .. import models
            monkeypatch.setattr(models, "get_storage_root", mock_get_storage_root)
            for engine_id in ENGINE_IDS:
                success, message = create_model(
                    engine_id=engine_id,
                    model_name="test_model",
                )
                assert success is True
                assert message is not None
                required_keys = set(ModelMetadata.__annotations__.keys())
                missing = required_keys - set(message.keys())
                assert not missing, f"Missing keys in model metadata: {missing}"
                assert message["name"] == "test_model"
                assert message["engine_id"] == engine_id

    
        def test_create_model_invalid_engine(self, monkeypatch):
            from ..models import create_model
            from .. import models
            monkeypatch.setattr(models, "get_storage_root", mock_get_storage_root)

            success, message = create_model(
                engine_id="INVALID_ENGINE",
                model_name="test_model",
            )
            assert success is False
            assert "Unsupported engine_id" in message
            assert Path(get_storage_root() / "INVALID_ENGINE").exists() is False


        def test_create_multiple_models(self, monkeypatch):
            from ..models import create_model
            from .. import models
            monkeypatch.setattr(models, "get_storage_root", mock_get_storage_root)

            engine_id = ENGINE_IDS[0]
            model_names = [f"model_{i}" for i in range(5)]
            created_ids = set()

            for name in model_names:
                success, message = create_model(
                    engine_id=engine_id,
                    model_name=name,
                )
                assert success is True
                assert message["name"] == name
                assert message["id"] not in created_ids, "Duplicate model ID generated"
                created_ids.add(message["id"])

        def test_model_paths_created(self, monkeypatch):
            from ..models import create_model
            from .. import models
            monkeypatch.setattr(models, "get_storage_root", mock_get_storage_root)

            engine_id = ENGINE_IDS[0]
            success, message = create_model(
                engine_id=engine_id,
                model_name="path_test_model",
            )
            assert success is True

            model_path = Path(message["model_path"])
            data_path = Path(message["data_path"])
            eval_path = Path(message["eval_path"])
            train_path = Path(message["train_path"])

            # Check that the directories exist
            assert model_path.parent.exists(), "Model directory does not exist"
            assert data_path.exists()
            assert eval_path.exists()
            assert train_path.exists()  

        def test_model_fits_modelmetadata(self, monkeypatch):
            from ..models import ModelMetadata, create_model
            from .. import models
            monkeypatch.setattr(models, "get_storage_root", mock_get_storage_root)

            engine_id = ENGINE_IDS[0]
            success, message = create_model(
                engine_id=engine_id,
                model_name="metadata_test_model",
            )
            assert success is True

            # Check that the returned message fits the ModelMetadata TypedDict
            required_keys = set(ModelMetadata.__annotations__.keys())
            missing = required_keys - set(message.keys())
            assert not missing, f"Missing keys in model metadata: {missing}"

    class TestListModels:
        def test_list_models_empty(self, monkeypatch):
            from ..models import list_models
            from .. import models
            monkeypatch.setattr(models, "get_storage_root", mock_get_storage_root)

            engine_id = ENGINE_IDS[0]
            models_list = list_models(engine_id=engine_id)
            assert isinstance(models_list, list)
            assert len(models_list) == 0

        def test_list_models_non_empty(self, monkeypatch):
            from ..models import create_model, list_models
            from .. import models
            monkeypatch.setattr(models, "get_storage_root", mock_get_storage_root)

            engine_id = ENGINE_IDS[0]
            # Create some models
            for i in range(3):
                create_model(
                    engine_id=engine_id,
                    model_name=f"list_test_model_{i}",
                )

            models_list = list_models(engine_id=engine_id)
            assert isinstance(models_list, list)
            assert len(models_list) == 3

        def test_list_models_output_format(self, monkeypatch):
            from ..models import create_model, list_models
            from .. import models
            monkeypatch.setattr(models, "get_storage_root", mock_get_storage_root)

            engine_id = ENGINE_IDS[0]
            # Create a model
            create_model(
                engine_id=engine_id,
                model_name="format_test_model",
            )

            models_list = list_models(engine_id=engine_id)
            assert isinstance(models_list, list)
            assert len(models_list) == 1

            model_metadata = models_list[0]
            required_keys = set(models.ModelMetadata.__annotations__.keys())
            missing = required_keys - set(model_metadata.keys())
            assert not missing, f"Missing keys in model metadata: {missing}"

        def test_list_models_multiple_engines(self, monkeypatch):
            from ..models import create_model, list_models
            from .. import models
            monkeypatch.setattr(models, "get_storage_root", mock_get_storage_root)

            # Create models for different engines
            for engine_id in ENGINE_IDS:
                for i in range(2):
                    create_model(
                        engine_id=engine_id,
                        model_name=f"multi_engine_model_{i}",
                    )

            for engine_id in ENGINE_IDS:
                models_list = list_models(engine_id=engine_id)
                assert isinstance(models_list, list)
                assert len(models_list) == 2

    class TestDeleteModel:
        def test_delete_model_success(self, monkeypatch):
            from ..models import create_model, delete_model, list_models
            from .. import models
            monkeypatch.setattr(models, "get_storage_root", mock_get_storage_root)

            for engine_id in ENGINE_IDS:
                # Create a model to delete
                success, message = create_model(
                    engine_id=engine_id,
                    model_name="delete_test_model",
                )
                assert success is True
                model_id = message["id"]

                # Now delete the model
                del_success, del_message = delete_model(
                    engine_id=engine_id,
                    model_id=model_id,
                )
                assert del_success is True
                assert del_message == "Model deleted successfully."

                # Verify the model is no longer listed
                models_list = list_models(engine_id=engine_id)
                model_ids = [model["id"] for model in models_list]
                assert model_id not in model_ids

        def test_delete_model_nonexistent(self, monkeypatch):
            from ..models import delete_model
            from .. import models
            monkeypatch.setattr(models, "get_storage_root", mock_get_storage_root)

            engine_id = ENGINE_IDS[0]
            fake_model_id = "nonexistent_model_id"

            with pytest.raises(TypeError) as _:
                delete_model(
                    engine_id=engine_id,
                    model_id=fake_model_id,
                )

        def test_delete_model_multiple(self, monkeypatch):
            from ..models import create_model, delete_model, list_models
            from .. import models
            monkeypatch.setattr(models, "get_storage_root", mock_get_storage_root)

            engine_id = ENGINE_IDS[0]
            model_ids = []

            # Create multiple models
            for i in range(3):
                success, message = create_model(
                    engine_id=engine_id,
                    model_name=f"multi_delete_model_{i}",
                )
                assert success is True
                model_ids.append(message["id"])

            # Delete the models one by one
            for model_id in model_ids:
                del_success, _ = delete_model(
                    engine_id=engine_id,
                    model_id=model_id,
                )
                assert del_success is True

            # Verify all models are deleted
            models_list = list_models(engine_id=engine_id)
            assert len(models_list) == 0

        def test_delete_model_invalid_engine(self, monkeypatch):
            from ..models import create_model, delete_model
            from .. import models
            monkeypatch.setattr(models, "get_storage_root", mock_get_storage_root)

            engine_id = ENGINE_IDS[0]
            # Create a model to delete
            success, message = create_model(
                engine_id=engine_id,
                model_name="invalid_engine_delete_model",
            )
            assert success is True
            model_id = message["id"]

            # Attempt to delete with invalid engine_id
            invalid_engine_id = "INVALID_ENGINE"
            with pytest.raises(TypeError) as _:
                delete_model(
                    engine_id=invalid_engine_id,
                    model_id=model_id,
                )

    class TestGetModelMetadata:
        def test_get_model_metadata_success(self, monkeypatch):
            from ..models import create_model, get_model_metadata
            from .. import models
            monkeypatch.setattr(models, "get_storage_root", mock_get_storage_root)

            for engine_id in ENGINE_IDS:
                # Create a model
                success, message = create_model(
                    engine_id=engine_id,
                    model_name="metadata_test_model",
                )
                assert success is True
                model_id = message["id"]

                # Retrieve metadata
                metadata = get_model_metadata(
                    engine_id=engine_id,
                    model_id=model_id,
                )
                assert metadata["id"] == model_id
                assert metadata["name"] == "metadata_test_model"
                assert metadata["engine_id"] == engine_id

        def test_get_model_metadata_nonexistent(self, monkeypatch):
            from ..models import get_model_metadata
            from .. import models
            monkeypatch.setattr(models, "get_storage_root", mock_get_storage_root)

            engine_id = ENGINE_IDS[0]
            fake_model_id = "nonexistent_model_id"

            with pytest.raises(FileNotFoundError) as _:
                get_model_metadata(
                    engine_id=engine_id,
                    model_id=fake_model_id,
                )
    
        def test_get_model_metadata_multiple(self, monkeypatch):
            from ..models import create_model, get_model_metadata
            from .. import models
            monkeypatch.setattr(models, "get_storage_root", mock_get_storage_root)

            engine_id = ENGINE_IDS[0]
            model_ids = []

            # Create multiple models
            for i in range(3):
                success, message = create_model(
                    engine_id=engine_id,
                    model_name=f"multi_metadata_model_{i}",
                )
                assert success is True
                model_ids.append(message["id"])

            # Retrieve and verify metadata for each model
            for model_id in model_ids:
                metadata = get_model_metadata(
                    engine_id=engine_id,
                    model_id=model_id,
                )
                assert metadata["id"] == model_id
                assert metadata["engine_id"] == engine_id

        
        def test_get_model_metadata_invalid_engine(self, monkeypatch):
            from ..models import create_model, get_model_metadata
            from .. import models
            monkeypatch.setattr(models, "get_storage_root", mock_get_storage_root)

            engine_id = ENGINE_IDS[0]
            # Create a model
            success, message = create_model(
                engine_id=engine_id,
                model_name="invalid_engine_metadata_model",
            )
            assert success is True
            model_id = message["id"]

            # Attempt to get metadata with invalid engine_id
            invalid_engine_id = "INVALID_ENGINE"
            with pytest.raises(FileNotFoundError) as _:
                get_model_metadata(
                    engine_id=invalid_engine_id,
                    model_id=model_id,
                )

        def test_get_model_metadata_output_format(self, monkeypatch):
            from ..models import create_model, get_model_metadata
            from .. import models
            monkeypatch.setattr(models, "get_storage_root", mock_get_storage_root)

            engine_id = ENGINE_IDS[0]
            # Create a model
            success, message = create_model(
                engine_id=engine_id,
                model_name="format_metadata_model",
            )
            assert success is True
            model_id = message["id"]

            # Retrieve metadata
            metadata = get_model_metadata(
                engine_id=engine_id,
                model_id=model_id,
            )

            required_keys = set(models.ModelMetadata.__annotations__.keys())
            missing = required_keys - set(metadata.keys())
            assert not missing, f"Missing keys in model metadata: {missing}"

            