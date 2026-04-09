"""
Author: abe<wechat:abrahamgreyson>
Date: 2024/6/13 11:00:36
"""

from abc import ABC, abstractmethod
from typing import Any, List, Optional

from huaweicloudsdkcore.exceptions.exceptions import ClientRequestException
from tencentcloud.common.exception import TencentCloudSDKException

from stay_in_whitelist.logger import get_logger

logger = get_logger()


class BaseCloudProvider(ABC):
    access_key: str
    """ 云服务 access key """

    secret_key: str
    """ 云服务 secret key """

    region: str
    """ 云服务区域 """

    client: Any
    """ 云服务客户端 """

    def __init__(self, access_key: str, secret_key: str, region: str, **kwargs: Any) -> None:
        """
        保存 credentials 和 region 信息
        安全组 sg 我们在调用方法时再指定，这样可以避免多个规则反复初始化客户端
        """
        self.access_key = access_key
        self.secret_key = secret_key
        self.region = region
        self.rule_prefix = kwargs.pop('rule_prefix', 'from Wulihe')
        for key, value in kwargs.items():
            setattr(self, key, value)
        self.initialize_client()

    @staticmethod
    def log(e: Exception) -> None:
        """
        打印日志
        """
        error_message = f"一个未知错误{e.__class__.__name__}发生了: {e.__str__()}"
        # 华为
        if isinstance(e, ClientRequestException):
            error_message = f"""
                Status code: {e.status_code}
                Request ID: {e.request_id}
                Error code: {e.error_code}
                Error message: {e.error_msg}
                """
            if e.status_code == 409:
                logger.warning(error_message.strip())
                return
        # 腾讯
        elif isinstance(e, TencentCloudSDKException):
            error_message = f"""
                Request ID: {e.get_request_id()}
                Error code: {e.get_code()}
                Error message: {e.get_message()}
                """

        logger.error(error_message.strip())

    @staticmethod
    def is_sg_not_found(e: Exception) -> bool:
        """判断异常是否表示安全组不存在（华为 404 / 腾讯 InvalidSecurityGroupID.NotFound）。"""
        if isinstance(e, ClientRequestException) and e.status_code == 404:
            return True
        if isinstance(e, TencentCloudSDKException) and e.get_code() == 'InvalidSecurityGroupID.NotFound':
            return True
        return False

    @abstractmethod
    def initialize_client(self):
        """
        初始化特定云服务的客户端
        """
    pass

    @abstractmethod
    def delete_rules(self, group_id, rules):
        """
        删除安全组规则
        """
        pass

    @abstractmethod
    def add_rules(self, group_id, rules, ip):
        """
        添加安全组规则
        """
        pass

    @abstractmethod
    def get_rules(self, group_id) -> Optional[List]:
        """
        获取安全组规则。返回 None 表示安全组不存在，返回 [] 表示无匹配规则。
        """
        pass
