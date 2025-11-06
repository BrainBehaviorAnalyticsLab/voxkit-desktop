
"""
Pytest test suite for paths module
"""
import os
from pathlib import Path
from unittest.mock import patch

import pytest

# Assuming imports from your module
from voxkit.storage.paths import (
    DATA_PREFIX,
    MODEL_PREFIX,
    STORAGE_ROOT,
    TRAIN_ROOT,
    create_train_destination,
    delete_training_run,
    get_storage_root,
    human_readable_date,
    list_models,
    list_modelz,
    machine_readable_date,
    scrub_training_run,
)


@pytest.fixture
def temp_storage_root(tmp_path):
    """Create a temporary storage root directory"""
    storage_dir = tmp_path / ".tpe-speech-analysis"
    storage_dir.mkdir()
    return storage_dir


@pytest.fixture
def mock_storage_root(temp_storage_root):
    """Mock the STORAGE_ROOT to use temp directory"""
    with patch("voxkit.storage.paths.STORAGE_ROOT", str(temp_storage_root)):
        yield temp_storage_root


@pytest.fixture
def sample_date_strings():
    """Sample date strings for testing"""
    return {
        "machine": "20240115_143000",
        "human": "01-15-2024 2:30 pm",
        "invalid": "not-a-date",
    }


@pytest.fixture
def mock_model_structure(temp_storage_root):
    """Create a mock model directory structure"""
    structure = {
        "W2TG": {
            "20240115_120000": {
                "9276_model_test_model_1": {},
                "8372_dataset_test_model_1": {},
            },
            "20240116_150000": {
                "9276_model_test_model_2": {},
                "8372_dataset_test_model_2": {},
            },
        },
        "MFA": {
            "20240117_100000": {
                "9276_model_mfa_model_1": {"model.zip": ""},
                "8372_dataset_mfa_model_1": {},
            },
            "20240118_140000": {
                "9276_model_mfa_model_2": {"model.zip": ""},
            },
        },
    }
    
    # Create the directory structure
    train_root = temp_storage_root / "train"
    train_root.mkdir(exist_ok=True)
    
    for mode, timestamps in structure.items():
        mode_path = train_root / mode
        mode_path.mkdir(exist_ok=True)
        
        for timestamp, models in timestamps.items():
            timestamp_path = mode_path / timestamp
            timestamp_path.mkdir(exist_ok=True)
            
            for model_name, files in models.items():
                model_path = timestamp_path / model_name
                model_path.mkdir(exist_ok=True)
                
                # Create files
                for file_name, content in files.items():
                    file_path = model_path / file_name
                    file_path.write_text(content)
    
    return train_root


# ============================================================================
# Constants Tests
# ============================================================================

class TestConstants:
    """Test module constants"""
    
    def test_storage_root_starts_with_tilde(self):
        """Test that STORAGE_ROOT starts with ~"""
        assert STORAGE_ROOT.startswith("~")
    
    def test_model_prefix_format(self):
        """Test MODEL_PREFIX format"""
        assert MODEL_PREFIX == "9276_model_"
        assert MODEL_PREFIX.endswith("_")
    
    def test_data_prefix_format(self):
        """Test DATA_PREFIX format"""
        assert DATA_PREFIX == "8372_dataset_"
        assert DATA_PREFIX.endswith("_")
    
    def test_train_root_constant(self):
        """Test TRAIN_ROOT constant"""
        assert TRAIN_ROOT == "train"


# ============================================================================
# get_storage_root Tests
# ============================================================================

