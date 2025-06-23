import builtins
import io
import logging
import os
import pytest
import yaml

from unittest.mock import patch, mock_open, MagicMock
from box import Box

from nethawk.core.config import Config  # replace your_module with actual module name


@pytest.fixture
def sample_yaml():
    return """
    key1: value1
    nested:
      key2: value2
    """

@pytest.fixture
def sample_dict():
    return {
        "key1": "value1",
        "nested": {
            "key2": "value2"
        }
    }

def make_mock_files(data_yaml):
    """Create a mock context for pkg_resources.files(...).joinpath(...).open(...)"""
    mock_file = io.StringIO(data_yaml)
    mock_joinpath = MagicMock()
    mock_joinpath.open = MagicMock(return_value=mock_file)
    mock_files = MagicMock()
    mock_files.joinpath = MagicMock(return_value=mock_joinpath)
    return mock_files

@patch("os.makedirs")
@patch("os.path.exists")
@patch("importlib.resources.files")
@patch("builtins.open", new_callable=mock_open, read_data="key1: value1\nnested:\n  key2: value2\n")
@patch("os.getenv")
@patch.object(Config, '_load_config', return_value={})
def test_publish_creates_default_config(mock_load_config, mock_getenv, mock_open_file, mock_files, mock_exists, mock_makedirs, sample_yaml):
    # Setup mocks
    mock_getenv.side_effect = lambda k: None  # simulate no sudo
    mock_exists.return_value = False  # config file does not exist
    mock_files.return_value = make_mock_files(sample_yaml)
    
    cfg = Config()
    cfg.publish()
    
    mock_makedirs.assert_called_once_with(cfg._default_dest_dir, exist_ok=True)
    mock_files.return_value.joinpath.assert_called_with(cfg.DEFAULT_CONFIG_NAME)
    mock_open_file.assert_called_with(cfg._default_config_path, "wb")

@patch("os.path.isfile")
@patch("builtins.open", new_callable=mock_open, read_data="key1: value1\nnested:\n  key2: value2\n")
def test_use_valid_custom_config(mock_open_file, mock_isfile, sample_dict):
    mock_isfile.return_value = True
    cfg = Config()
    cfg.use("custom_config.yaml")
    assert isinstance(cfg._box, Box)
    assert cfg._box.key1 == "value1"
    assert cfg._custom_config_path == "custom_config.yaml"

@patch("os.path.isfile")
def test_use_invalid_path_raises(mock_isfile):
    mock_isfile.return_value = False
    cfg = Config()
    with pytest.raises(FileNotFoundError):
        cfg.use("nonexistent.yaml")

# @patch("builtins.open", new_callable=mock_open, read_data="not: [valid, yaml")
# @patch("os.path.isfile")
# def test_use_invalid_yaml_raises(mock_isfile, mock_open_file):
#     mock_isfile.return_value = True
#     cfg = Config()
#     with pytest.raises(ValueError):
#         cfg.use("invalid.yaml")

@patch("builtins.open", new_callable=mock_open, read_data="key1: value1\nnested:\n  key2: value2\n")
def test_get_and_update_and_save(mock_open_file, sample_dict):
    cfg = Config()
    # Update a nested key
    cfg.update("nested.key2", "updated")
    assert cfg.get("nested.key2") == "updated"
    
    # Save should call open to write
    with patch("builtins.open", mock_open()) as m:
        cfg.save()
        m.assert_called_with(cfg.path, "w")

@patch("builtins.open", new_callable=mock_open, read_data="key1: oldvalue\n")
@patch("importlib.resources.files")
def test_republish_merges_configs(mock_files, mock_open_file):
    # Prepare template config
    template_yaml = "key1: newvalue\nkey3: addedvalue\n"
    mock_files.return_value = make_mock_files(template_yaml)

    cfg = Config()
    # Set current config manually
    cfg._box = Box({"key1": "oldvalue"}, default_box=True)
    
    # Patch open for reading current user config and writing merged config
    with patch("builtins.open", mock_open(read_data="key1: oldvalue\n")) as mocked_file:
        cfg.republish()
        # After republish, key1 should be oldvalue (user override), key3 added from template
        assert cfg._box.key1 == "oldvalue"
        assert cfg._box.key3 == "addedvalue"

def test_get_key_not_exists_logs_warning_and_returns_none(caplog):
    cfg = Config()
    cfg._box = Box({"existing": {"key": "value"}}, default_box=True)

    with caplog.at_level(logging.WARNING):
        result1 = cfg.get("missing.key")  # Missing at top level
        result2 = cfg.get("existing.missingkey")  # Missing nested
        result3 = cfg.get("existing.key.subkey")  # Path broken: 'existing.key' is a str

    # All should return None (the default default)
    assert result1 is None
    assert result2 is None
    assert result3 is None

    # Verify that proper warnings were logged
    messages = [rec.message for rec in caplog.records]
    assert any("Config key 'missing.key' not found at 'missing'" in m for m in messages)
    assert any("Config key 'existing.missingkey' not found at 'missingkey'" in m for m in messages)
    assert any("Config key 'existing.key.subkey' path broken at 'subkey', encountered non-dict: str" in m for m in messages)

def test_deep_merge_behavior():
    source = {
        "a": 1,
        "b": {
            "c": 2,
            "d": 3,
        },
        "e": 4,
    }
    override = {
        "b": {
            "c": 20,
        },
        "e": 40,
        "f": 50,
    }
    merged = Config._deep_merge(source, override)
    assert merged["a"] == 1
    assert merged["b"]["c"] == 20
    assert merged["b"]["d"] == 3
    assert merged["e"] == 40
    assert merged["f"] == 50

def test_path_property_with_and_without_custom():
    cfg = Config()
    # By default
    assert cfg.path == cfg._default_config_path
    
    # After using custom config
    cfg._custom_config_path = "/tmp/custom.yaml"
    assert cfg.path == "/tmp/custom.yaml"

def test_show_config_path_logs(caplog):
    with caplog.at_level(logging.INFO):
        cfg = Config()
        path = cfg.show_config_path()
        assert path == cfg.path
        assert any("Using config file:" in rec.message for rec in caplog.records)

