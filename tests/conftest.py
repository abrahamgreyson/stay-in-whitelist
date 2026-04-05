"""
Shared test fixtures for stay-in-whitelist test suite.
Provides mock_config fixture per D-13 for use across all test files.
"""

import pytest
from update_whitelist.config.config import (
    Config,
    CloudProvider,
    Region,
    Rule,
    Allow,
    Paths,
    TimeoutSettings,
    IPInfo,
)


@pytest.fixture
def mock_config():
    """
    Returns a valid Config object with huawei and tencent providers,
    suitable for unit tests that need a realistic config without file I/O.
    """
    return Config(
        huawei=CloudProvider(
            access_key='test_ak',
            secret_key='test_sk',
            regions=[
                Region(
                    region='cn-east-3',
                    rules=[
                        Rule(
                            sg='sg-test',
                            allow=[Allow(port=80, desc='http')]
                        )
                    ]
                )
            ]
        ),
        tencent=CloudProvider(
            access_key='test_ak',
            secret_key='test_sk',
            regions=[
                Region(
                    region='ap-guangzhou',
                    rules=[
                        Rule(
                            sg='sg-test2',
                            allow=[Allow(port=443, desc='https')]
                        )
                    ]
                )
            ]
        ),
        ipinfo=IPInfo(tokens=['test_token']),
        check_interval=600,
        paths=Paths(ip_cache='/tmp/test_ip_cache.txt', log_file='/tmp/test.log'),
    )