class TestGetStorageRoot:
    """Test get_storage_root function"""
    
    def test_expands_tilde_path(self):
        """Test that ~ is expanded to home directory"""
        
        result = get_storage_root()
        
        # Should not contain ~
        assert "~" not in result
        # Should be an absolute path
        assert os.path.isabs(result)
        # Should end with .tpe-speech-analysis
        assert result.endswith(".tpe-speech-analysis")
    
    def test_returns_string(self):
        """Test that function returns a string"""
        
        result = get_storage_root()
        
        assert isinstance(result, str)
    
    def test_raises_error_for_invalid_path(self):
        """Test error raised for path not starting with ~"""
        
        with patch("voxkit.storage.paths.STORAGE_ROOT", "/absolute/path"):
            with pytest.raises(ValueError, match="STORAGE_ROOT must be a valid path starting with '~'"):
                get_storage_root()
    
    def test_consistent_results(self):
        """Test that multiple calls return the same result"""
        
        result1 = get_storage_root()
        result2 = get_storage_root()
        
        assert result1 == result2
    
    def test_path_contains_home_directory(self):
        """Test that expanded path contains home directory"""
        
        result = get_storage_root()
        home = str(Path.home())
        
        assert result.startswith(home)


# ============================================================================
# human_readable_date Tests
# ============================================================================

class TestHumanReadableDate:
    """Test human_readable_date function"""
    
    def test_converts_valid_date(self):
        """Test conversion of valid date format"""
        
        result = human_readable_date("20240115_143000")
        
        assert result == "01-15-2024 2:30 pm"
    
    def test_handles_midnight(self):
        """Test conversion of midnight time"""
        
        result = human_readable_date("20240115_000000")
        
        assert result == "01-15-2024 12:00 am"
    
    def test_handles_noon(self):
        """Test conversion of noon time"""
        
        result = human_readable_date("20240115_120000")
        
        assert result == "01-15-2024 12:00 pm"
    
    def test_removes_leading_zero_from_hour(self):
        """Test that leading zero is removed from hour"""
        
        result = human_readable_date("20240115_090000")
        
        # Should be "9:00 am" not "09:00 am"
        assert "9:00 am" in result
        assert "09:00" not in result
    
    def test_handles_invalid_date_gracefully(self):
        """Test that invalid dates are returned as-is"""
        
        invalid_date = "not-a-date"
        result = human_readable_date(invalid_date)
        
        assert result == invalid_date
    
    def test_handles_wrong_format(self):
        """Test handling of wrong format"""
        
        result = human_readable_date("2024-01-15 14:30:00")
        
        # Should return input unchanged
        assert result == "2024-01-15 14:30:00"
    
    @pytest.mark.parametrize("input_date,expected", [
        ("20240101_000000", "01-01-2024 12:00 am"),
        ("20241231_235959", "12-31-2024 11:59 pm"),
        ("20240630_183045", "06-30-2024 6:30 pm"),
        ("20240215_010000", "02-15-2024 1:00 am"),
    ])
    def test_various_dates(self, input_date, expected):
        """Test conversion of various date formats"""
        
        result = human_readable_date(input_date)
        
        assert result == expected
    
    def test_am_pm_lowercase(self):
        """Test that AM/PM is lowercase"""
        
        result = human_readable_date("20240115_143000")
        
        assert " pm" in result or " am" in result
        assert " PM" not in result and " AM" not in result


# ============================================================================
# machine_readable_date Tests
# ============================================================================

