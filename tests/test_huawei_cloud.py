"""
Author: abe<wechat:abrahamgreyson>
Date: 2024/6/25 16:31:45
"""
import pytest
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkcore.exceptions import exceptions
from huaweicloudsdkvpc.v3 import VpcClient
from stay_in_whitelist.cloud_providers.huawei_cloud import HuaweiCloud
from stay_in_whitelist.config.config import Allow


def test_initialize_client(mocker):
    # 创建一个模拟的 VpcClient 对象
    mock_vpc_client = mocker.MagicMock()
    # 创建一个模拟的 VpcClientBuilder 对象
    mock_vpc_client_builder = mocker.MagicMock()
    # 设置 VpcClientBuilder.build 方法的返回值为 mock_vpc_client
    mock_vpc_client_builder.build.return_value = mock_vpc_client
    # 设置 with_credentials 和 with_region 方法的返回值为 mock_vpc_client_builder
    mock_vpc_client_builder.with_credentials.return_value = mock_vpc_client_builder
    mock_vpc_client_builder.with_region.return_value = mock_vpc_client_builder
    # 使用模拟的 VpcClientBuilder 对象替代真实的 VpcClient.new_builder 静态方法
    mocker.patch('huaweicloudsdkvpc.v3.VpcClient.new_builder', return_value=mock_vpc_client_builder)
    # 模拟 VpcRegion.value_of 方法返回一个有效的区域
    mocker.patch('huaweicloudsdkvpc.v3.region.vpc_region.VpcRegion.value_of', return_value='cn-north-1')
    huawei_cloud = HuaweiCloud('access_key', 'secret_key', 'cn-north-1')
    huawei_cloud.initialize_client()
    assert VpcClient.new_builder.called
    assert mock_vpc_client_builder.with_credentials.call_count == 2
    assert mock_vpc_client_builder.with_region.called
    assert mock_vpc_client_builder.build.called
    assert huawei_cloud.client == mock_vpc_client

def test_get_rules(mocker):
    # 创建一个模拟的 VpcClient 对象
    mock_vpc_client = mocker.MagicMock()
    # 使用模拟的 VpcClient 对象替代真实的 VpcClient 类
    mocker.patch('huaweicloudsdkvpc.v3.VpcClient.new_builder', return_value=mock_vpc_client)
    huawei_cloud = HuaweiCloud('access_key', 'secret_key', 'cn-north-1')
    huawei_cloud.client = mock_vpc_client
    huawei_cloud.get_rules('group_id')
    mock_vpc_client.list_security_group_rules.assert_called_once()


def test_delete_rules(mocker):
    # 创建一个模拟的 VpcClient 对象
    mock_vpc_client = mocker.MagicMock()
    # 使用模拟的 VpcClient 对象替代真实的 VpcClient 类
    mocker.patch('huaweicloudsdkvpc.v3.VpcClient.new_builder', return_value=mock_vpc_client)
    huawei_cloud = HuaweiCloud('access_key', 'secret_key', 'cn-north-1')
    huawei_cloud.client = mock_vpc_client
    # 创建一个包含 id 属性的模拟规则对象
    mock_rule = mocker.MagicMock()
    mock_rule.id = 'rule1'
    huawei_cloud.delete_rules('group_id', [mock_rule])
    mock_vpc_client.delete_security_group_rule.assert_called_once()


def test_add_rules(mocker):
    # 创建一个模拟的 VpcClient 对象
    mock_vpc_client = mocker.MagicMock()
    # 使用模拟的 VpcClient 对象替代真实的 VpcClient 类
    mocker.patch('huaweicloudsdkvpc.v3.VpcClient.new_builder', return_value=mock_vpc_client)
    huawei_cloud = HuaweiCloud('access_key', 'secret_key', 'cn-north-1')
    huawei_cloud.client = mock_vpc_client
    huawei_cloud.add_rules('group_id', [Allow(port=80, desc='test')], '127.0.0.1')
    mock_vpc_client.batch_create_security_group_rules.assert_called_once()


def test_get_rules_returns_empty_list_on_error(mocker):
    """get_rules() raises ClientRequestException for non-404 errors (not swallows them)."""
    from huaweicloudsdkcore.exceptions.exceptions import SdkError
    mock_vpc_client = mocker.MagicMock()
    mock_vpc_client.list_security_group_rules.side_effect = exceptions.ClientRequestException(
        500, SdkError(request_id="test", error_code="test", error_msg="test error")
    )
    mocker.patch('huaweicloudsdkvpc.v3.VpcClient.new_builder', return_value=mock_vpc_client)
    huawei_cloud = HuaweiCloud('access_key', 'secret_key', 'cn-north-1')
    huawei_cloud.client = mock_vpc_client
    with pytest.raises(exceptions.ClientRequestException):
        huawei_cloud.get_rules('group_id')


