import pytest
from pathlib import Path
from tracker_app import config

def test_directories_exist():
    # setup_directories() should run successfully and create directories
    config.setup_directories()
    
    assert config.DATA_DIR.exists()
    assert config.DATA_DIR.is_dir()
    
    assert config.MODELS_DIR.exists()
    assert config.MODELS_DIR.is_dir()

def test_intervals_are_positive():
    assert config.TRACK_INTERVAL > 0
    assert config.SCREENSHOT_INTERVAL > 0
    assert config.AUDIO_INTERVAL > 0
    assert config.WEBCAM_INTERVAL > 0

def test_db_path_is_string():
    assert isinstance(config.DB_PATH, str)
    assert "sessions.db" in config.DB_PATH