class TestMachineReadableDate:
    """Test machine_readable_date function"""
    
    def test_converts_valid_date(self):
        """Test conversion of valid human-readable date"""
        
        result = machine_readable_date("01-15-2024 2:30 pm")
        
        assert result == "20240115_143000"
    
    def test_handles_midnight(self):
        """Test conversion of midnight"""
        
        result = machine_readable_date("01-15-2024 12:00 am")
        
        assert result == "20240115_000000"
    
    def test_handles_noon(self):
        """Test conversion of noon"""
        
        result = machine_readable_date("01-15-2024 12:00 pm")
        
        assert result == "20240115_120000"
    
    def test_handles_invalid_date_gracefully(self):
        """Test that invalid dates are returned as-is"""
        
        invalid_date = "not-a-date"
        result = machine_readable_date(invalid_date)
        
        assert result == invalid_date
    
    def test_round_trip_conversion(self):
        """Test that human->machine->human conversion works"""
        
        original = "20240115_143000"
        human = human_readable_date(original)
        back_to_machine = machine_readable_date(human)
        
        assert back_to_machine == original
    
    @pytest.mark.parametrize("input_date,expected", [
        ("01-01-2024 12:00 am", "20240101_000000"),
        ("12-31-2024 11:59 pm", "20241231_235900"),  # Note: seconds will be 00
        ("06-30-2024 6:30 pm", "20240630_183000"),
        ("02-15-2024 1:00 am", "20240215_010000"),
    ])
    def test_various_dates(self, input_date, expected):
        """Test conversion of various date formats"""
        
        result = machine_readable_date(input_date)
        
        assert result == expected
    
    def test_handles_extra_whitespace(self):
        """Test that extra whitespace is handled"""
        
        result = machine_readable_date("  01-15-2024 2:30 pm  ")
        
        assert result == "20240115_143000"


# ============================================================================
# list_models Tests
# ============================================================================

class TestListModels:
    """Test list_models function"""
    
    def test_lists_w2tg_models_without_date(self, mock_storage_root, mock_model_structure):
        """Test listing W2TG models without dates"""
        
        with patch("voxkit.storage.paths.get_storage_root", return_value=str(mock_storage_root)):
            result = list_models("W2TG", add_date=False)
        
        assert isinstance(result, dict)
        assert "test_model_1" in result
        assert "test_model_2" in result
    
    def test_lists_w2tg_models_with_date(self, mock_storage_root, mock_model_structure):
        """Test listing W2TG models with dates"""
        
        with patch("voxkit.storage.paths.get_storage_root", return_value=str(mock_storage_root)):
            result = list_models("W2TG", add_date=True)
        
        # Keys should include date information
        for key in result.keys():
            if "test_model" in key:
                assert "(" in key and ")" in key  # Date should be in parentheses
    
    def test_lists_mfa_models_without_date(self, mock_storage_root, mock_model_structure):
        """Test listing MFA models without dates"""
        
        with patch("voxkit.storage.paths.get_storage_root", return_value=str(mock_storage_root)):
            result = list_models("MFA", add_date=False)
        
        assert isinstance(result, dict)
        assert "mfa_model_1" in result
        assert "mfa_model_2" in result
    
    def test_mfa_model_paths_include_zip(self, mock_storage_root, mock_model_structure):
        """Test that MFA model paths include model.zip"""
        
        with patch("voxkit.storage.paths.get_storage_root", return_value=str(mock_storage_root)):
            result = list_models("MFA", add_date=False)
        
        for path in result.values():
            assert path.endswith("model.zip")
    
    def test_returns_empty_dict_for_nonexistent_path(self, mock_storage_root):
        """Test returns empty dict when mode path doesn't exist"""
        
        with patch("voxkit.storage.paths.get_storage_root", return_value=str(mock_storage_root)):
            result = list_models("W2TG", add_date=False)
        
        # Should return empty dict if no models directory exists
        if not (mock_storage_root / "train" / "W2TG").exists():
            assert result == {}
    
    def test_skips_mfa_models_without_zip(self, mock_storage_root, mock_model_structure):
        """Test that MFA models without model.zip are skipped"""
        
        # Remove model.zip from one model
        zip_path = mock_model_structure / "MFA" / "20240117_100000" / "9276_model_mfa_model_1" / "model.zip"
        if zip_path.exists():
            zip_path.unlink()
        
        with patch("voxkit.storage.paths.get_storage_root", return_value=str(mock_storage_root)):
            result = list_models("MFA", add_date=False)
        
        # mfa_model_1 should not be in results
        assert "mfa_model_1" not in result
    
    def test_handles_exception_gracefully(self, mock_storage_root):
        """Test that exceptions are handled and empty dict is returned"""
        
        with patch("voxkit.storage.paths.get_storage_root", side_effect=Exception("Test error")):
            result = list_models("W2TG", add_date=False)
        
        assert result == {}
    
    def test_model_prefix_is_stripped(self, mock_storage_root, mock_model_structure):
        """Test that MODEL_PREFIX is stripped from model names"""
        
        with patch("voxkit.storage.paths.get_storage_root", return_value=str(mock_storage_root)):
            result = list_models("W2TG", add_date=False)
        
        # Model names should not contain prefix
        for model_name in result.keys():
            assert not model_name.startswith(MODEL_PREFIX)