def test_add_rules_catches_exception(mocker):
    """add_rules() raises ClientRequestException for non-404/non-409 errors."""
    from huaweicloudsdkcore.exceptions.exceptions import SdkError
    mock_vpc_client = mocker.MagicMock()
    mock_vpc_client.batch_create_security_group_rules.side_effect = exceptions.ClientRequestException(
        500, SdkError(request_id="test", error_code="test", error_msg="test error")
    )
    mocker.patch('huaweicloudsdkvpc.v3.VpcClient.new_builder', return_value=mock_vpc_client)
    huawei_cloud = HuaweiCloud('access_key', 'secret_key', 'cn-north-1')
    huawei_cloud.client = mock_vpc_client
    with pytest.raises(exceptions.ClientRequestException):
        huawei_cloud.add_rules('group_id', [Allow(port=80, desc='test')], '127.0.0.1')

def test_get_rules_returns_none_on_404(mocker):
    """get_rules() returns None (not []) when 404 ClientRequestException is raised."""
    from huaweicloudsdkcore.exceptions.exceptions import SdkError
    mock_vpc_client = mocker.MagicMock()
    mock_vpc_client.list_security_group_rules.side_effect = exceptions.ClientRequestException(
        404, SdkError(request_id="test", error_code="sg_not_found", error_msg="security group not found")
    )
    mocker.patch('huaweicloudsdkvpc.v3.VpcClient.new_builder', return_value=mock_vpc_client)
    huawei_cloud = HuaweiCloud('access_key', 'secret_key', 'cn-north-1')
    huawei_cloud.client = mock_vpc_client
    result = huawei_cloud.get_rules('group_id')
    assert result is None


def test_get_rules_raises_on_non_404_error(mocker):
    """get_rules() raises ClientRequestException for non-404 errors (not swallows them)."""
    from huaweicloudsdkcore.exceptions.exceptions import SdkError
    mock_vpc_client = mocker.MagicMock()
    mock_vpc_client.list_security_group_rules.side_effect = exceptions.ClientRequestException(
        500, SdkError(request_id="test", error_code="internal_error", error_msg="internal server error")
    )
    mocker.patch('huaweicloudsdkvpc.v3.VpcClient.new_builder', return_value=mock_vpc_client)
    huawei_cloud = HuaweiCloud('access_key', 'secret_key', 'cn-north-1')
    huawei_cloud.client = mock_vpc_client
    with pytest.raises(exceptions.ClientRequestException):
        huawei_cloud.get_rules('group_id')


def test_add_rules_returns_on_404(mocker):
    """add_rules() returns silently (no raise) when 404 ClientRequestException is raised."""
    from huaweicloudsdkcore.exceptions.exceptions import SdkError
    mock_vpc_client = mocker.MagicMock()
    mock_vpc_client.batch_create_security_group_rules.side_effect = exceptions.ClientRequestException(
        404, SdkError(request_id="test", error_code="sg_not_found", error_msg="security group not found")
    )
    mocker.patch('huaweicloudsdkvpc.v3.VpcClient.new_builder', return_value=mock_vpc_client)
    huawei_cloud = HuaweiCloud('access_key', 'secret_key', 'cn-north-1')
    huawei_cloud.client = mock_vpc_client
    # Should NOT raise -- 404 means sg not found, skip silently
    result = huawei_cloud.add_rules('group_id', [Allow(port=80, desc='test')], '127.0.0.1')
    assert result is None


def test_add_rules_raises_on_non_404_non_409_error(mocker):
    """add_rules() raises ClientRequestException for errors other than 404 and 409."""
    from huaweicloudsdkcore.exceptions.exceptions import SdkError
    mock_vpc_client = mocker.MagicMock()
    mock_vpc_client.batch_create_security_group_rules.side_effect = exceptions.ClientRequestException(
        500, SdkError(request_id="test", error_code="internal_error", error_msg="internal server error")
    )
    mocker.patch('huaweicloudsdkvpc.v3.VpcClient.new_builder', return_value=mock_vpc_client)
    huawei_cloud = HuaweiCloud('access_key', 'secret_key', 'cn-north-1')
    huawei_cloud.client = mock_vpc_client
    with pytest.raises(exceptions.ClientRequestException):
        huawei_cloud.add_rules('group_id', [Allow(port=80, desc='test')], '127.0.0.1')


def test_add_rules_does_not_raise_on_409(mocker):
    """add_rules() does NOT raise on 409 (rule already exists -- expected)."""
    from huaweicloudsdkcore.exceptions.exceptions import SdkError
    mock_vpc_client = mocker.MagicMock()
    mock_vpc_client.batch_create_security_group_rules.side_effect = exceptions.ClientRequestException(
        409, SdkError(request_id="test", error_code="rule_exists", error_msg="rule already exists")
    )
    mocker.patch('huaweicloudsdkvpc.v3.VpcClient.new_builder', return_value=mock_vpc_client)
    huawei_cloud = HuaweiCloud('access_key', 'secret_key', 'cn-north-1')
    huawei_cloud.client = mock_vpc_client
    # Should NOT raise -- 409 means rule already exists, not an error
    result = huawei_cloud.add_rules('group_id', [Allow(port=80, desc='test')], '127.0.0.1')
    assert result is None
