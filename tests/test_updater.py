"""
Author: abe<wechat:abrahamgreyson>
Date: 2024/6/25 12:14:39
"""

import pytest
import requests
from unittest.mock import Mock, patch, MagicMock  # noqa: F401
from stay_in_whitelist.updater import Updater
from stay_in_whitelist.cloud_providers.tencent_cloud import TencentCloud
from stay_in_whitelist.cloud_providers.huawei_cloud import HuaweiCloud
from stay_in_whitelist.cloud_providers.aliyun_swas_firewall import AliyunSwasFirewall
from stay_in_whitelist.config.config import Config, CloudProvider, Region, Rule, Allow, StaticIPs


def test_client_is_instance_variable():
    """Two Updater instances must NOT share client state."""
    u1 = Updater()
    u2 = Updater()
    u1.client = Mock()  # type: ignore[assignment]
    assert u2.client is None


def test_update_cloud_providers_uses_attributes(mocker):
    """update_cloud_providers iterates Pydantic Config attributes, not dict."""
    mocker.patch.object(Updater, 'set_client')
    mocker.patch.object(Updater, 'update_security_group_rules')
    updater = Updater()
    updater.client = Mock()
    config = Config(
        tencent=CloudProvider(
            access_key='key1',
            secret_key='secret1',
            regions=[Region(
                region='region1',
                rules=[Rule(sg='sg1', allow=[Allow(port=80, desc='http')])]
            )]
        )
    )
    updater.update_cloud_providers('127.0.0.1', config)
    updater.set_client.assert_called_once_with('tencent', 'key1', 'secret1', 'region1', 'from Wulihe')
    updater.update_security_group_rules.assert_called_once_with('sg1', config.tencent.regions[0].rules[0].allow, '127.0.0.1')


def test_update_cloud_providers_skips_none_providers(mocker):
    """Providers set to None are skipped."""
    mocker.patch.object(Updater, 'set_client')
    mocker.patch.object(Updater, 'update_security_group_rules')
    updater = Updater()
    config = Config(
        huawei=CloudProvider(
            access_key='hk1',
            secret_key='hs1',
            regions=[Region(
                region='cn-north',
                rules=[Rule(sg='sg-h', allow=[Allow(port=22)])]
            )]
        )
        # tencent and aliyun are None by default
    )
    updater.update_cloud_providers('1.2.3.4', config)
    updater.set_client.assert_called_once_with('huawei', 'hk1', 'hs1', 'cn-north', 'from Wulihe')


def test_update_cloud_providers_skips_non_provider_fields(mocker):
    """Non-provider fields like ipinfo, timeouts are not iterated as providers."""
    mocker.patch.object(Updater, 'set_client')
    mocker.patch.object(Updater, 'update_security_group_rules')
    updater = Updater()
    config = Config(
        tencent=CloudProvider(
            access_key='tk',
            secret_key='ts',
            regions=[Region(
                region='ap-guangzhou',
                rules=[Rule(sg='sg-t', allow=[Allow(port=443)])]
            )]
        )
    )
    updater.update_cloud_providers('10.0.0.1', config)
    # Only tencent should be called, not ipinfo/timeouts
    assert updater.set_client.call_count == 1
    updater.set_client.assert_called_once_with('tencent', 'tk', 'ts', 'ap-guangzhou', 'from Wulihe')


def test_update_security_group_rules_with_existed_rules(mocker):
    updater = Updater()
    updater.client = Mock()
    updater.client.add_rules.return_value = True
    mocker.patch.object(updater, 'fetch_security_group_rules', return_value=['rule1'])
    mocker.patch.object(updater, '_call_with_retry', side_effect=lambda fn, *a, **kw: fn(*a, **kw))
    updater.update_security_group_rules('sg1', [Allow(port=80)], '127.0.0.1')
    # Verify add_rules and delete_rules called (order ensured by code: add first, delete second)
    updater.client.add_rules.assert_called_once_with('sg1', [Allow(port=80)], '127.0.0.1')
    updater.client.delete_rules.assert_called_once_with('sg1', ['rule1'])


