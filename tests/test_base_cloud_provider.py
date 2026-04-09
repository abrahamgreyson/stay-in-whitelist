"""
Author: abe<wechat:abrahamgreyson>
Date: 2024/6/25 17:19:21
"""

from stay_in_whitelist.cloud_providers.base_cloud_provider import BaseCloudProvider
from stay_in_whitelist.logger import get_logger


class MockCloudProvider(BaseCloudProvider):
    def initialize_client(self):
        pass

    def delete_rules(self, group_id, rules):
        pass

    def add_rules(self, group_id, rules, ip):
        pass

    def get_rules(self, group_id):
        pass


def test_base_cloud_provider(mocker):
    # 显式地初始化 BaseCloudProvider 的 logger
    BaseCloudProvider.logger = get_logger()
    mock_cloud_provider = MockCloudProvider('access_key', 'secret_key', 'region')
    assert mock_cloud_provider.access_key == 'access_key'
    assert mock_cloud_provider.secret_key == 'secret_key'
    assert mock_cloud_provider.region == 'region'

    # 测试 log 方法
    exception = Exception("Test exception")
    mocker.patch.object(BaseCloudProvider.logger, 'error')
    mock_cloud_provider.log(exception)
    BaseCloudProvider.logger.error.assert_called_once()

    # 由于这些方法在 MockCloudProvider 中没有实现，所以我们只能测试它们是否存在
    assert hasattr(mock_cloud_provider, 'initialize_client')
    assert hasattr(mock_cloud_provider, 'delete_rules')
    assert hasattr(mock_cloud_provider, 'add_rules')
    assert hasattr(mock_cloud_provider, 'get_rules')


# --- New contract tests (Task 1) ---

def test_is_sg_not_found_with_huawei_404():
    """is_sg_not_found() returns True for Huawei 404 ClientRequestException."""
    from huaweicloudsdkcore.exceptions.exceptions import ClientRequestException, SdkError
    e = ClientRequestException(404, SdkError(request_id="r", error_code="c", error_msg="m"))
    assert BaseCloudProvider.is_sg_not_found(e) is True


def test_is_sg_not_found_with_huawei_non_404():
    """is_sg_not_found() returns False for Huawei non-404 ClientRequestException."""
    from huaweicloudsdkcore.exceptions.exceptions import ClientRequestException, SdkError
    e = ClientRequestException(500, SdkError(request_id="r", error_code="c", error_msg="m"))
    assert BaseCloudProvider.is_sg_not_found(e) is False


def test_is_sg_not_found_with_tencent_sg_not_found():
    """is_sg_not_found() returns True for Tencent InvalidSecurityGroupID.NotFound exception."""
    from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
    e = TencentCloudSDKException(code="InvalidSecurityGroupID.NotFound", message="not found")
    assert BaseCloudProvider.is_sg_not_found(e) is True


def test_is_sg_not_found_with_tencent_other_error():
    """is_sg_not_found() returns False for Tencent non-sg-not-found exception."""
    from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
    e = TencentCloudSDKException(code="InternalError", message="internal error")
    assert BaseCloudProvider.is_sg_not_found(e) is False


def test_is_sg_not_found_with_generic_exception():
    """is_sg_not_found() returns False for generic Python exceptions."""
    e = ValueError("some error")
    assert BaseCloudProvider.is_sg_not_found(e) is False
