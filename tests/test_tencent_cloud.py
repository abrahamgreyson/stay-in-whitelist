"""
Author: abe<wechat:abrahamgreyson>
Date: 2024/6/25 17:07:59
"""
import json

import pytest
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.vpc.v20170312 import vpc_client  # noqa: F401
from stay_in_whitelist.cloud_providers.tencent_cloud import TencentCloud
from stay_in_whitelist.config.config import Allow


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
    tencent_cloud.add_rules('group_id', [Allow(port=80, desc='test')], '127.0.0.1')
    assert mock_vpc_client.CreateSecurityGroupPolicies.called


def test_delete_rules(mocker):
    mock_vpc_client = mocker.MagicMock()
    mocker.patch('tencentcloud.vpc.v20170312.vpc_client.VpcClient', return_value=mock_vpc_client)
    tencent_cloud = TencentCloud('access_key', 'secret_key', 'region')
    tencent_cloud.client = mock_vpc_client
    tencent_cloud.delete_rules('group_id', [{'PolicyIndex': 1}])
    assert mock_vpc_client.DeleteSecurityGroupPolicies.called


def test_get_rules_returns_empty_list_on_error(mocker):
    """get_rules() raises TencentCloudSDKException for non-sg-not-found errors."""
    mock_vpc_client = mocker.MagicMock()
    mock_vpc_client.DescribeSecurityGroupPolicies.side_effect = TencentCloudSDKException(
        code="InternalError",
        message="internal server error"
    )
    mocker.patch('tencentcloud.vpc.v20170312.vpc_client.VpcClient', return_value=mock_vpc_client)
    tencent_cloud = TencentCloud('access_key', 'secret_key', 'region')
    tencent_cloud.client = mock_vpc_client
    with pytest.raises(TencentCloudSDKException):
        tencent_cloud.get_rules('group_id')


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


# --- New contract tests (Task 1) ---

def test_get_rules_returns_none_on_sg_not_found(mocker):
    """get_rules() returns None when InvalidSecurityGroupID.NotFound is raised."""
    mock_vpc_client = mocker.MagicMock()
    mock_vpc_client.DescribeSecurityGroupPolicies.side_effect = TencentCloudSDKException(
        code="InvalidSecurityGroupID.NotFound",
        message="security group not found"
    )
    mocker.patch('tencentcloud.vpc.v20170312.vpc_client.VpcClient', return_value=mock_vpc_client)
    tencent_cloud = TencentCloud('access_key', 'secret_key', 'region')
    tencent_cloud.client = mock_vpc_client
    result = tencent_cloud.get_rules('group_id')
    assert result is None


def test_get_rules_raises_on_other_tencent_error(mocker):
    """get_rules() raises TencentCloudSDKException for errors other than sg-not-found."""
    mock_vpc_client = mocker.MagicMock()
    mock_vpc_client.DescribeSecurityGroupPolicies.side_effect = TencentCloudSDKException(
        code="InternalError",
        message="internal server error"
    )
    mocker.patch('tencentcloud.vpc.v20170312.vpc_client.VpcClient', return_value=mock_vpc_client)
    tencent_cloud = TencentCloud('access_key', 'secret_key', 'region')
    tencent_cloud.client = mock_vpc_client
    with pytest.raises(TencentCloudSDKException):
        tencent_cloud.get_rules('group_id')


def test_add_rules_returns_on_sg_not_found(mocker):
    """add_rules() returns silently (no raise) when InvalidSecurityGroupID.NotFound is raised."""
    mock_vpc_client = mocker.MagicMock()
    mock_vpc_client.CreateSecurityGroupPolicies.side_effect = TencentCloudSDKException(
        code="InvalidSecurityGroupID.NotFound",
        message="security group not found"
    )
    mocker.patch('tencentcloud.vpc.v20170312.vpc_client.VpcClient', return_value=mock_vpc_client)
    tencent_cloud = TencentCloud('access_key', 'secret_key', 'region')
    tencent_cloud.client = mock_vpc_client
    # Should NOT raise -- sg not found, skip silently
    result = tencent_cloud.add_rules('group_id', [Allow(port=80, desc='test')], '127.0.0.1')
    assert result is None


def test_add_rules_raises_on_other_tencent_error(mocker):
    """add_rules() raises TencentCloudSDKException for errors other than sg-not-found."""
    mock_vpc_client = mocker.MagicMock()
    mock_vpc_client.CreateSecurityGroupPolicies.side_effect = TencentCloudSDKException(
        code="InternalError",
        message="internal server error"
    )
    mocker.patch('tencentcloud.vpc.v20170312.vpc_client.VpcClient', return_value=mock_vpc_client)
    tencent_cloud = TencentCloud('access_key', 'secret_key', 'region')
    tencent_cloud.client = mock_vpc_client
    with pytest.raises(TencentCloudSDKException):
        tencent_cloud.add_rules('group_id', [Allow(port=80, desc='test')], '127.0.0.1')
