"""
Tests for update_whitelist.config.config module.
Covers: import safety, load_config() errors, Config validation, Paths defaults.
"""

import os
import pytest
import yaml
from pydantic import ValidationError

from update_whitelist.config.config import (
    Config,
    CloudProvider,
    Region,
    Rule,
    Allow,
    Paths,
    TimeoutSettings,
    IPInfo,
    load_config,
)


class TestImportSafety:
    """Importing the config module must not trigger file I/O."""

    def test_import_without_file(self):
        """Importing update_whitelist.config.config does NOT raise
        even when config.yaml is absent from the working directory."""
        # If we got here, the import at the top of this file succeeded
        # without needing a config.yaml in the current directory.
        assert True

    def test_no_module_level_config_singleton(self):
        """The module must NOT expose a 'config' singleton variable."""
        import update_whitelist.config.config as cfg_module
        assert not hasattr(cfg_module, 'config'), \
            "Module should not have a 'config' singleton (module-level I/O removed)"


class TestLoadConfigErrors:
    """load_config() must raise appropriate errors for bad inputs."""

    def test_load_config_missing_file_raises(self, tmp_path):
        """load_config('/nonexistent/path') raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            load_config(str(tmp_path / "nonexistent.yaml"))

    def test_load_config_malformed_yaml_raises(self, tmp_path):
        """load_config() with malformed YAML raises yaml.YAMLError."""
        bad_yaml = tmp_path / "bad.yaml"
        bad_yaml.write_text("---\ninvalid: [yaml: content", encoding="utf-8")
        with pytest.raises(yaml.YAMLError):
            load_config(str(bad_yaml))

    def test_load_config_empty_file_raises(self, tmp_path):
        """load_config() with empty YAML file raises ValueError."""
        empty_yaml = tmp_path / "empty.yaml"
        empty_yaml.write_text("", encoding="utf-8")
        with pytest.raises(ValueError, match="empty"):
            load_config(str(empty_yaml))

    def test_load_config_valid_yaml_returns_config(self, tmp_path):
        """load_config() with valid YAML returns a Config object."""
        valid_yaml = tmp_path / "valid.yaml"
        valid_yaml.write_text(
            "huawei:\n"
            "  access_key: test_ak\n"
            "  secret_key: test_sk\n"
            "  regions:\n"
            "    - region: cn-east-3\n"
            "      rules:\n"
            "        - sg: sg-test\n"
            "          allow:\n"
            "            - port: 80\n"
            "              desc: http\n",
            encoding="utf-8"
        )
        result = load_config(str(valid_yaml))
        assert isinstance(result, Config)
        assert result.huawei is not None
        assert result.huawei.access_key == 'test_ak'


class TestCheckInterval:
    """check_interval field validation and defaults."""

    def test_check_interval_default_600(self):
        """Config() defaults check_interval to 600."""
        cfg = Config()
        assert cfg.check_interval == 600

    def test_check_interval_below_minimum_raises(self):
        """Config(check_interval=100) raises ValidationError."""
        with pytest.raises(ValidationError):
            Config(check_interval=100)

    def test_check_interval_minimum_accepted(self):
        """Config(check_interval=600) accepts the minimum valid value."""
        cfg = Config(check_interval=600)
        assert cfg.check_interval == 600

    def test_check_interval_above_minimum_accepted(self):
        """Config(check_interval=900) accepts valid values above minimum."""
        cfg = Config(check_interval=900)
        assert cfg.check_interval == 900


class TestPaths:
    """Paths model defaults and custom values."""

    def test_paths_default_none(self):
        """Config().paths.ip_cache and paths.log_file default to None."""
        cfg = Config()
        assert cfg.paths.ip_cache is None
        assert cfg.paths.log_file is None

    def test_paths_custom_values(self):
        """Paths(ip_cache='/a', log_file='/b') stores values correctly."""
        paths = Paths(ip_cache="/a", log_file="/b")
        assert paths.ip_cache == "/a"
        assert paths.log_file == "/b"

    def test_config_with_custom_paths(self):
        """Config with custom paths roundtrips correctly."""
        cfg = Config(paths=Paths(ip_cache="/tmp/cache.txt", log_file="/var/log/app.log"))
        assert cfg.paths.ip_cache == "/tmp/cache.txt"
        assert cfg.paths.log_file == "/var/log/app.log"


class TestMockConfigFixture:
    """Verify the conftest.py mock_config fixture works correctly."""

    def test_mock_config_returns_valid_config(self, mock_config):
        """mock_config fixture returns a valid Config with huawei and tencent."""
        assert isinstance(mock_config, Config)
        assert mock_config.huawei is not None
        assert mock_config.tencent is not None
        assert mock_config.huawei.access_key == 'test_ak'
        assert mock_config.tencent.access_key == 'test_ak'

    def test_mock_config_has_check_interval(self, mock_config):
        """mock_config has check_interval set to 600."""
        assert mock_config.check_interval == 600

    def test_mock_config_has_paths(self, mock_config):
        """mock_config has paths with ip_cache and log_file."""
        assert mock_config.paths.ip_cache == '/tmp/test_ip_cache.txt'
        assert mock_config.paths.log_file == '/tmp/test.log'