def test_update_security_group_rules_without_existed_rules(mocker):
    updater = Updater()
    updater.client = Mock()
    mocker.patch.object(updater, 'fetch_security_group_rules', return_value=[])
    mocker.patch.object(updater, '_call_with_retry', side_effect=lambda fn, *a, **kw: fn(*a, **kw))
    updater.update_security_group_rules('sg1', [Allow(port=80)], '127.0.0.1')
    updater.client.add_rules.assert_called_once_with('sg1', [Allow(port=80)], '127.0.0.1')
    updater.client.delete_rules.assert_not_called()


def test_add_rules_called_even_when_no_existed_rules(mocker):
    """add_rules must always be called regardless of existed_rules state."""
    updater = Updater()
    updater.client = Mock()
    mocker.patch.object(updater, 'fetch_security_group_rules', return_value=[])
    mocker.patch.object(updater, '_call_with_retry', side_effect=lambda fn, *a, **kw: fn(*a, **kw))
    updater.update_security_group_rules('sg1', [Allow(port=80)], '127.0.0.1')
    updater.client.add_rules.assert_called_once()


def test_delete_rules_not_called_when_existed_rules_empty(mocker):
    """delete_rules must NOT be called when existed_rules is empty list."""
    updater = Updater()
    updater.client = Mock()
    mocker.patch.object(updater, 'fetch_security_group_rules', return_value=[])
    mocker.patch.object(updater, '_call_with_retry', side_effect=lambda fn, *a, **kw: fn(*a, **kw))
    updater.update_security_group_rules('sg1', [Allow(port=80)], '127.0.0.1')
    updater.client.delete_rules.assert_not_called()


def test_delete_rules_called_when_existed_rules_present(mocker):
    """delete_rules IS called when existed_rules has items."""
    updater = Updater()
    updater.client = Mock()
    updater.client.add_rules.return_value = True
    mocker.patch.object(updater, 'fetch_security_group_rules', return_value=['rule1', 'rule2'])
    mocker.patch.object(updater, '_call_with_retry', side_effect=lambda fn, *a, **kw: fn(*a, **kw))
    updater.update_security_group_rules('sg1', [Allow(port=80)], '127.0.0.1')
    updater.client.delete_rules.assert_called_once_with('sg1', ['rule1', 'rule2'])


def test_set_client(mocker):
    updater = Updater()
    # 创建一个模拟的 TencentCloud 对象
    mock_tencent_cloud = mocker.MagicMock(spec=TencentCloud)
    # 使用模拟的 TencentCloud 对象替代真实的 TencentCloud 类
    mocker.patch('stay_in_whitelist.updater.TencentCloud', return_value=mock_tencent_cloud)
    updater.set_client('tencent', 'key1', 'secret1', 'region1', 'from Wulihe')
    assert isinstance(updater.client, TencentCloud)
    # 创建一个模拟的 HuaweiCloud 对象
    mock_huawei_cloud = mocker.MagicMock(spec=HuaweiCloud)
    # 使用模拟的 HuaweiCloud 对象替代真实的 HuaweiCloud 类
    mocker.patch('stay_in_whitelist.updater.HuaweiCloud', return_value=mock_huawei_cloud)
    updater.set_client('huawei', 'key2', 'secret2', 'ae-ad-1', 'from Wulihe')
    assert isinstance(updater.client, HuaweiCloud)
    with pytest.raises(ValueError):
        updater.set_client('unsupported', 'key', 'secret', 'region', 'from Wulihe')


def test_fetch_security_group_rules_propagates_exception(mocker):
    """fetch_security_group_rules must propagate exception (not swallow it)."""
    updater = Updater()
    updater.client = Mock()
    updater.client.get_rules.side_effect = Exception('error')
    with patch('stay_in_whitelist.updater.logger'):
        with pytest.raises(Exception, match='error'):
            updater.fetch_security_group_rules('sg1')


# --- New contract tests (Task 2) ---

def test_fetch_security_group_rules_returns_none_when_sg_not_found(mocker):
    """fetch_security_group_rules returns None when get_rules returns None (sg not found)."""
    updater = Updater()
    updater.client = Mock()
    updater.client.get_rules.return_value = None
    result = updater.fetch_security_group_rules('sg1')
    assert result is None


