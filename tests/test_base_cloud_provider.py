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
