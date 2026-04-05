"""
Author: abe<wechat:abrahamgreyson>
Date: 2024/6/13 13:45:50
"""

import logging

import requests
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type, before_sleep_log

from .cloud_providers.tencent_cloud import TencentCloud
from .cloud_providers.huawei_cloud import HuaweiCloud
from .logger import get_logger

logger = get_logger()

# Retryable exceptions -- network level only per D-10, D-11
RETRYABLE_EXCEPTIONS = (
    requests.exceptions.ConnectionError,
    requests.exceptions.Timeout,
)


class Updater:
    client = None

    def update_cloud_providers(self, current_ip, config):
        """
        更新云服务商的白名单
        """

        # 遍历每个云服务提供商
        for provider_name, provider_config in config.dict().items():
            if provider_config is None or provider_name == 'ipinfo':
                continue

            logger.info(f"更新 {provider_name}...")
            access_key = provider_config['access_key']
            secret_key = provider_config['secret_key']

            # 遍历每个区域
            for region_config in provider_config['regions']:
                region = region_config['region']
                rules = region_config['rules']

                # 遍历每个安全组
                for rule in rules:
                    sg = rule['sg']
                    allows = rule['allow']

                    # 我Men以安全组为单位去初始化云服务客户端
                    self.set_client(provider_name, access_key, secret_key, region)
                    # 更新规则
                    self.update_security_group_rules(sg, allows, current_ip)
        return None

    def update_security_group_rules(self, sg, rules, ip):
        """
        更新安全组规则
        Per D-13: add new rules FIRST, then delete old rules.
        This ensures no lockout window during the update.
        """
        logger.info(f"获取安全组 {sg} 的规则...")
        existed_rules = self.fetch_security_group_rules(sg)

        # ADD new rules FIRST (D-13)
        logger.info(f"添加安全组 {sg} 的规则...")
        self._call_with_retry(self.client.add_rules, sg, rules, ip)

        # DELETE old rules SECOND (only after new rules are in place)
        if existed_rules:
            logger.info(f"有符合条件的规则，删除安全组 {sg} 的所有规则...")
            self._call_with_retry(self.client.delete_rules, sg, existed_rules)
        else:
            logger.info(f"安全组 {sg} 没有符合条件的规则，跳过删除...")

        return None

    def set_client(self, provider_name, access_key, secret_key, region) -> None:
        """
        设置云服务客户端
        """
        if provider_name == 'huawei':
            self.client = HuaweiCloud(access_key, secret_key, region)
        elif provider_name == 'tencent':
            self.client = TencentCloud(access_key, secret_key, region)
        elif provider_name == 'aliyun':
            # 如果您还没有实现阿里云，我们可以暂时抛出一个异常
            raise NotImplementedError("阿里云安全组规则获取尚未实现")
        else:
            raise ValueError(f"不支持的云服务提供商: {provider_name}")

    def fetch_security_group_rules(self, sg):
        """
        获取安全组规则
        """
        try:
            # 调用相应云服务的方法获取安全组规则
            rules = self.client.get_rules(sg)
            logger.info(f"成功获取安全组 {sg} 的规则")
            return rules

        except Exception as e:
            logger.error(f"获取 {sg} 安全组规则时出错: {str(e)}")
            return []

    def _call_with_retry(self, fn, *args, **kwargs):
        """Execute a cloud API call with retry on transient network errors per D-09."""
        retry_decorator = retry(
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=1, min=1, max=10),
            retry=retry_if_exception_type(RETRYABLE_EXCEPTIONS),
            before_sleep=before_sleep_log(logger, logging.WARNING),
            reraise=True,
        )
        return retry_decorator(fn)(*args, **kwargs)