# ============================================================================
# list_modelz Tests
# ============================================================================

class TestListModelz:
    """Test list_modelz function (enhanced version)"""
    
    def test_returns_dict_with_metadata(self, mock_storage_root, mock_model_structure):
        """Test that list_modelz returns dict with metadata"""
        
        with patch("voxkit.storage.paths.get_storage_root", return_value=str(mock_storage_root)):
            result = list_modelz("W2TG", add_date=True)
        
        assert isinstance(result, dict)
        
        # Check structure
        for model_name, metadata in result.items():
            assert isinstance(metadata, dict)
            assert "path" in metadata
            assert "train_root" in metadata
            if "test_model" in model_name:
                assert "date" in metadata
                assert "time" in metadata
    
    def test_metadata_without_date(self, mock_storage_root, mock_model_structure):
        """Test list_modelz without date includes minimal metadata"""
        
        with patch("voxkit.storage.paths.get_storage_root", return_value=str(mock_storage_root)):
            result = list_modelz("W2TG", add_date=False)
        
        for model_name, metadata in result.items():
            assert "path" in metadata
            assert "train_root" in metadata
            # Should not have date/time when add_date=False
            assert "date" not in metadata or metadata.get("date") is None
    
    def test_mfa_paths_include_zip_in_metadata(self, mock_storage_root, mock_model_structure):
        """Test that MFA model paths in metadata include model.zip"""
        
        with patch("voxkit.storage.paths.get_storage_root", return_value=str(mock_storage_root)):
            result = list_modelz("MFA", add_date=False)
        
        for metadata in result.values():
            assert metadata["path"].endswith("model.zip")
    
    def test_skips_mfa_models_without_zip(self, mock_storage_root, mock_model_structure):
        """Test that MFA models without model.zip are skipped"""
        
        # Remove model.zip
        zip_path = mock_model_structure / "MFA" / "20240117_100000" / "9276_model_mfa_model_1" / "model.zip"
        if zip_path.exists():
            zip_path.unlink()
        
        with patch("voxkit.storage.paths.get_storage_root", return_value=str(mock_storage_root)):
            result = list_modelz("MFA", add_date=False)
        
        assert "mfa_model_1" not in result
    
    def test_date_time_split_correctly(self, mock_storage_root, mock_model_structure):
        """Test that date and time are split correctly"""
        
        with patch("voxkit.storage.paths.get_storage_root", return_value=str(mock_storage_root)):
            result = list_modelz("W2TG", add_date=True)
        
        for metadata in result.values():
            if "date" in metadata:
                # Date should be in MM-DD-YYYY format
                assert len(metadata["date"].split("-")) == 3
                # Time should contain colon
                if "time" in metadata:
                    assert ":" in metadata["time"]
    
    def test_train_root_matches_timestamp(self, mock_storage_root, mock_model_structure):
        """Test that train_root matches the timestamp directory"""
        
        with patch("voxkit.storage.paths.get_storage_root", return_value=str(mock_storage_root)):
            result = list_modelz("W2TG", add_date=False)
        
        for metadata in result.values():
            # train_root should be a timestamp format
            train_root = metadata["train_root"]
            # Should match YYYYMMDD_HHMMSS format
            assert len(train_root) == 15
            assert "_" in train_root


# ============================================================================
# scrub_training_run Tests
# ============================================================================

