"""
Author: abe<wechat:abrahamgreyson>
Date: 2024/6/25 16:27:03
"""

import pytest
import requests
from unittest.mock import patch, MagicMock

from stay_in_whitelist.ip_fetcher import get_current_ip, load_cached_ip, cache_ip


def _mock_response(status_code=200, text="1.2.3.4"):
    """Helper to create a mock response."""
    mock = MagicMock()
    mock.status_code = status_code
    mock.text = text
    return mock


def test_get_current_ip_ipinfo_success(mocker, mock_config):
    """Test: get_current_ip returns valid IP when first provider (ipinfo) succeeds."""
    mocker.patch('requests.get', return_value=_mock_response(200, "1.2.3.4\n"))
    result = get_current_ip(mock_config)
    assert result == "1.2.3.4"


def test_get_current_ip_fallback_on_failure(mocker, mock_config):
    """Test: get_current_ip falls back to second provider when first fails with ConnectionError."""
    mock_response = _mock_response(200, "5.6.7.8\n")
    # First call: ConnectionError (ipinfo), second call: success (icanhazip)
    mocker.patch('requests.get', side_effect=[requests.ConnectionError(), mock_response])
    result = get_current_ip(mock_config)
    assert result == "5.6.7.8"


def test_get_current_ip_fallback_two_providers_fail(mocker, mock_config):
    """Test: get_current_ip falls back to third provider when first two fail."""
    mock_response = _mock_response(200, "9.10.11.12\n")
    mocker.patch('requests.get', side_effect=[
        requests.ConnectionError(),   # ipinfo fails
        requests.ConnectionError(),   # icanhazip fails
        mock_response,                # ipify succeeds
    ])
    result = get_current_ip(mock_config)
    assert result == "9.10.11.12"


def test_get_current_ip_all_providers_fail(mocker, mock_config):
    """Test: get_current_ip returns None when ALL providers fail."""
    mocker.patch('requests.get', side_effect=requests.ConnectionError())
    result = get_current_ip(mock_config)
    assert result is None


def test_get_current_ip_rejects_invalid_ip(mocker, mock_config):
    """Test: get_current_ip rejects invalid IP like 'Rate limit exceeded'."""
    # All providers return "Rate limit exceeded" -- invalid IP
    mocker.patch('requests.get', return_value=_mock_response(200, "Rate limit exceeded"))
    result = get_current_ip(mock_config)
    assert result is None


def test_get_current_ip_rejects_html(mocker, mock_config):
    """Test: get_current_ip rejects HTML response like '<html>error</html>'."""
    mocker.patch('requests.get', return_value=_mock_response(200, "<html>Error</html>"))
    result = get_current_ip(mock_config)
    assert result is None


def test_get_current_ip_uses_timeout(mocker, mock_config):
    """Test: get_current_ip passes timeout tuple to requests.get."""
    mock_get = mocker.patch('requests.get', return_value=_mock_response(200, "1.2.3.4\n"))
    get_current_ip(mock_config)
    call_kwargs = mock_get.call_args
    assert "timeout" in call_kwargs.kwargs
    assert call_kwargs.kwargs["timeout"] == (3, 5)


def test_get_current_ip_no_token_skips_ipinfo(mocker, mock_config):
    """Test: get_current_ip skips ipinfo when no token configured."""
    mock_config.ipinfo = None
    mock_get = mocker.patch('requests.get', return_value=_mock_response(200, "10.20.30.40\n"))
    result = get_current_ip(mock_config)
    assert result == "10.20.30.40"
    # First call should NOT be to ipinfo (since no token)
    first_call_url = mock_get.call_args_list[0][0][0]
    assert "ipinfo" not in first_call_url


def test_get_current_ip_logs_provider_name_not_url(mocker, mock_config):
    """Test: get_current_ip logs provider name, not full URL (no token exposure)."""
    mock_logger = mocker.patch('stay_in_whitelist.ip_fetcher.logger')
    mocker.patch('requests.get', return_value=_mock_response(200, "1.2.3.4\n"))
    get_current_ip(mock_config)
    # Check that no log call contains the token
    for call_args in mock_logger.info.call_args_list:
        msg = str(call_args)
        assert "token=" not in msg


def test_load_cached_ip(mocker, mock_config):
    """Test: load_cached_ip still works (unchanged)."""
    mocker.patch('builtins.open', mocker.mock_open(read_data='127.0.0.1\n'))
    mocker.patch('os.path.exists', return_value=True)
    assert load_cached_ip(mock_config) == '127.0.0.1'


def test_load_cached_ip_cache_file_not_exists(mocker, mock_config):
    """Test: load_cached_ip returns None when cache file doesn't exist."""
    mocker.patch('os.path.exists', return_value=False)
    assert load_cached_ip(mock_config) is None


def test_cache_ip(mocker, mock_config):
    """Test: cache_ip still works (unchanged)."""
    mock_file = mocker.mock_open()
    mocker.patch('builtins.open', mock_file)
    cache_ip('127.0.0.1', mock_config)
    mock_file().write.assert_called_once_with('127.0.0.1')
