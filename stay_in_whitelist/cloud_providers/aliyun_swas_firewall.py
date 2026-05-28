from .base_cloud_provider import BaseCloudProvider
from typing import Any, List, Optional

from alibabacloud_swas_open20200601.client import Client as SwasClient
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_swas_open20200601 import models as swas_models
from alibabacloud_tea_util import models as util_models

from stay_in_whitelist.logger import get_logger

logger = get_logger()


class AliyunSwasFirewall(BaseCloudProvider):
    """阿里云轻量应用服务器防火墙 Provider"""

    def rule_fingerprint(self, rule) -> tuple:
        ip = getattr(rule, 'source_cidr_ip', '') or ''
        return (ip.replace('/32', ''), str(getattr(rule, 'port', '')))

    def initialize_client(self):
        config = open_api_models.Config(
            access_key_id=self.access_key,
            access_key_secret=self.secret_key,
        )
        config.endpoint = f'swas.{self.region}.aliyuncs.com'
        self.client = SwasClient(config)

    def get_rules(self, group_id) -> Optional[List]:
        try:
            all_rules = []
            page_number = 1
            while True:
                request = swas_models.ListFirewallRulesRequest(
                    instance_id=group_id,
                    region_id=self.region,
                    page_size=100,
                    page_number=page_number,
                )
                runtime = util_models.RuntimeOptions()
                resp = self.client.list_firewall_rules_with_options(request, runtime)

                rules = resp.body.firewall_rules or []
                all_rules.extend(rules)

                total = resp.body.total_count
                if len(all_rules) >= total or not rules:
                    break
                page_number += 1

            filtered = [
                rule for rule in all_rules
                if rule.remark and rule.remark.startswith(self.rule_prefix)
            ]
            return filtered
        except Exception as e:
            if self._is_instance_not_found(e):
                return None
            BaseCloudProvider.log(e)
            return []

    def add_rules(self, group_id, rules, ip) -> bool:
        try:
            firewall_rules = [
                swas_models.CreateFirewallRulesRequestFirewallRules(
                    rule_protocol="TCP",
                    port=str(rule.port),
                    source_cidr_ip=f"{ip}/32",
                    remark=f"{self.rule_prefix}{' - ' + rule.desc if rule.desc else ''}"
                )
                for rule in rules
            ]
            request = swas_models.CreateFirewallRulesRequest(
                instance_id=group_id,
                region_id=self.region,
                firewall_rules=firewall_rules,
            )
            runtime = util_models.RuntimeOptions()
            self.client.create_firewall_rules_with_options(request, runtime)
            return True
        except Exception as e:
            if self._is_instance_not_found(e):
                BaseCloudProvider.log(e)
                return False
            if self._is_rule_already_exists(e):
                logger.warning(f"防火墙规则已存在，跳过: {e}")
                return False
            BaseCloudProvider.log(e)
            raise

    def delete_rules(self, group_id, rules):
        try:
            rule_ids = [rule.rule_id for rule in rules]
            request = swas_models.DeleteFirewallRulesRequest(
                instance_id=group_id,
                region_id=self.region,
                rule_ids=rule_ids,
            )
            runtime = util_models.RuntimeOptions()
            self.client.delete_firewall_rules_with_options(request, runtime)
        except Exception as e:
            BaseCloudProvider.log(e)

    @staticmethod
    def _is_instance_not_found(e: Any) -> bool:
        code = getattr(e, 'code', None) or getattr(e, 'error_code', None)
        if code == 'InvalidInstanceId.NotFound':
            return True
        return 'InvalidInstanceId.NotFound' in str(e)

    @staticmethod
    def _is_rule_already_exists(e: Any) -> bool:
        code = getattr(e, 'code', None) or getattr(e, 'error_code', None)
        if code == 'FirewallRuleAlreadyExist':
            return True
        return 'FirewallRuleAlreadyExist' in str(e)