def test_update_security_group_rules_skips_when_sg_not_found(mocker):
    """update_security_group_rules skips add_rules and delete_rules when sg not found (None)."""
    updater = Updater()
    updater.client = Mock()
    mocker.patch.object(updater, 'fetch_security_group_rules', return_value=None)
    updater.update_security_group_rules('sg1', [Allow(port=80)], '127.0.0.1')
    updater.client.add_rules.assert_not_called()
    updater.client.delete_rules.assert_not_called()


def test_update_cloud_providers_isolates_provider_exception(mocker):
    """update_cloud_providers catches per-provider exceptions and logs error, does not propagate."""
    mock_logger = mocker.patch('stay_in_whitelist.updater.logger')
    mocker.patch.object(Updater, 'set_client')
    mocker.patch.object(Updater, 'update_security_group_rules', side_effect=Exception('provider error'))
    updater = Updater()
    updater.client = Mock()
    config = Config(
        tencent=CloudProvider(
            access_key='key1',
            secret_key='secret1',
            regions=[Region(
                region='region1',
                rules=[Rule(sg='sg1', allow=[Allow(port=80, desc='http')])]
            )]
        )
    )
    # Should NOT raise — exception is caught per-provider
    updater.update_cloud_providers('127.0.0.1', config)
    # Should log the error
    mock_logger.error.assert_called_once()
    assert '失败' in mock_logger.error.call_args[0][0]


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
    updater.client.add_rules.return_value = True
    mocker.patch.object(updater, 'fetch_security_group_rules', return_value=['old_rule'])
    mocker.patch.object(updater, '_call_with_retry', side_effect=lambda fn, *a, **kw: fn(*a, **kw))
    updater.update_security_group_rules('sg1', [Allow(port=80)], '127.0.0.1')
    # Filter to only API calls (skip rule_fingerprint internal calls)
    api_calls = [c[0] for c in updater.client.method_calls if c[0] in ('add_rules', 'delete_rules')]
    assert api_calls == ['add_rules', 'delete_rules']


def test_retry_on_connection_error(mocker):
    """Cloud API calls retry up to 3 times on ConnectionError."""
    updater = Updater()
    updater.client = Mock()

    call_count = {'n': 0}

    def add_rules_side_effect(*args, **kwargs):
        call_count['n'] += 1
        if call_count['n'] < 3:
            raise requests.exceptions.ConnectionError("Connection failed")
        return True

    updater.client.add_rules.side_effect = add_rules_side_effect
    mocker.patch.object(updater, 'fetch_security_group_rules', return_value=[])

    updater.update_security_group_rules('sg1', [Allow(port=80)], '127.0.0.1')

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
        updater.update_security_group_rules('sg1', [Allow(port=80)], '127.0.0.1')

    assert call_count['n'] == 1, f"Expected exactly 1 attempt (no retry), got {call_count['n']}"


def test_delete_skipped_when_add_returns_false(mocker):
    """当 add_rules 返回 False（如 409 幂等），delete_rules 不被调用。"""
    updater = Updater()
    updater.client = Mock()
    updater.client.add_rules.return_value = False
    mocker.patch.object(updater, 'fetch_security_group_rules', return_value=['rule1'])
    mocker.patch.object(updater, '_call_with_retry', side_effect=lambda fn, *a, **kw: fn(*a, **kw))
    updater.update_security_group_rules('sg1', [Allow(port=80)], '127.0.0.1')
    updater.client.delete_rules.assert_not_called()


def test_delete_called_when_add_returns_true(mocker):
    """当 add_rules 返回 True（成功写入），且有旧规则时，delete_rules 被调用。"""
    updater = Updater()
    updater.client = Mock()
    updater.client.add_rules.return_value = True
    mocker.patch.object(updater, 'fetch_security_group_rules', return_value=['rule1'])
    mocker.patch.object(updater, '_call_with_retry', side_effect=lambda fn, *a, **kw: fn(*a, **kw))
    updater.update_security_group_rules('sg1', [Allow(port=80)], '127.0.0.1')
    updater.client.delete_rules.assert_called_once_with('sg1', ['rule1'])


