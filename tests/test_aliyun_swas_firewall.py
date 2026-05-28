import pytest
from unittest.mock import MagicMock, patch
from stay_in_whitelist.cloud_providers.aliyun_swas_firewall import AliyunSwasFirewall
from stay_in_whitelist.config.config import Allow


def _make_firewall_rule(rule_id, remark, port, source_cidr_ip='0.0.0.0/0'):
    rule = MagicMock()
    rule.rule_id = rule_id
    rule.remark = remark
    rule.port = port
    rule.source_cidr_ip = source_cidr_ip
    rule.rule_protocol = 'TCP'
    rule.policy = 'accept'
    return rule


def _mock_list_response(rules, total_count=None):
    body = MagicMock()
    body.firewall_rules = rules
    body.total_count = total_count if total_count is not None else len(rules)
    resp = MagicMock()
    resp.body = body
    return resp


@patch('stay_in_whitelist.cloud_providers.aliyun_swas_firewall.SwasClient')
@patch('stay_in_whitelist.cloud_providers.aliyun_swas_firewall.open_api_models')
def test_initialize_client(mock_open_api, mock_swas_client_cls):
    provider = AliyunSwasFirewall('ak', 'sk', 'cn-hongkong')
    mock_swas_client_cls.assert_called_once()
    assert provider.client is not None


@patch('stay_in_whitelist.cloud_providers.aliyun_swas_firewall.SwasClient')
@patch('stay_in_whitelist.cloud_providers.aliyun_swas_firewall.open_api_models')
def test_get_rules_filters_by_prefix(mock_open_api, mock_swas_client_cls):
    provider = AliyunSwasFirewall('ak', 'sk', 'cn-hongkong', rule_prefix='from Wulihe')
    provider.client = MagicMock()

    rules = [
        _make_firewall_rule('id1', 'from Wulihe', '3306'),
        _make_firewall_rule('id2', 'other-prefix', '80'),
        _make_firewall_rule('id3', 'from Wulihe - ssh', '22'),
    ]
    provider.client.list_firewall_rules_with_options.return_value = _mock_list_response(rules)

    result = provider.get_rules('inst-001')
    assert len(result) == 2
    assert result[0].rule_id == 'id1'
    assert result[1].rule_id == 'id3'


@patch('stay_in_whitelist.cloud_providers.aliyun_swas_firewall.SwasClient')
@patch('stay_in_whitelist.cloud_providers.aliyun_swas_firewall.open_api_models')
def test_get_rules_returns_none_on_instance_not_found(mock_open_api, mock_swas_client_cls):
    provider = AliyunSwasFirewall('ak', 'sk', 'cn-hongkong')
    provider.client = MagicMock()

    error = Exception('not found')
    error.code = 'InvalidInstanceId.NotFound'
    provider.client.list_firewall_rules_with_options.side_effect = error

    result = provider.get_rules('bad-inst')
    assert result is None


@patch('stay_in_whitelist.cloud_providers.aliyun_swas_firewall.SwasClient')
@patch('stay_in_whitelist.cloud_providers.aliyun_swas_firewall.open_api_models')
def test_get_rules_returns_empty_on_other_error(mock_open_api, mock_swas_client_cls):
    provider = AliyunSwasFirewall('ak', 'sk', 'cn-hongkong')
    provider.client = MagicMock()

    error = Exception('internal error')
    error.code = 'InternalError'
    provider.client.list_firewall_rules_with_options.side_effect = error

    result = provider.get_rules('inst-001')
    assert result == []


@patch('stay_in_whitelist.cloud_providers.aliyun_swas_firewall.SwasClient')
@patch('stay_in_whitelist.cloud_providers.aliyun_swas_firewall.open_api_models')
def test_get_rules_handles_pagination(mock_open_api, mock_swas_client_cls):
    provider = AliyunSwasFirewall('ak', 'sk', 'cn-hongkong')
    provider.client = MagicMock()

    page1 = [_make_firewall_rule('id1', 'from Wulihe', '3306')]
    page2 = [_make_firewall_rule('id2', 'from Wulihe', '80')]

    resp1 = _mock_list_response(page1, total_count=2)
    resp2 = _mock_list_response(page2, total_count=2)
    provider.client.list_firewall_rules_with_options.side_effect = [resp1, resp2]

    result = provider.get_rules('inst-001')
    assert len(result) == 2


