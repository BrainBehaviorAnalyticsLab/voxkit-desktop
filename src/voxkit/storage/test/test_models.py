from pathlib import Path

import pytest

from .test_setup import activate_test_environment, deactivate_test_environment

ENGINE_IDS = ["ENGINE_A", "ENGINE_B", "ENGINE_C"]

@pytest.fixture(autouse=True)
def manage_test_environment():
    # Setup before each test
    activate_test_environment(ENGINE_IDS)
    yield
    # Cleanup after each test
    deactivate_test_environment()

class TestModels:
    class TestCreateModel:
        def test_create_model_success(self):
            from ..models import ModelMetadata, create_model

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
                assert Path(message["model_path"]).exists() 
                assert Path(message["data_path"]).exists()
                assert Path(message["eval_path"]).exists()
                assert Path(message["train_path"]).exists()