# --- reconcile_security_group_rules tests ---


def test_reconcile_deletes_before_adds(mocker):
    """reconcile must delete stale rules BEFORE adding missing ones."""
    updater = Updater()
    updater.client = Mock()
    mocker.patch.object(updater, 'fetch_security_group_rules', return_value=['old_rule'])
    mocker.patch.object(updater, '_call_with_retry', side_effect=lambda fn, *a, **kw: fn(*a, **kw))
    updater.reconcile_security_group_rules('sg1', [Allow(port=80)], ['1.2.3.4'])
    # Filter to only API calls (skip rule_fingerprint internal calls)
    api_calls = [c[0] for c in updater.client.method_calls if c[0] in ('delete_rules', 'add_rules')]
    assert api_calls == ['delete_rules', 'add_rules']


def test_reconcile_adds_rules_for_each_ip(mocker):
    """reconcile calls add_rules once per IP in the list."""
    updater = Updater()
    updater.client = Mock()
    mocker.patch.object(updater, 'fetch_security_group_rules', return_value=[])
    mocker.patch.object(updater, '_call_with_retry', side_effect=lambda fn, *a, **kw: fn(*a, **kw))
    updater.reconcile_security_group_rules('sg1', [Allow(port=80)], ['1.2.3.4', '5.6.7.8'])
    assert updater.client.add_rules.call_count == 2
    updater.client.add_rules.assert_any_call('sg1', [Allow(port=80)], '1.2.3.4')
    updater.client.add_rules.assert_any_call('sg1', [Allow(port=80)], '5.6.7.8')


def test_reconcile_skips_when_sg_not_found(mocker):
    """reconcile returns early when fetch returns None (sg not found)."""
    updater = Updater()
    updater.client = Mock()
    mocker.patch.object(updater, 'fetch_security_group_rules', return_value=None)
    updater.reconcile_security_group_rules('sg1', [Allow(port=80)], ['1.2.3.4'])
    updater.client.delete_rules.assert_not_called()
    updater.client.add_rules.assert_not_called()


def test_reconcile_skips_delete_when_no_existing_rules(mocker):
    """reconcile does not call delete_rules when no existing rules."""
    updater = Updater()
    updater.client = Mock()
    mocker.patch.object(updater, 'fetch_security_group_rules', return_value=[])
    mocker.patch.object(updater, '_call_with_retry', side_effect=lambda fn, *a, **kw: fn(*a, **kw))
    updater.reconcile_security_group_rules('sg1', [Allow(port=80)], ['1.2.3.4'])
    updater.client.delete_rules.assert_not_called()
    updater.client.add_rules.assert_called_once_with('sg1', [Allow(port=80)], '1.2.3.4')


def test_reconcile_empty_ips_only_deletes(mocker):
    """reconcile with empty ips list deletes existing rules without adding any."""
    updater = Updater()
    updater.client = Mock()
    mocker.patch.object(updater, 'fetch_security_group_rules', return_value=['rule1', 'rule2'])
    mocker.patch.object(updater, '_call_with_retry', side_effect=lambda fn, *a, **kw: fn(*a, **kw))
    updater.reconcile_security_group_rules('sg1', [Allow(port=80)], [])
    updater.client.delete_rules.assert_called_once_with('sg1', ['rule1', 'rule2'])
    updater.client.add_rules.assert_not_called()


def test_reconcile_idempotent(mocker):
    """reconcile skips when existing rules match desired state (fingerprint match)."""
    updater = Updater()
    updater.client = Mock()
    updater.client.rule_fingerprint.return_value = ('1.2.3.4', '80')
    mocker.patch.object(updater, 'fetch_security_group_rules', return_value=['existing_rule'])
    updater.reconcile_security_group_rules('sg1', [Allow(port=80)], ['1.2.3.4'])
    updater.client.delete_rules.assert_not_called()
    updater.client.add_rules.assert_not_called()


# --- static IPs (per-provider) tests ---