@patch('stay_in_whitelist.cloud_providers.aliyun_swas_firewall.SwasClient')
@patch('stay_in_whitelist.cloud_providers.aliyun_swas_firewall.open_api_models')
def test_add_rules_success(mock_open_api, mock_swas_client_cls):
    provider = AliyunSwasFirewall('ak', 'sk', 'cn-hongkong')
    provider.client = MagicMock()
    provider.client.create_firewall_rules_with_options.return_value = MagicMock()

    rules = [Allow(port=3306, desc='MySQL')]
    result = provider.add_rules('inst-001', rules, '1.2.3.4')
    assert result is True
    provider.client.create_firewall_rules_with_options.assert_called_once()


@patch('stay_in_whitelist.cloud_providers.aliyun_swas_firewall.SwasClient')
@patch('stay_in_whitelist.cloud_providers.aliyun_swas_firewall.open_api_models')
def test_add_rules_returns_false_on_already_exists(mock_open_api, mock_swas_client_cls):
    provider = AliyunSwasFirewall('ak', 'sk', 'cn-hongkong')
    provider.client = MagicMock()

    error = Exception('already exists')
    error.code = 'FirewallRuleAlreadyExist'
    provider.client.create_firewall_rules_with_options.side_effect = error

    rules = [Allow(port=3306, desc='MySQL')]
    result = provider.add_rules('inst-001', rules, '1.2.3.4')
    assert result is False


@patch('stay_in_whitelist.cloud_providers.aliyun_swas_firewall.SwasClient')
@patch('stay_in_whitelist.cloud_providers.aliyun_swas_firewall.open_api_models')
def test_add_rules_returns_false_on_instance_not_found(mock_open_api, mock_swas_client_cls):
    provider = AliyunSwasFirewall('ak', 'sk', 'cn-hongkong')
    provider.client = MagicMock()

    error = Exception('not found')
    error.code = 'InvalidInstanceId.NotFound'
    provider.client.create_firewall_rules_with_options.side_effect = error

    rules = [Allow(port=3306, desc='MySQL')]
    result = provider.add_rules('inst-001', rules, '1.2.3.4')
    assert result is False


@patch('stay_in_whitelist.cloud_providers.aliyun_swas_firewall.SwasClient')
@patch('stay_in_whitelist.cloud_providers.aliyun_swas_firewall.open_api_models')
def test_add_rules_raises_on_other_error(mock_open_api, mock_swas_client_cls):
    provider = AliyunSwasFirewall('ak', 'sk', 'cn-hongkong')
    provider.client = MagicMock()

    error = Exception('internal error')
    error.code = 'InternalError'
    provider.client.create_firewall_rules_with_options.side_effect = error

    rules = [Allow(port=3306, desc='MySQL')]
    with pytest.raises(Exception):
        provider.add_rules('inst-001', rules, '1.2.3.4')


@patch('stay_in_whitelist.cloud_providers.aliyun_swas_firewall.SwasClient')
@patch('stay_in_whitelist.cloud_providers.aliyun_swas_firewall.open_api_models')
def test_delete_rules_success(mock_open_api, mock_swas_client_cls):
    provider = AliyunSwasFirewall('ak', 'sk', 'cn-hongkong')
    provider.client = MagicMock()
    provider.client.delete_firewall_rules_with_options.return_value = MagicMock()

    rules = [_make_firewall_rule('id1', 'from Wulihe', '3306')]
    provider.delete_rules('inst-001', rules)
    provider.client.delete_firewall_rules_with_options.assert_called_once()


@patch('stay_in_whitelist.cloud_providers.aliyun_swas_firewall.SwasClient')
@patch('stay_in_whitelist.cloud_providers.aliyun_swas_firewall.open_api_models')
def test_delete_rules_extracts_rule_ids(mock_open_api, mock_swas_client_cls):
    provider = AliyunSwasFirewall('ak', 'sk', 'cn-hongkong')
    provider.client = MagicMock()
    provider.client.delete_firewall_rules_with_options.return_value = MagicMock()

    rules = [
        _make_firewall_rule('id1', 'from Wulihe', '3306'),
        _make_firewall_rule('id2', 'from Wulihe', '80'),
    ]
    provider.delete_rules('inst-001', rules)

    call_args = provider.client.delete_firewall_rules_with_options.call_args
    request_arg = call_args[0][0]
    assert request_arg.rule_ids == ['id1', 'id2']
