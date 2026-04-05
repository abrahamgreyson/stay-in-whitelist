"""
Author: abe<wechat:abrahamgreyson>
Date: 2024/6/25 12:14:39
"""

import pytest
import requests
from unittest.mock import Mock, patch, call
from update_whitelist.updater import Updater
from update_whitelist.cloud_providers.tencent_cloud import TencentCloud
from update_whitelist.cloud_providers.huawei_cloud import HuaweiCloud


def test_update_cloud_providers(mocker):
    mocker.patch.object(Updater, 'set_client')
    mocker.patch.object(Updater, 'update_security_group_rules')
    updater = Updater()
    config = {
        'tencent': {
            'access_key': 'key1',
            'secret_key': 'secret1',
            'regions': [
                {
                    'region': 'region1',
                    'rules': [
                        {
                            'sg': 'sg1',
                            'allow': ['allow1']
                        }
                    ]
                }
            ]
        }
    }
    # 创建一个 MagicMock 对象，并设置其 .dict() 方法返回 config
    config_mock = mocker.MagicMock()
    config_mock.dict.return_value = config
    updater.update_cloud_providers('127.0.0.1', config_mock)
    updater.set_client.assert_called_once_with('tencent', 'key1', 'secret1', 'region1')
    updater.update_security_group_rules.assert_called_once_with('sg1', ['allow1'], '127.0.0.1')


def test_update_security_group_rules_with_existed_rules(mocker):
    updater = Updater()
    updater.client = Mock()
    mocker.patch.object(updater, 'fetch_security_group_rules', return_value=['rule1'])
    mocker.patch.object(updater, '_call_with_retry', side_effect=lambda fn, *a, **kw: fn(*a, **kw))
    updater.update_security_group_rules('sg1', ['allow1'], '127.0.0.1')
    # Verify order: add_rules called BEFORE delete_rules
    assert updater.client.method_calls[0][0] == 'add_rules'
    assert updater.client.method_calls[1][0] == 'delete_rules'
    updater.client.add_rules.assert_called_once_with('sg1', ['allow1'], '127.0.0.1')
    updater.client.delete_rules.assert_called_once_with('sg1', ['rule1'])


def test_update_security_group_rules_without_existed_rules(mocker):
    updater = Updater()
    updater.client = Mock()
    mocker.patch.object(updater, 'fetch_security_group_rules', return_value=[])
    mocker.patch.object(updater, '_call_with_retry', side_effect=lambda fn, *a, **kw: fn(*a, **kw))
    updater.update_security_group_rules('sg1', ['allow1'], '127.0.0.1')
    updater.client.add_rules.assert_called_once_with('sg1', ['allow1'], '127.0.0.1')
    updater.client.delete_rules.assert_not_called()


def test_add_rules_called_even_when_no_existed_rules(mocker):
    """add_rules must always be called regardless of existed_rules state."""
    updater = Updater()
    updater.client = Mock()
    mocker.patch.object(updater, 'fetch_security_group_rules', return_value=[])
    mocker.patch.object(updater, '_call_with_retry', side_effect=lambda fn, *a, **kw: fn(*a, **kw))
    updater.update_security_group_rules('sg1', ['allow1'], '127.0.0.1')
    updater.client.add_rules.assert_called_once()


def test_delete_rules_not_called_when_existed_rules_empty(mocker):
    """delete_rules must NOT be called when existed_rules is empty list."""
    updater = Updater()
    updater.client = Mock()
    mocker.patch.object(updater, 'fetch_security_group_rules', return_value=[])
    mocker.patch.object(updater, '_call_with_retry', side_effect=lambda fn, *a, **kw: fn(*a, **kw))
    updater.update_security_group_rules('sg1', ['allow1'], '127.0.0.1')
    updater.client.delete_rules.assert_not_called()


def test_delete_rules_called_when_existed_rules_present(mocker):
    """delete_rules IS called when existed_rules has items."""
    updater = Updater()
    updater.client = Mock()
    mocker.patch.object(updater, 'fetch_security_group_rules', return_value=['rule1', 'rule2'])
    mocker.patch.object(updater, '_call_with_retry', side_effect=lambda fn, *a, **kw: fn(*a, **kw))
    updater.update_security_group_rules('sg1', ['allow1'], '127.0.0.1')
    updater.client.delete_rules.assert_called_once_with('sg1', ['rule1', 'rule2'])