def test_update_cloud_providers_applies_static_ips(mocker):
    """When provider has static_ips, both dynamic and static rules are applied."""
    mocker.patch.object(Updater, 'set_client')
    mocker.patch.object(Updater, 'update_security_group_rules')
    mocker.patch.object(Updater, 'reconcile_security_group_rules')
    updater = Updater()
    updater.client = Mock()
    config = Config(
        tencent=CloudProvider(
            access_key='key1',
            secret_key='secret1',
            regions=[Region(
                region='ap-guangzhou',
                rules=[Rule(sg='sg-t1', allow=[Allow(port=80)])]
            )],
            static_ips=StaticIPs(ips=["10.0.0.1"])
        )
    )
    updater.update_cloud_providers('1.2.3.4', config)
    # Dynamic IP rules + Static IP rules
    assert updater.update_security_group_rules.call_count == 1
    assert updater.reconcile_security_group_rules.call_count == 1


def test_update_cloud_providers_no_static_ips_skips_reconcile(mocker):
    """When provider has no static_ips, reconcile is not called."""
    mocker.patch.object(Updater, 'set_client')
    mocker.patch.object(Updater, 'update_security_group_rules')
    mocker.patch.object(Updater, 'reconcile_security_group_rules')
    updater = Updater()
    updater.client = Mock()
    config = Config(
        tencent=CloudProvider(
            access_key='key1',
            secret_key='secret1',
            regions=[Region(
                region='ap-guangzhou',
                rules=[Rule(sg='sg-t1', allow=[Allow(port=80)])]
            )]
        )
    )
    updater.update_cloud_providers('1.2.3.4', config)
    assert updater.update_security_group_rules.call_count == 1
    updater.reconcile_security_group_rules.assert_not_called()


def test_update_cloud_providers_except_ports_filters_allows(mocker):
    """except_ports excludes matching ports from static IP reconcile."""
    mocker.patch.object(Updater, 'set_client')
    mocker.patch.object(Updater, 'update_security_group_rules')
    mocker.patch.object(Updater, 'reconcile_security_group_rules')
    updater = Updater()
    updater.client = Mock()
    config = Config(
        tencent=CloudProvider(
            access_key='key1',
            secret_key='secret1',
            regions=[Region(
                region='ap-guangzhou',
                rules=[Rule(sg='sg-t1', allow=[
                    Allow(port=22, desc='ssh'),
                    Allow(port=32560, desc='MySQL'),
                    Allow(port=32561, desc='MySQL8'),
                ])]
            )],
            static_ips=StaticIPs(ips=["10.0.0.1"], except_ports=[22])
        )
    )
    updater.update_cloud_providers('1.2.3.4', config)
    # reconcile called with filtered allows (22 excluded)
    updater.reconcile_security_group_rules.assert_called_once()
    filtered_allows = updater.reconcile_security_group_rules.call_args[0][1]
    assert len(filtered_allows) == 2
    assert all(str(a.port) != '22' for a in filtered_allows)


def test_update_cloud_providers_except_ports_all_skips_reconcile(mocker):
    """When except_ports excludes ALL ports, reconcile is skipped entirely."""
    mocker.patch.object(Updater, 'set_client')
    mocker.patch.object(Updater, 'update_security_group_rules')
    mocker.patch.object(Updater, 'reconcile_security_group_rules')
    updater = Updater()
    updater.client = Mock()
    config = Config(
        tencent=CloudProvider(
            access_key='key1',
            secret_key='secret1',
            regions=[Region(
                region='ap-guangzhou',
                rules=[Rule(sg='sg-t1', allow=[Allow(port=22)])]
            )],
            static_ips=StaticIPs(ips=["10.0.0.1"], except_ports=[22])
        )
    )
    updater.update_cloud_providers('1.2.3.4', config)
    updater.reconcile_security_group_rules.assert_not_called()
# --- aliyun / aliyun_firewall tests ---


def test_set_client_aliyun_sets_none_and_warns(mocker):
    """aliyun (ECS) sets client to None and logs warning."""
    mock_logger = mocker.patch('stay_in_whitelist.updater.logger')
    updater = Updater()
    updater.set_client('aliyun', 'ak', 'sk', 'cn-hangzhou', 'from Wulihe')
    assert updater.client is None
    mock_logger.warning.assert_called_once()
    assert 'aliyun_firewall' in mock_logger.warning.call_args[0][0]


