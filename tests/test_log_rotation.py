"""ROADMAP R20: log rotation is real (RotatingFileHandler / TimedRotatingFileHandler)
and configured from the environment, not a plain FileHandler."""
import logging
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler

import pytest

from src.utils.logger import setup_logging, setup_logging_from_env


@pytest.fixture
def restore_root_logger():
    """setup_logging configures the root logger; restore it afterwards."""
    root = logging.getLogger()
    saved_handlers = root.handlers[:]
    saved_level = root.level
    yield
    for handler in root.handlers[:]:
        handler.close()
    root.handlers[:] = saved_handlers
    root.setLevel(saved_level)


def _file_handlers(logger):
    return [h for h in logger.handlers if isinstance(h, logging.FileHandler)]


def test_size_rotation_produces_a_backup_file(tmp_path, restore_root_logger):
    logger = setup_logging(
        level="INFO",
        log_format="text",
        log_dir=str(tmp_path),
        rotation="size",
        max_bytes=200,
        backup_count=2,
    )
    for _ in range(50):
        logger.info("x" * 100)
    for handler in _file_handlers(logger):
        handler.flush()

    assert (tmp_path / "app.log").exists()
    assert (tmp_path / "app.log.1").exists(), "size rotation did not produce app.log.1"


def test_setup_logging_from_env_honours_size_rotation(tmp_path, restore_root_logger, monkeypatch):
    monkeypatch.setenv("LOG_DIR", str(tmp_path))
    monkeypatch.setenv("LOG_FORMAT", "text")
    monkeypatch.setenv("LOG_ROTATION", "size")
    monkeypatch.setenv("LOG_MAX_BYTES", "200")
    monkeypatch.setenv("LOG_BACKUP_COUNT", "2")

    logger = setup_logging_from_env()
    for _ in range(50):
        logger.info("x" * 100)
    for handler in _file_handlers(logger):
        handler.flush()

    assert (tmp_path / "app.log.1").exists(), "env-configured size rotation did not rotate"


def test_daily_rotation_uses_timed_handler(tmp_path, restore_root_logger):
    logger = setup_logging(
        level="INFO", log_format="text", log_dir=str(tmp_path), rotation="daily"
    )
    assert any(isinstance(h, TimedRotatingFileHandler) for h in _file_handlers(logger))


def test_none_uses_a_plain_file_handler(tmp_path, restore_root_logger):
    logger = setup_logging(
        level="INFO", log_format="text", log_dir=str(tmp_path), rotation="none"
    )
    handlers = _file_handlers(logger)
    assert handlers, "expected a file handler"
    assert not any(
        isinstance(h, (RotatingFileHandler, TimedRotatingFileHandler)) for h in handlers
    )
