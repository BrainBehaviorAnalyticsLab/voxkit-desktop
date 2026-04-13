import logging
from logging.handlers import RotatingFileHandler

import pytest

from voxkit.config import logging_config
from voxkit.config.logging_config import reset_logging, setup_logging


@pytest.fixture(autouse=True)
def _clean_logging(monkeypatch):
    reset_logging()
    monkeypatch.delenv("VOXKIT_DEBUG", raising=False)
    yield
    reset_logging()


def test_setup_logging_creates_rotating_file_handler(tmp_path):
    log_file = tmp_path / "voxkit.log"
    handler = setup_logging(max_bytes=1024, backup_count=2, log_file=log_file)

    assert isinstance(handler, RotatingFileHandler)
    assert handler.maxBytes == 1024
    assert handler.backupCount == 2
    assert log_file.parent.exists()


def test_setup_logging_is_idempotent(tmp_path):
    log_file = tmp_path / "voxkit.log"
    first = setup_logging(max_bytes=1024, backup_count=2, log_file=log_file)
    second = setup_logging(max_bytes=9999, backup_count=9, log_file=log_file)
    assert first is second
    root_handlers = [h for h in logging.getLogger().handlers if isinstance(h, RotatingFileHandler)]
    assert len(root_handlers) == 1


def test_setup_logging_default_level_is_info(tmp_path):
    setup_logging(log_file=tmp_path / "voxkit.log")
    assert logging.getLogger().level == logging.INFO


def test_voxkit_debug_env_raises_level_to_debug(tmp_path, monkeypatch):
    monkeypatch.setenv("VOXKIT_DEBUG", "1")
    setup_logging(log_file=tmp_path / "voxkit.log")
    assert logging.getLogger().level == logging.DEBUG


def test_log_records_are_written_to_file(tmp_path):
    log_file = tmp_path / "voxkit.log"
    setup_logging(log_file=log_file)
    logging.getLogger("voxkit.test").info("hello-world-marker")
    for h in logging.getLogger().handlers:
        h.flush()
    assert "hello-world-marker" in log_file.read_text()


def test_default_constants_match_story_values():
    assert logging_config.DEFAULT_MAX_BYTES == 5 * 1024 * 1024
    assert logging_config.DEFAULT_BACKUP_COUNT == 3
