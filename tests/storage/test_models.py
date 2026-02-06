from pathlib import Path

import pytest

from voxkit.storage.utils import get_storage_root

from .test_setup import (
    ENGINE_IDS,
    activate_test_environment,
    deactivate_test_environment,
    mock_get_storage_root,
)


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
            from voxkit.storage import models
            from voxkit.storage.models import ModelMetadata, create_model

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
            from voxkit.storage import models
            from voxkit.storage.models import create_model

            monkeypatch.setattr(models, "get_storage_root", mock_get_storage_root)

            success, message = create_model(
                engine_id="INVALID_ENGINE",
                model_name="test_model",
            )
            assert success is False
            assert "Unsupported engine_id" in message
            assert Path(get_storage_root() / "INVALID_ENGINE").exists() is False

        def test_create_multiple_models(self, monkeypatch):
            from voxkit.storage import models
            from voxkit.storage.models import create_model

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
            from voxkit.storage import models
            from voxkit.storage.models import create_model

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
            from voxkit.storage import models
            from voxkit.storage.models import ModelMetadata, create_model

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
            from voxkit.storage import models
            from voxkit.storage.models import list_models

            monkeypatch.setattr(models, "get_storage_root", mock_get_storage_root)

            engine_id = ENGINE_IDS[0]
            models_list = list_models(engine_id=engine_id)
            assert isinstance(models_list, list)
            assert len(models_list) == 0

        def test_list_models_non_empty(self, monkeypatch):
            from voxkit.storage import models
            from voxkit.storage.models import create_model, list_models

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
            from voxkit.storage import models
            from voxkit.storage.models import create_model, list_models

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
            from voxkit.storage import models
            from voxkit.storage.models import create_model, list_models

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
            from voxkit.storage import models
            from voxkit.storage.models import create_model, delete_model, list_models

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
            from voxkit.storage import models
            from voxkit.storage.models import delete_model

            monkeypatch.setattr(models, "get_storage_root", mock_get_storage_root)

            engine_id = ENGINE_IDS[0]
            fake_model_id = "nonexistent_model_id"

            success, msg = delete_model(
                engine_id=engine_id,
                model_id=fake_model_id,
            )

            assert success is False
            assert "not found" in msg

        def test_delete_model_multiple(self, monkeypatch):
            from voxkit.storage import models
            from voxkit.storage.models import create_model, delete_model, list_models

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
            from voxkit.storage import models
            from voxkit.storage.models import create_model, delete_model

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

            success, msg = delete_model(
                engine_id=invalid_engine_id,
                model_id=model_id,
            )

            assert success is False
            assert "not found" in msg

    class TestGetModelMetadata:
        def test_get_model_metadata_success(self, monkeypatch):
            from voxkit.storage import models
            from voxkit.storage.models import create_model, get_model_metadata

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
            from voxkit.storage import models
            from voxkit.storage.models import get_model_metadata

            monkeypatch.setattr(models, "get_storage_root", mock_get_storage_root)

            engine_id = ENGINE_IDS[0]
            fake_model_id = "nonexistent_model_id"

            with pytest.raises(FileNotFoundError) as _:
                get_model_metadata(
                    engine_id=engine_id,
                    model_id=fake_model_id,
                )

        def test_get_model_metadata_multiple(self, monkeypatch):
            from voxkit.storage import models
            from voxkit.storage.models import create_model, get_model_metadata

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
            from voxkit.storage import models
            from voxkit.storage.models import create_model, get_model_metadata

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
            from voxkit.storage import models
            from voxkit.storage.models import create_model, get_model_metadata

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

    class TestUpdateModelMetadata:
        def test_update_model_metadata_success(self, monkeypatch):
            from voxkit.storage import models
            from voxkit.storage.models import (
                create_model,
                get_model_metadata,
                update_model_metadata,
            )

            monkeypatch.setattr(models, "get_storage_root", mock_get_storage_root)

            engine_id = ENGINE_IDS[0]
            success, message = create_model(
                engine_id=engine_id,
                model_name="update_test_model",
            )
            assert success is True
            model_id = message["id"]

            # Update the model metadata
            update_success, update_msg = update_model_metadata(
                engine_id=engine_id,
                model_id=model_id,
                updates={"name": "updated_model_name"},
            )

            assert update_success is True
            assert "updated successfully" in update_msg

            # Verify the update
            metadata = get_model_metadata(engine_id=engine_id, model_id=model_id)
            assert metadata["name"] == "updated_model_name"

        def test_update_model_metadata_nonexistent(self, monkeypatch):
            from voxkit.storage import models
            from voxkit.storage.models import update_model_metadata

            monkeypatch.setattr(models, "get_storage_root", mock_get_storage_root)

            engine_id = ENGINE_IDS[0]
            update_success, update_msg = update_model_metadata(
                engine_id=engine_id,
                model_id="nonexistent_model_id",
                updates={"name": "new_name"},
            )

            assert update_success is False
            assert "not found" in update_msg

        def test_update_model_metadata_invalid_engine(self, monkeypatch):
            from voxkit.storage import models
            from voxkit.storage.models import create_model, update_model_metadata

            monkeypatch.setattr(models, "get_storage_root", mock_get_storage_root)

            engine_id = ENGINE_IDS[0]
            success, message = create_model(
                engine_id=engine_id,
                model_name="invalid_engine_update_model",
            )
            assert success is True
            model_id = message["id"]

            # Try to update with invalid engine
            update_success, update_msg = update_model_metadata(
                engine_id="INVALID_ENGINE",
                model_id=model_id,
                updates={"name": "new_name"},
            )

            assert update_success is False
            assert "not found" in update_msg

        def test_update_model_metadata_ignores_unknown_fields(self, monkeypatch):
            from voxkit.storage import models
            from voxkit.storage.models import (
                create_model,
                get_model_metadata,
                update_model_metadata,
            )

            monkeypatch.setattr(models, "get_storage_root", mock_get_storage_root)

            engine_id = ENGINE_IDS[0]
            success, message = create_model(
                engine_id=engine_id,
                model_name="unknown_fields_model",
            )
            assert success is True
            model_id = message["id"]

            # Update with unknown field
            update_success, _ = update_model_metadata(
                engine_id=engine_id,
                model_id=model_id,
                updates={"unknown_field": "value", "name": "updated_name"},
            )

            assert update_success is True

            # Verify only known field was updated
            metadata = get_model_metadata(engine_id=engine_id, model_id=model_id)
            assert metadata["name"] == "updated_name"
            assert "unknown_field" not in metadata

    class TestCreateModelWithSourcePath:
        def test_create_model_with_directory_source(self, monkeypatch):
            from voxkit.storage import models
            from voxkit.storage.models import create_model

            monkeypatch.setattr(models, "get_storage_root", mock_get_storage_root)

            engine_id = ENGINE_IDS[0]

            # Create a source directory with some files
            source_dir = mock_get_storage_root() / "model_source"
            source_dir.mkdir(parents=True, exist_ok=True)
            (source_dir / "model_file.bin").touch()
            (source_dir / "config.json").touch()

            success, message = create_model(
                engine_id=engine_id,
                model_name="model_from_source",
                source_path=source_dir,
            )

            assert success is True
            assert message["name"] == "model_from_source"

            # Verify source files were copied
            model_path = Path(message["model_path"])
            assert model_path.exists()
            assert (model_path / "model_file.bin").exists()
            assert (model_path / "config.json").exists()

        def test_create_model_with_zip_source(self, monkeypatch):
            import zipfile

            from voxkit.storage import models
            from voxkit.storage.models import create_model

            monkeypatch.setattr(models, "get_storage_root", mock_get_storage_root)

            engine_id = ENGINE_IDS[0]

            # Create a zip file
            zip_path = mock_get_storage_root() / "model_source.zip"
            with zipfile.ZipFile(zip_path, "w") as zf:
                zf.writestr("model_data.bin", "fake model data")

            success, message = create_model(
                engine_id=engine_id,
                model_name="model_from_zip",
                source_path=zip_path,
            )

            assert success is True
            assert message["name"] == "model_from_zip"

            # Verify zip was copied as entrypoint.zip
            model_path = Path(message["model_path"])
            assert model_path.exists()
            assert model_path.suffix == ".zip"

        def test_create_model_with_nonexistent_source(self, monkeypatch):
            from voxkit.storage import models
            from voxkit.storage.models import create_model

            monkeypatch.setattr(models, "get_storage_root", mock_get_storage_root)

            engine_id = ENGINE_IDS[0]
            nonexistent_path = mock_get_storage_root() / "nonexistent_source"

            success, message = create_model(
                engine_id=engine_id,
                model_name="model_bad_source",
                source_path=nonexistent_path,
            )

            assert success is False
            assert "does not exist" in message

    class TestImportModels:
        def test_import_models_success(self, monkeypatch):
            import json

            from voxkit.storage import models
            from voxkit.storage.config import MODELS_ROOT
            from voxkit.storage.models import import_models

            monkeypatch.setattr(models, "get_storage_root", mock_get_storage_root)

            engine_id = ENGINE_IDS[0]

            # Create a source directory with models to import
            import_source = mock_get_storage_root() / "import_source"

            # Create a model with proper structure
            model_dir = import_source / "model_to_import"
            model_dir.mkdir(parents=True, exist_ok=True)

            # Create entrypoint.model directory
            entrypoint = model_dir / "entrypoint.model"
            entrypoint.mkdir(parents=True, exist_ok=True)

            # Create metadata file with correct model_path format
            model_path_str = f"/some/path/{engine_id}/{MODELS_ROOT}/old_id/entrypoint.model"
            metadata = {
                "name": "imported_model",
                "engine_id": engine_id,
                "model_path": model_path_str,
                "data_path": "/some/path/data",
                "eval_path": "/some/path/eval",
                "train_path": "/some/path/train",
                "download_date": "January 01, 2024 at 12:00:00 PM",
                "id": "old_id",
            }

            with open(model_dir / "voxkit_model.json", "w") as f:
                json.dump(metadata, f, indent=4)

            success, msg = import_models(engine_id=engine_id, new_models_root=import_source)

            assert success is True
            assert "imported successfully" in msg

        def test_import_models_missing_metadata(self, monkeypatch):
            from voxkit.storage import models
            from voxkit.storage.models import import_models

            monkeypatch.setattr(models, "get_storage_root", mock_get_storage_root)

            engine_id = ENGINE_IDS[0]

            # Create a source directory with model missing metadata
            import_source = mock_get_storage_root() / "import_source_no_meta"
            model_dir = import_source / "model_without_metadata"
            model_dir.mkdir(parents=True, exist_ok=True)

            success, msg = import_models(engine_id=engine_id, new_models_root=import_source)

            assert success is False
            assert "missing metadata file" in msg

        def test_import_models_engine_mismatch(self, monkeypatch):
            import json

            from voxkit.storage import models
            from voxkit.storage.config import MODELS_ROOT
            from voxkit.storage.models import import_models

            monkeypatch.setattr(models, "get_storage_root", mock_get_storage_root)

            engine_id = ENGINE_IDS[0]
            different_engine = ENGINE_IDS[1]

            # Create a source directory with model for different engine
            import_source = mock_get_storage_root() / "import_source_mismatch"
            model_dir = import_source / "model_wrong_engine"
            model_dir.mkdir(parents=True, exist_ok=True)

            model_path_str = f"/some/path/{different_engine}/{MODELS_ROOT}/old_id/entrypoint.model"
            metadata = {
                "name": "wrong_engine_model",
                "engine_id": different_engine,
                "model_path": model_path_str,
                "data_path": "/some/path/data",
                "eval_path": "/some/path/eval",
                "train_path": "/some/path/train",
                "download_date": "January 01, 2024 at 12:00:00 PM",
                "id": "old_id",
            }

            with open(model_dir / "voxkit_model.json", "w") as f:
                json.dump(metadata, f, indent=4)

            success, msg = import_models(engine_id=engine_id, new_models_root=import_source)

            assert success is False
            assert "engine_id mismatch" in msg

        def test_import_models_empty_source(self, monkeypatch):
            from voxkit.storage import models
            from voxkit.storage.models import import_models

            monkeypatch.setattr(models, "get_storage_root", mock_get_storage_root)

            engine_id = ENGINE_IDS[0]

            # Create an empty source directory
            import_source = mock_get_storage_root() / "import_source_empty"
            import_source.mkdir(parents=True, exist_ok=True)

            success, msg = import_models(engine_id=engine_id, new_models_root=import_source)

            assert success is True
            assert "imported successfully" in msg
