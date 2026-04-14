"""
Tests for cli.py: tri-state has_ip_changed and check_and_update_ip failure handling.
"""

from unittest.mock import patch, MagicMock, call

import pytest
import requests

from stay_in_whitelist.cli import has_ip_changed, check_and_update_ip


# ---------------------------------------------------------------------------
# has_ip_changed — tri-state return tests
# ---------------------------------------------------------------------------


def test_has_ip_changed_returns_none_none_on_fetch_failure(mocker, mock_config):
    """has_ip_changed returns (None, None) when get_current_ip returns None."""
    mocker.patch('stay_in_whitelist.cli.get_current_ip', return_value=None)
    result = has_ip_changed(mock_config)
    assert result == (None, None)


def test_has_ip_changed_returns_false_ip_when_ip_matches_cache(mocker, mock_config):
    """has_ip_changed returns (False, ip) when IP matches cached value."""
    mocker.patch('stay_in_whitelist.cli.get_current_ip', return_value='1.2.3.4')
    mocker.patch('stay_in_whitelist.cli.load_cached_ip', return_value='1.2.3.4')
    result = has_ip_changed(mock_config)
    assert result == (False, '1.2.3.4')


def test_has_ip_changed_returns_true_ip_when_ip_differs_from_cache(mocker, mock_config):
    """has_ip_changed returns (True, ip) when IP differs from cached value."""
    mocker.patch('stay_in_whitelist.cli.get_current_ip', return_value='5.6.7.8')
    mocker.patch('stay_in_whitelist.cli.load_cached_ip', return_value='1.2.3.4')
    result = has_ip_changed(mock_config)
    assert result == (True, '5.6.7.8')


def test_has_ip_changed_returns_true_ip_when_no_cache_exists(mocker, mock_config):
    """has_ip_changed returns (True, ip) when current IP is valid but no cache exists."""
    mocker.patch('stay_in_whitelist.cli.get_current_ip', return_value='9.10.11.12')
    mocker.patch('stay_in_whitelist.cli.load_cached_ip', return_value=None)
    result = has_ip_changed(mock_config)
    assert result == (True, '9.10.11.12')


def test_has_ip_changed_returns_none_none_on_request_exception(mocker, mock_config):
    """has_ip_changed returns (None, None) when get_current_ip raises RequestException."""
    mocker.patch('stay_in_whitelist.cli.get_current_ip', side_effect=requests.RequestException("timeout"))
    result = has_ip_changed(mock_config)
    assert result == (None, None)


# ---------------------------------------------------------------------------
# check_and_update_ip — failure path tests
# ---------------------------------------------------------------------------


def test_check_and_update_ip_logs_failure_when_fetch_fails(mocker, mock_config):
    """check_and_update_ip logs a failure message (not '没有更改') when IP fetch fails."""
    mock_logger = mocker.patch('stay_in_whitelist.cli.logger')
    mocker.patch('stay_in_whitelist.cli.has_ip_changed', return_value=(None, None))
    mock_updater_cls = mocker.patch('stay_in_whitelist.cli.Updater')
    mock_cache_ip = mocker.patch('stay_in_whitelist.cli.cache_ip')

    check_and_update_ip(mock_config)

    # Should NOT have called Updater or cache_ip
    mock_updater_cls.assert_not_called()
    mock_cache_ip.assert_not_called()

    # Should have logged a failure message, NOT "没有更改"
    error_calls = mock_logger.error.call_args_list
    info_calls = mock_logger.info.call_args_list
    all_messages = [str(c) for c in error_calls + info_calls]
    # At least one log call should contain a failure/error indicator
    assert any('失败' in msg or 'error' in msg.lower() or 'fail' in msg.lower() for msg in all_messages), \
        f"Expected a failure log, got: {all_messages}"


def test_check_and_update_ip_calls_updater_when_ip_changed(mocker, mock_config):
    """check_and_update_ip calls Updater.update_cloud_providers when IP changed."""
    mock_logger = mocker.patch('stay_in_whitelist.cli.logger')
    mocker.patch('stay_in_whitelist.cli.has_ip_changed', return_value=(True, '5.6.7.8'))
    mock_updater_instance = MagicMock()
    mock_updater_cls = mocker.patch('stay_in_whitelist.cli.Updater', return_value=mock_updater_instance)
    mock_cache_ip = mocker.patch('stay_in_whitelist.cli.cache_ip')

    check_and_update_ip(mock_config)

    mock_updater_cls.assert_called_once()
    mock_updater_instance.update_cloud_providers.assert_called_once_with('5.6.7.8', mock_config)
    mock_cache_ip.assert_called_once_with('5.6.7.8', mock_config)


def test_check_and_update_ip_logs_unchanged_when_ip_not_changed(mocker, mock_config):
    """check_and_update_ip logs '没有更改' when IP truly unchanged."""
    mock_logger = mocker.patch('stay_in_whitelist.cli.logger')
    mocker.patch('stay_in_whitelist.cli.has_ip_changed', return_value=(False, '1.2.3.4'))
    mock_updater_cls = mocker.patch('stay_in_whitelist.cli.Updater')
    mock_cache_ip = mocker.patch('stay_in_whitelist.cli.cache_ip')

    check_and_update_ip(mock_config)

    # Should NOT have called Updater or cache_ip
    mock_updater_cls.assert_not_called()
    mock_cache_ip.assert_not_called()

    # Should log "没有更改"
    info_messages = [str(c) for c in mock_logger.info.call_args_list]
    assert any('没有更改' in msg for msg in info_messages), \
        f"Expected '没有更改' log, got: {info_messages}"
