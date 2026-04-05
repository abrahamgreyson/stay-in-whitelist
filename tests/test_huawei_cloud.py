"""
Author: abe<wechat:abrahamgreyson>
Date: 2024/6/25 16:31:45
"""
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkcore.exceptions import exceptions
from huaweicloudsdkvpc.v3 import VpcClient
from update_whitelist.cloud_providers.huawei_cloud import HuaweiCloud


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
    huawei_cloud.add_rules('group_id', [{'port': 80, 'desc': 'test'}], '127.0.0.1')
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
    """add_rules() should catch ClientRequestException and log it without crashing"""
    from huaweicloudsdkcore.exceptions.exceptions import SdkError
    mock_vpc_client = mocker.MagicMock()
    mock_vpc_client.batch_create_security_group_rules.side_effect = exceptions.ClientRequestException(
        500, SdkError(request_id="test", error_code="test", error_msg="test error")
    )
    mocker.patch('huaweicloudsdkvpc.v3.VpcClient.new_builder', return_value=mock_vpc_client)
    mock_log = mocker.patch('update_whitelist.cloud_providers.huawei_cloud.BaseCloudProvider.log')
    huawei_cloud = HuaweiCloud('access_key', 'secret_key', 'cn-north-1')
    huawei_cloud.client = mock_vpc_client
    # Should NOT raise -- exception is caught internally
    huawei_cloud.add_rules('group_id', [{'port': 80, 'desc': 'test'}], '127.0.0.1')
    mock_log.assert_called_once()
