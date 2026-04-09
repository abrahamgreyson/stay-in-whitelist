"""
Author: abe<wechat:abrahamgreyson>
Date: 2024/6/25 16:31:45
"""
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
    """get_rules() should return [] (not None) when ClientRequestException is raised"""
    from huaweicloudsdkcore.exceptions.exceptions import SdkError
    mock_vpc_client = mocker.MagicMock()
    mock_vpc_client.list_security_group_rules.side_effect = exceptions.ClientRequestException(
        500, SdkError(request_id="test", error_code="test", error_msg="test error")
    )
    mocker.patch('huaweicloudsdkvpc.v3.VpcClient.new_builder', return_value=mock_vpc_client)
    huawei_cloud = HuaweiCloud('access_key', 'secret_key', 'cn-north-1')
    huawei_cloud.client = mock_vpc_client
    result = huawei_cloud.get_rules('group_id')
    assert result == []
    assert result is not None


def test_add_rules_catches_exception(mocker):
    """add_rules() 遇到 404/409 时返回 False，遇到其他状态码时抛出异常"""
    from huaweicloudsdkcore.exceptions.exceptions import SdkError
    import pytest
    mock_vpc_client = mocker.MagicMock()
    mock_vpc_client.batch_create_security_group_rules.side_effect = exceptions.ClientRequestException(
        500, SdkError(request_id="test", error_code="test", error_msg="test error")
    )
    mocker.patch('huaweicloudsdkvpc.v3.VpcClient.new_builder', return_value=mock_vpc_client)
    mock_log = mocker.patch('stay_in_whitelist.cloud_providers.huawei_cloud.BaseCloudProvider.log')
    huawei_cloud = HuaweiCloud('access_key', 'secret_key', 'cn-north-1')
    huawei_cloud.client = mock_vpc_client
    # 500 (非 404/409) 应当向上抛出
    with pytest.raises(exceptions.ClientRequestException):
        huawei_cloud.add_rules('group_id', [Allow(port=80, desc='test')], '127.0.0.1')
    mock_log.assert_called_once()


def test_add_rules_returns_false_on_409(mocker):
    """add_rules() 遇到 409（规则已存在）时返回 False，不抛出异常。"""
    from huaweicloudsdkcore.exceptions.exceptions import SdkError
    mock_vpc_client = mocker.MagicMock()
    mock_vpc_client.batch_create_security_group_rules.side_effect = exceptions.ClientRequestException(
        409, SdkError(request_id="test", error_code="Conflict", error_msg="rule already exists")
    )
    mocker.patch('huaweicloudsdkvpc.v3.VpcClient.new_builder', return_value=mock_vpc_client)
    huawei_cloud = HuaweiCloud('access_key', 'secret_key', 'cn-north-1')
    huawei_cloud.client = mock_vpc_client
    result = huawei_cloud.add_rules('group_id', [Allow(port=80, desc='test')], '127.0.0.1')
    assert result is False


def test_add_rules_returns_false_on_404(mocker):
    """add_rules() 遇到 404（安全组不存在）时返回 False，不抛出异常。"""
    from huaweicloudsdkcore.exceptions.exceptions import SdkError
    mock_vpc_client = mocker.MagicMock()
    mock_vpc_client.batch_create_security_group_rules.side_effect = exceptions.ClientRequestException(
        404, SdkError(request_id="test", error_code="NotFound", error_msg="security group not found")
    )
    mocker.patch('huaweicloudsdkvpc.v3.VpcClient.new_builder', return_value=mock_vpc_client)
    huawei_cloud = HuaweiCloud('access_key', 'secret_key', 'cn-north-1')
    huawei_cloud.client = mock_vpc_client
    result = huawei_cloud.add_rules('group_id', [Allow(port=80, desc='test')], '127.0.0.1')
    assert result is False


def test_add_rules_returns_true_on_success(mocker):
    """add_rules() 成功时返回 True。"""
    mock_vpc_client = mocker.MagicMock()
    mocker.patch('huaweicloudsdkvpc.v3.VpcClient.new_builder', return_value=mock_vpc_client)
    huawei_cloud = HuaweiCloud('access_key', 'secret_key', 'cn-north-1')
    huawei_cloud.client = mock_vpc_client
    result = huawei_cloud.add_rules('group_id', [Allow(port=80, desc='test')], '127.0.0.1')
    assert result is True
