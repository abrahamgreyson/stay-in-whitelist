"""
Author: abe<wechat:abrahamgreyson>
Date: 2024/6/25 17:07:59
"""
import json

import pytest
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.vpc.v20170312 import vpc_client
from stay_in_whitelist.cloud_providers.tencent_cloud import TencentCloud


def test_initialize_client(mocker):
    mock_vpc_client = mocker.MagicMock()
    mocker.patch('tencentcloud.vpc.v20170312.vpc_client.VpcClient', return_value=mock_vpc_client)
    tencent_cloud = TencentCloud('access_key', 'secret_key', 'region')
    tencent_cloud.initialize_client()
    assert tencent_cloud.client == mock_vpc_client


def test_get_rules(mocker):
    mock_vpc_client = mocker.MagicMock()
    mock_response = mocker.MagicMock()
    mock_response.to_json_string.return_value = json.dumps({
        "SecurityGroupPolicySet": {
            "Ingress": [
                {
                    "PolicyDescription": "from Wulihe",
                    "PolicyIndex": 1
                }
            ]
        }
    })
    mock_vpc_client.DescribeSecurityGroupPolicies.return_value = mock_response
    mocker.patch('tencentcloud.vpc.v20170312.vpc_client.VpcClient', return_value=mock_vpc_client)
    tencent_cloud = TencentCloud('access_key', 'secret_key', 'region')
    tencent_cloud.client = mock_vpc_client
    rules = tencent_cloud.get_rules('group_id')
    assert mock_vpc_client.DescribeSecurityGroupPolicies.called
    assert len(rules) == 1
    assert rules[0]['PolicyDescription'] == 'from Wulihe'
    assert rules[0]['PolicyIndex'] == 1


def test_add_rules(mocker):
    mock_vpc_client = mocker.MagicMock()
    mocker.patch('tencentcloud.vpc.v20170312.vpc_client.VpcClient', return_value=mock_vpc_client)
    tencent_cloud = TencentCloud('access_key', 'secret_key', 'region')
    tencent_cloud.client = mock_vpc_client
    tencent_cloud.add_rules('group_id', [{'port': 80, 'desc': 'test'}], '127.0.0.1')
    assert mock_vpc_client.CreateSecurityGroupPolicies.called


def test_delete_rules(mocker):
    mock_vpc_client = mocker.MagicMock()
    mocker.patch('tencentcloud.vpc.v20170312.vpc_client.VpcClient', return_value=mock_vpc_client)
    tencent_cloud = TencentCloud('access_key', 'secret_key', 'region')
    tencent_cloud.client = mock_vpc_client
    tencent_cloud.delete_rules('group_id', [{'PolicyIndex': 1}])
    assert mock_vpc_client.DeleteSecurityGroupPolicies.called


def test_get_rules_returns_empty_list_on_error(mocker):
    """get_rules() should return [] (not None) when TencentCloudSDKException is raised"""
    mock_vpc_client = mocker.MagicMock()
    mock_vpc_client.DescribeSecurityGroupPolicies.side_effect = TencentCloudSDKException("test error")
    mocker.patch('tencentcloud.vpc.v20170312.vpc_client.VpcClient', return_value=mock_vpc_client)
    tencent_cloud = TencentCloud('access_key', 'secret_key', 'region')
    tencent_cloud.client = mock_vpc_client
    result = tencent_cloud.get_rules('group_id')
    assert result == []
    assert result is not None


def test_get_rules_with_custom_prefix(mocker):
    """get_rules filters by custom rule_prefix when configured."""
    mock_vpc_client = mocker.MagicMock()
    mock_response = mocker.MagicMock()
    mock_response.to_json_string.return_value = json.dumps({
        "SecurityGroupPolicySet": {
            "Ingress": [
                {
                    "PolicyDescription": "custom-prefix",
                    "PolicyIndex": 1
                },
                {
                    "PolicyDescription": "from Wulihe",
                    "PolicyIndex": 2
                }
            ]
        }
    })
    mock_vpc_client.DescribeSecurityGroupPolicies.return_value = mock_response
    mocker.patch('tencentcloud.vpc.v20170312.vpc_client.VpcClient', return_value=mock_vpc_client)
    tencent_cloud = TencentCloud('access_key', 'secret_key', 'region', rule_prefix='custom-prefix')
    tencent_cloud.client = mock_vpc_client
    rules = tencent_cloud.get_rules('group_id')
    assert len(rules) == 1
    assert rules[0]['PolicyDescription'] == 'custom-prefix'


def test_get_rules_filters_by_prefix(mocker):
    """get_rules excludes rules not matching the configured prefix."""
    mock_vpc_client = mocker.MagicMock()
    mock_response = mocker.MagicMock()
    mock_response.to_json_string.return_value = json.dumps({
        "SecurityGroupPolicySet": {
            "Ingress": [
                {
                    "PolicyDescription": "from Wulihe",
                    "PolicyIndex": 1
                },
                {
                    "PolicyDescription": "other-prefix",
                    "PolicyIndex": 2
                }
            ]
        }
    })
    mock_vpc_client.DescribeSecurityGroupPolicies.return_value = mock_response
    mocker.patch('tencentcloud.vpc.v20170312.vpc_client.VpcClient', return_value=mock_vpc_client)
    tencent_cloud = TencentCloud('access_key', 'secret_key', 'region')
    tencent_cloud.client = mock_vpc_client
    rules = tencent_cloud.get_rules('group_id')
    assert len(rules) == 1
    assert rules[0]['PolicyDescription'] == 'from Wulihe'