class TestScrubTrainingRun:
    """Test scrub_training_run function"""
    
    def test_deletes_existing_training_run(self, mock_storage_root, mock_model_structure):
        """Test that existing training run is deleted"""
        
        train_path = mock_model_structure / "W2TG" / "20240115_120000"
        assert train_path.exists()
        
        with patch("voxkit.storage.paths.get_storage_root", return_value=str(mock_storage_root)):
            scrub_training_run("W2TG", "20240115_120000")
        
        assert not train_path.exists()
    
    def test_raises_error_for_nonexistent_path(self, mock_storage_root):
        """Test that FileNotFoundError is raised for nonexistent path"""
        
        with patch("voxkit.storage.paths.get_storage_root", return_value=str(mock_storage_root)):
            with pytest.raises(FileNotFoundError, match="Training run path does not exist"):
                scrub_training_run("W2TG", "nonexistent_20240101_000000")
    
    def test_deletes_entire_directory_tree(self, mock_storage_root, mock_model_structure):
        """Test that entire directory tree is deleted"""
        
        # Verify subdirectories exist
        train_path = mock_model_structure / "W2TG" / "20240115_120000"
        model_path = train_path / "9276_model_test_model_1"
        assert model_path.exists()
        
        with patch("voxkit.storage.paths.get_storage_root", return_value=str(mock_storage_root)):
            scrub_training_run("W2TG", "20240115_120000")
        
        # Entire tree should be gone
        assert not train_path.exists()
        assert not model_path.exists()
    
    def test_works_with_mfa_engine(self, mock_storage_root, mock_model_structure):
        """Test scrub_training_run works with MFA engine"""
        
        train_path = mock_model_structure / "MFA" / "20240117_100000"
        assert train_path.exists()
        
        with patch("voxkit.storage.paths.get_storage_root", return_value=str(mock_storage_root)):
            scrub_training_run("MFA", "20240117_100000")
        
        assert not train_path.exists()
    
    def test_does_not_affect_other_training_runs(self, mock_storage_root, mock_model_structure):
        """Test that other training runs are not affected"""
        
        train_path_1 = mock_model_structure / "W2TG" / "20240115_120000"
        train_path_2 = mock_model_structure / "W2TG" / "20240116_150000"
        
        assert train_path_1.exists()
        assert train_path_2.exists()
        
        with patch("voxkit.storage.paths.get_storage_root", return_value=str(mock_storage_root)):
            scrub_training_run("W2TG", "20240115_120000")
        
        # Only first path should be deleted
        assert not train_path_1.exists()
        assert train_path_2.exists()


# ============================================================================
# create_train_destination Tests
# ============================================================================