def test_set_client(mocker):
    updater = Updater()
    # 创建一个模拟的 TencentCloud 对象
    mock_tencent_cloud = mocker.MagicMock(spec=TencentCloud)
    # 使用模拟的 TencentCloud 对象替代真实的 TencentCloud 类
    mocker.patch('update_whitelist.updater.TencentCloud', return_value=mock_tencent_cloud)
    updater.set_client('tencent', 'key1', 'secret1', 'region1')
    assert isinstance(updater.client, TencentCloud)
    # 创建一个模拟的 HuaweiCloud 对象
    mock_huawei_cloud = mocker.MagicMock(spec=HuaweiCloud)
    # 使用模拟的 HuaweiCloud 对象替代真实的 HuaweiCloud 类
    mocker.patch('update_whitelist.updater.HuaweiCloud', return_value=mock_huawei_cloud)
    updater.set_client('huawei', 'key2', 'secret2', 'ae-ad-1')
    assert isinstance(updater.client, HuaweiCloud)
    with pytest.raises(ValueError):
        updater.set_client('unsupported', 'key', 'secret', 'region')


def test_fetch_security_group_rules_returns_empty_list_on_error(mocker):
    """fetch_security_group_rules must return [] on exception, not None."""
    updater = Updater()
    updater.client = Mock()
    updater.client.get_rules.side_effect = Exception('error')
    with patch('update_whitelist.updater.logger'):
        result = updater.fetch_security_group_rules('sg1')
    assert result == []


def test_fetch_security_group_rules_success(mocker):
    """fetch_security_group_rules returns rules list on success."""
    updater = Updater()
    updater.client = Mock()
    updater.client.get_rules.return_value = ['rule1']
    assert updater.fetch_security_group_rules('sg1') == ['rule1']


def test_add_before_delete_order(mocker):
    """Verify exact call order: add_rules must come before delete_rules."""
    updater = Updater()
    updater.client = Mock()
    mocker.patch.object(updater, 'fetch_security_group_rules', return_value=['old_rule'])
    mocker.patch.object(updater, '_call_with_retry', side_effect=lambda fn, *a, **kw: fn(*a, **kw))
    updater.update_security_group_rules('sg1', ['allow1'], '127.0.0.1')
    # The first client call must be add_rules, second must be delete_rules
    calls = [c[0] for c in updater.client.method_calls]
    assert calls == ['add_rules', 'delete_rules']


def test_retry_on_connection_error(mocker):
    """Cloud API calls retry up to 3 times on ConnectionError."""
    updater = Updater()
    updater.client = Mock()

    call_count = {'n': 0}

    def add_rules_side_effect(*args, **kwargs):
        call_count['n'] += 1
        if call_count['n'] < 3:
            raise requests.exceptions.ConnectionError("Connection failed")
        return None

    updater.client.add_rules.side_effect = add_rules_side_effect
    mocker.patch.object(updater, 'fetch_security_group_rules', return_value=[])

    updater.update_security_group_rules('sg1', ['allow1'], '127.0.0.1')

    assert call_count['n'] == 3, f"Expected 3 attempts, got {call_count['n']}"


def test_no_retry_on_non_network_error(mocker):
    """Cloud API calls do NOT retry on ValueError (non-network error)."""
    updater = Updater()
    updater.client = Mock()

    call_count = {'n': 0}

    def add_rules_side_effect(*args, **kwargs):
        call_count['n'] += 1
        raise ValueError("bad value")

    updater.client.add_rules.side_effect = add_rules_side_effect
    mocker.patch.object(updater, 'fetch_security_group_rules', return_value=[])

    with pytest.raises(ValueError, match="bad value"):
        updater.update_security_group_rules('sg1', ['allow1'], '127.0.0.1')

    assert call_count['n'] == 1, f"Expected exactly 1 attempt (no retry), got {call_count['n']}"
