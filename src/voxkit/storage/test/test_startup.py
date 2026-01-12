"""Tests for startup script functionality."""

import shutil
from pathlib import Path
from unittest.mock import patch

import pytest

from ..utils import is_first_launch, mark_first_launch_complete


@pytest.fixture
def temp_storage_root(tmp_path):
    """Create a temporary storage root for testing."""
    storage_root = tmp_path / ".voxkit"
    storage_root.mkdir(parents=True, exist_ok=True)
    
    # Patch get_storage_root to return our temp directory
    with patch("voxkit.storage.utils.get_storage_root", return_value=storage_root):
        yield storage_root
    
    # Cleanup
    if storage_root.exists():
        shutil.rmtree(storage_root)


def test_is_first_launch_when_no_flag_exists(temp_storage_root):
    """Test that is_first_launch returns True when flag file doesn't exist."""
    # Patch get_storage_root for the functions being tested
    with patch("voxkit.storage.utils.get_storage_root", return_value=temp_storage_root):
        assert is_first_launch() is True


def test_is_first_launch_when_flag_exists(temp_storage_root):
    """Test that is_first_launch returns False when flag file exists."""
    flag_file = temp_storage_root / ".first_launch_complete"
    flag_file.touch()
    
    with patch("voxkit.storage.utils.get_storage_root", return_value=temp_storage_root):
        assert is_first_launch() is False


def test_mark_first_launch_complete(temp_storage_root):
    """Test that mark_first_launch_complete creates the flag file."""
    with patch("voxkit.storage.utils.get_storage_root", return_value=temp_storage_root):
        mark_first_launch_complete()
        
        flag_file = temp_storage_root / ".first_launch_complete"
        assert flag_file.exists()


def test_mark_first_launch_complete_creates_storage_root(tmp_path):
    """Test that mark_first_launch_complete creates storage root if it doesn't exist."""
    storage_root = tmp_path / ".voxkit_test"
    
    with patch("voxkit.storage.utils.get_storage_root", return_value=storage_root):
        mark_first_launch_complete()
        
        assert storage_root.exists()
        flag_file = storage_root / ".first_launch_complete"
        assert flag_file.exists()
    
    # Cleanup
    if storage_root.exists():
        shutil.rmtree(storage_root)


def test_first_launch_workflow(temp_storage_root):
    """Test the complete workflow of first launch detection and marking."""
    with patch("voxkit.storage.utils.get_storage_root", return_value=temp_storage_root):
        # Initially should be first launch
        assert is_first_launch() is True
        
        # Mark as complete
        mark_first_launch_complete()
        
        # Should no longer be first launch
        assert is_first_launch() is False
        
        # Marking again should be idempotent
        mark_first_launch_complete()
        assert is_first_launch() is False