class TestCreateTrainDestination:
    """Test create_train_destination function"""
    
    def test_creates_w2tg_directories(self, mock_storage_root):
        """Test that W2TG directories are created"""
        
        with patch("voxkit.storage.paths.get_storage_root", return_value=str(mock_storage_root)):
            data_path, model_path, train_path, eval_path = create_train_destination(
                "test_model", "W2TG"
            )
        
        # All paths should be strings
        assert isinstance(data_path, str)
        assert isinstance(model_path, str)
        assert isinstance(train_path, str)
        assert isinstance(eval_path, str)
        
        # Directories should exist
        assert os.path.exists(data_path)
        assert os.path.exists(model_path)
        assert os.path.exists(train_path)
    
    def test_creates_mfa_directories(self, mock_storage_root):
        """Test that MFA directories are created"""
        
        with patch("voxkit.storage.paths.get_storage_root", return_value=str(mock_storage_root)):
            data_path, model_path, train_path, eval_path = create_train_destination(
                "test_model", "MFA"
            )
        
        # MFA model path should end with model.zip
        assert model_path.endswith("model.zip")
        
        # Parent directory of model.zip should exist
        model_dir = os.path.dirname(model_path)
        assert os.path.exists(model_dir)
        assert os.path.exists(data_path)
    
    def test_directory_names_include_prefixes(self, mock_storage_root):
        """Test that directory names include correct prefixes"""
        
        with patch("voxkit.storage.paths.get_storage_root", return_value=str(mock_storage_root)):
            data_path, model_path, train_path, eval_path = create_train_destination(
                "my_model", "W2TG"
            )
        
        # Model path should contain MODEL_PREFIX
        assert MODEL_PREFIX in model_path
        # Data path should contain DATA_PREFIX
        assert DATA_PREFIX in data_path
    
    def test_uses_timestamp_in_path(self, mock_storage_root):
        """Test that timestamp is used in path"""
        
        with patch("voxkit.storage.paths.get_storage_root", return_value=str(mock_storage_root)):
            _, _, train_path, _ = create_train_destination("test_model", "W2TG")
        
        # Train path should contain a timestamp (YYYYMMDD_HHMMSS format)
        # Extract last directory name
        timestamp = os.path.basename(train_path)
        assert len(timestamp) == 15  # YYYYMMDD_HHMMSS
        assert "_" in timestamp
    
    def test_multiple_calls_create_different_timestamps(self, mock_storage_root):
        """Test that multiple calls create different timestamp directories"""
        import time

        
        with patch("voxkit.storage.paths.get_storage_root", return_value=str(mock_storage_root)):
            _, _, train_path_1, _ = create_train_destination("model1", "W2TG")
            time.sleep(1)  # Ensure different timestamp
            _, _, train_path_2, _ = create_train_destination("model2", "W2TG")
        
        # Paths should be different
        assert train_path_1 != train_path_2
    
    def test_returns_correct_number_of_paths(self, mock_storage_root):
        """Test that function returns 4 paths"""
        
        with patch("voxkit.storage.paths.get_storage_root", return_value=str(mock_storage_root)):
            result = create_train_destination("test_model", "W2TG")
        
        assert len(result) == 4
    
    def test_eval_path_format(self, mock_storage_root):
        """Test that eval path has correct format"""
        
        with patch("voxkit.storage.paths.get_storage_root", return_value=str(mock_storage_root)):
            _, _, _, eval_path = create_train_destination("test_model", "W2TG")
        
        # Should contain eval_output_textgrids
        assert "eval_output_textgrids" in eval_path
    
    def test_model_name_in_paths(self, mock_storage_root):
        """Test that model name appears in paths"""
        
        model_name = "my_custom_model"
        
        with patch("voxkit.storage.paths.get_storage_root", return_value=str(mock_storage_root)):
            data_path, model_path, _, _ = create_train_destination(model_name, "W2TG")
        
        assert model_name in data_path
        assert model_name in model_path


# ============================================================================
# delete_training_run Tests
# ============================================================================

class TestDeleteTrainingRun:
    """Test delete_training_run function"""
    
    def test_deletes_existing_training_run(self, mock_storage_root, mock_model_structure):
        """Test that existing training run is deleted"""
        
        train_path = mock_model_structure / "W2TG" / "20240115_120000"
        assert train_path.exists()
        
        with patch("voxkit.storage.paths.get_storage_root", return_value=str(mock_storage_root)):
            delete_training_run("W2TG", "20240115_120000")
        
        assert not train_path.exists()
    
    def test_raises_error_for_nonexistent_path(self, mock_storage_root):
        """Test that FileNotFoundError is raised for nonexistent path"""
        
        with patch("voxkit.storage.paths.get_storage_root", return_value=str(mock_storage_root)):
            with pytest.raises(FileNotFoundError, match="Training run path does not exist"):
                delete_training_run("W2TG", "nonexistent_20240101_000000")
    
    def test_functionally_identical_to_scrub(self, mock_storage_root, mock_model_structure):
        """Test that delete_training_run behaves same as scrub_training_run"""
        
        # Test with two similar paths
        train_path_1 = mock_model_structure / "W2TG" / "20240115_120000"
        train_path_2 = mock_model_structure / "W2TG" / "20240116_150000"
        
        with patch("voxkit.storage.paths.get_storage_root", return_value=str(mock_storage_root)):
            delete_training_run("W2TG", "20240115_120000")
            scrub_training_run("W2TG", "20240116_150000")
        
        # Both should be deleted
        assert not train_path_1.exists()
        assert not train_path_2.exists()


