"""
Author: abe<wechat:abrahamgreyson>
Date: 2024/6/13 13:45:50
"""

import logging

import requests
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type, before_sleep_log

from .cloud_providers.tencent_cloud import TencentCloud
from .cloud_providers.huawei_cloud import HuaweiCloud
from .cloud_providers.aliyun_swas_firewall import AliyunSwasFirewall
from .logger import get_logger

logger = get_logger()

# Retryable exceptions -- network level only per D-10, D-11
RETRYABLE_EXCEPTIONS = (
    requests.exceptions.ConnectionError,
    requests.exceptions.Timeout,
)

# Cloud provider field names in Config model (only these are iterated)
CLOUD_PROVIDER_FIELDS = ('huawei', 'tencent', 'aliyun', 'aliyun_firewall')

PROVIDER_DISPLAY_NAMES = {
    'huawei': '[华为云]',
    'tencent': '[腾讯云]',
    'aliyun': '[阿里云]',
    'aliyun_firewall': '[阿里云-轻量防火墙]',
}


class Updater:
    def __init__(self):
        self.client = None

    def update_cloud_providers(self, current_ip, config):
        """
        更新云服务商的白名单
        对每个 Provider：先写动态 IP 规则（from Wulihe），再写静态 IP 规则（Abe 等）
        """
        display = PROVIDER_DISPLAY_NAMES.get

        for provider_name in CLOUD_PROVIDER_FIELDS:
            provider_config = getattr(config, provider_name, None)
            if provider_config is None:
                continue

            name = display(provider_name, provider_name)
            try:
                logger.info(f"更新 {name}...")
                access_key = provider_config.access_key
                secret_key = provider_config.secret_key

                # Step 1: 静态 IP 规则（from Abe 等），先清理再添加，避免残留规则与动态 IP 冲突
                if provider_config.static_ips:
                    logger.info(f"更新 {name} 静态 IP（{provider_config.static_ips.rule_prefix}）...")
                    except_ports = set(str(p) for p in provider_config.static_ips.except_ports)
                    for region_config in provider_config.regions:
                        region = region_config.region
                        for rule in region_config.rules:
                            filtered_allows = [a for a in rule.allow if str(a.port) not in except_ports]
                            if not filtered_allows:
                                continue
                            self.set_client(provider_name, access_key, secret_key, region, provider_config.static_ips.rule_prefix)
                            if self.client is None:
                                continue
                            self.reconcile_security_group_rules(rule.sg, filtered_allows, provider_config.static_ips.ips)
                else:
                    # 未配置 static_ips，清理残留的静态 IP 规则
                    for region_config in provider_config.regions:
                        region = region_config.region
                        for rule in region_config.rules:
                            self.set_client(provider_name, access_key, secret_key, region, "from Abe")
                            if self.client is None:
                                continue
                            existed = self.fetch_security_group_rules(rule.sg)
                            if existed:
                                logger.info(f"清理安全组 {rule.sg} 的 {len(existed)} 条残留静态规则...")
                                self._call_with_retry(self.client.delete_rules, rule.sg, existed)

                # Step 2: 动态 IP 规则（from Wulihe）
                for region_config in provider_config.regions:
                    region = region_config.region
                    for rule in region_config.rules:
                        self.set_client(provider_name, access_key, secret_key, region, config.rule_prefix)
                        if self.client is None:
                            continue
                        self.update_security_group_rules(rule.sg, rule.allow, current_ip)
            except Exception:
                logger.error(f"{name} 更新失败，跳过继续处理下一个云厂商", exc_info=True)
        return None

    def update_security_group_rules(self, sg, rules, ip):
        """
        更新安全组规则（动态 IP 路径）
        幂等：如果现有规则的 (IP, port) 集合与期望一致，跳过。
        否则：先添加新规则（D-13），再删除不在期望集合中的旧规则。
        """
        logger.info(f"获取安全组 {sg} 的规则...")
        existed_rules = self.fetch_security_group_rules(sg)

        if existed_rules is None:
            logger.info(f"安全组 {sg} 不存在，跳过规则更新")
            return

        desired = self._desired_fingerprints(rules, ip)
        existing = self._existing_fingerprints(existed_rules)

        if existing == desired:
            logger.info(f"安全组 {sg} 的规则已匹配当前 IP，跳过更新")
            return

        # ADD new rules FIRST (D-13)
        logger.info(f"添加安全组 {sg} 的规则...")
        assert self.client is not None
        add_result = self._call_with_retry(self.client.add_rules, sg, rules, ip)

        # DELETE only stale rules (not in desired set)
        stale = [r for r in existed_rules if self.client.rule_fingerprint(r) not in desired]
        if add_result and stale:
            logger.info(f"删除安全组 {sg} 的 {len(stale)} 条旧规则...")
            self._call_with_retry(self.client.delete_rules, sg, stale)
        else:
            logger.info(f"安全组 {sg} 没有符合条件的旧规则，跳过删除...")

        return None

    def set_client(self, provider_name, access_key, secret_key, region, rule_prefix) -> None:
        """
        设置云服务客户端
        """
        if provider_name == 'huawei':
            self.client = HuaweiCloud(access_key, secret_key, region, rule_prefix=rule_prefix)
        elif provider_name == 'tencent':
            self.client = TencentCloud(access_key, secret_key, region, rule_prefix=rule_prefix)
        elif provider_name == 'aliyun':
            logger.warning("阿里云 ECS 安全组功能尚未实现，跳过！如需管理轻量服务器防火墙，请使用 aliyun_firewall 配置。")
            self.client = None
            return
        elif provider_name == 'aliyun_firewall':
            self.client = AliyunSwasFirewall(access_key, secret_key, region, rule_prefix=rule_prefix)
        else:
            raise ValueError(f"不支持的云服务提供商: {provider_name}")

    def reconcile_security_group_rules(self, sg, rules, ips):
        """
        静态 IP 模式的规则同步（幂等）。
        通过 (IP, port) 指纹比较期望与现有规则：
        - 完全匹配 → 跳过
        - 有差异 → 删除不在期望集合中的旧规则，添加缺失的规则
        不存在 delete-then-add 同一 (IP, port) 的竞态。
        """
        existed_rules = self.fetch_security_group_rules(sg)
        if existed_rules is None:
            return

        desired = set()
        for ip in ips:
            desired.update(self._desired_fingerprints(rules, ip))
        existing = self._existing_fingerprints(existed_rules)

        if existing == desired:
            logger.info(f"安全组 {sg} 的静态 IP 规则已正确，跳过")
            return

        # Delete stale rules (not in desired set)
        stale = [r for r in existed_rules if self.client.rule_fingerprint(r) not in desired]
        if stale:
            logger.info(f"清空安全组 {sg} 的 {len(stale)} 条旧规则...")
            self._call_with_retry(self.client.delete_rules, sg, stale)

        # Add missing rules
        missing_fps = desired - existing
        if missing_fps:
            missing_ips = sorted(set(fp[0] for fp in missing_fps))
            for ip in missing_ips:
                logger.info(f"添加安全组 {sg} 的规则，IP: {ip}...")
                assert self.client is not None
                self._call_with_retry(self.client.add_rules, sg, rules, ip)

    def fetch_security_group_rules(self, sg):
        """
        获取安全组规则。
        返回 None 表示安全组不存在（跳过该 sg）。
        返回 [] 表示安全组存在但无匹配规则。
        其他异常向上传播。
        """
        assert self.client is not None
        rules = self.client.get_rules(sg)
        if rules is None:
            logger.info(f"安全组 {sg} 不存在，跳过")
            return None
        logger.info(f"成功获取安全组 {sg} 的规则")
        return rules

    def _desired_fingerprints(self, rules, ip):
        """构建期望的 (ip, port) 指纹集合。"""
        return {(ip, str(rule.port)) for rule in rules}

    def _existing_fingerprints(self, existed_rules):
        """从现有规则构建 (ip, port) 指纹集合。"""
        assert self.client is not None
        return {self.client.rule_fingerprint(r) for r in existed_rules}

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