def test_set_client_aliyun_firewall(mocker):
    """aliyun_firewall creates AliyunSwasFirewall instance."""
    mock_fw = mocker.MagicMock(spec=AliyunSwasFirewall)
    mocker.patch('stay_in_whitelist.updater.AliyunSwasFirewall', return_value=mock_fw)
    updater = Updater()
    updater.set_client('aliyun_firewall', 'ak', 'sk', 'cn-hongkong', 'from Wulihe')
    assert updater.client == mock_fw


def test_update_cloud_providers_skips_when_client_none(mocker):
    """When set_client returns None (e.g. aliyun stub), update skips that rule."""
    mocker.patch.object(Updater, 'set_client')
    mocker.patch.object(Updater, 'update_security_group_rules')
    updater = Updater()
    # Make set_client set client to None (simulating aliyun stub)
    def set_client_stub(*args, **kwargs):
        updater.client = None
    updater.set_client.side_effect = set_client_stub

    config = Config(
        aliyun=CloudProvider(
            access_key='ak', secret_key='sk',
            regions=[Region(region='cn-hangzhou', rules=[Rule(sg='inst-001', allow=[Allow(port=22)])])]
        )
    )
    updater.update_cloud_providers('1.2.3.4', config)
    updater.update_security_group_rules.assert_not_called()


# --- fingerprint-based idempotency tests ---


def test_update_skips_when_fingerprints_match(mocker):
    """update_security_group_rules skips when existing rules match desired fingerprints."""
    updater = Updater()
    updater.client = Mock()
    updater.client.rule_fingerprint.return_value = ('127.0.0.1', '80')
    mocker.patch.object(updater, 'fetch_security_group_rules', return_value=['rule1'])
    updater.update_security_group_rules('sg1', [Allow(port=80)], '127.0.0.1')
    updater.client.add_rules.assert_not_called()
    updater.client.delete_rules.assert_not_called()


def test_update_only_deletes_stale_rules(mocker):
    """update only deletes rules whose fingerprint is NOT in desired set."""
    updater = Updater()
    updater.client = Mock()
    updater.client.add_rules.return_value = True

    rules = [Allow(port=80), Allow(port=443)]
    # rule_a has matching IP, rule_b has stale IP
    fingerprints = {'rule_a': ('127.0.0.1', '80'), 'rule_b': ('old_ip', '443')}
    updater.client.rule_fingerprint.side_effect = lambda r: fingerprints[r]
    mocker.patch.object(updater, 'fetch_security_group_rules', return_value=['rule_a', 'rule_b'])
    mocker.patch.object(updater, '_call_with_retry', side_effect=lambda fn, *a, **kw: fn(*a, **kw))
    updater.update_security_group_rules('sg1', rules, '127.0.0.1')
    # Only rule_b (stale) should be deleted
    updater.client.delete_rules.assert_called_once_with('sg1', ['rule_b'])


def test_reconcile_partial_update(mocker):
    """reconcile only deletes stale and adds missing, not touching matching rules."""
    updater = Updater()
    updater.client = Mock()

    # existing: ip_a has port 80, ip_c is stale
    fingerprints = {'r_a': ('1.2.3.4', '80'), 'r_c': ('9.9.9.9', '80')}
    updater.client.rule_fingerprint.side_effect = lambda r: fingerprints[r]
    mocker.patch.object(updater, 'fetch_security_group_rules', return_value=['r_a', 'r_c'])
    mocker.patch.object(updater, '_call_with_retry', side_effect=lambda fn, *a, **kw: fn(*a, **kw))
    updater.reconcile_security_group_rules('sg1', [Allow(port=80)], ['1.2.3.4', '5.6.7.8'])
    # r_c (stale) should be deleted, 5.6.7.8 (missing) should be added
    updater.client.delete_rules.assert_called_once_with('sg1', ['r_c'])
    updater.client.add_rules.assert_called_once_with('sg1', [Allow(port=80)], '5.6.7.8')