# ============================================================================
# Integration Tests
# ============================================================================

class TestIntegration:
    """Integration tests combining multiple functions"""
    
    def test_create_list_delete_workflow(self, mock_storage_root):
        """Test complete workflow: create, list, delete"""
        
        with patch("voxkit.storage.paths.get_storage_root", return_value=str(mock_storage_root)):
            # Create
            data_path, model_path, train_path, eval_path = create_train_destination(
                "integration_test", "W2TG"
            )
            
            # List
            models = list_modelz("W2TG", add_date=False)
            assert "integration_test" in models
            
            # Delete
            train_code = os.path.basename(train_path)
            delete_training_run("W2TG", train_code)
            
            # Verify deletion
            assert not os.path.exists(train_path)
    
    def test_date_conversion_round_trip(self):
        """Test round trip date conversion"""
        
        original = "20240115_143000"
        
        # Convert to human readable
        human = human_readable_date(original)
        assert human == "01-15-2024 2:30 pm"
        
        # Convert back to machine readable
        machine = machine_readable_date(human)
        assert machine == original
    
    def test_model_listing_consistency(self, mock_storage_root, mock_model_structure):
        """Test that list_models and list_modelz return consistent results"""
        
        with patch("voxkit.storage.paths.get_storage_root", return_value=str(mock_storage_root)):
            models_1 = list_models("W2TG", add_date=False)
            models_2 = list_modelz("W2TG", add_date=False)
        
        # Both should find the same model names (keys)
        # Note: list_modelz returns dict with metadata, list_models returns dict with paths
        assert set(models_1.keys()) == set(models_2.keys())


# ============================================================================
# Edge Cases Tests
# ============================================================================

class TestEdgeCases:
    """Test edge cases and boundary conditions"""
    
    def test_empty_model_name(self, mock_storage_root):
        """Test behavior with empty model name"""
        
        with patch("voxkit.storage.paths.get_storage_root", return_value=str(mock_storage_root)):
            # Should not crash
            data_path, model_path, train_path, eval_path = create_train_destination(
                "", "W2TG"
            )
            
            # Paths should still be created
            assert os.path.exists(train_path)
    
    def test_special_characters_in_model_name(self, mock_storage_root):
        """Test model names with special characters"""
        
        with patch("voxkit.storage.paths.get_storage_root", return_value=str(mock_storage_root)):
            # Should handle special characters
            data_path, model_path, train_path, eval_path = create_train_destination(
                "model-with_special.chars", "W2TG"
            )
            
            assert "model-with_special.chars" in model_path
    
    def test_very_long_model_name(self, mock_storage_root):
        """Test with very long model name"""
        
        long_name = "a" * 200
        
        with patch("voxkit.storage.paths.get_storage_root", return_value=str(mock_storage_root)):
            try:
                data_path, model_path, train_path, eval_path = create_train_destination(
                    long_name, "W2TG"
                )
                # If it succeeds, verify path exists
                assert os.path.exists(train_path)
            except OSError:
                # May fail on some systems due to path length limits
                pytest.skip("Path length limit exceeded")
    
    def test_concurrent_directory_creation(self, mock_storage_root):
        """Test that exist_ok prevents errors on concurrent creation"""
        
        with patch("voxkit.storage.paths.get_storage_root", return_value=str(mock_storage_root)):
            # Create same model twice (simulating race condition)
            # Should not raise error due to exist_ok=True
            create_train_destination("concurrent_test", "W2TG")
            # This might create different timestamp, but shouldn't crash
            create_train_destination("concurrent_test", "W2TG")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])