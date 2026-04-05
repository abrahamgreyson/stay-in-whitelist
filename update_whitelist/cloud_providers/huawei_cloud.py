# coding: utf-8
"""
Author: abe<wechat:abrahamgreyson>
Date: 2024/6/13 11:01:15
"""
from typing import List

from .base_cloud_provider import BaseCloudProvider
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkvpc.v3 import VpcClient, ListSecurityGroupRulesRequest, DeleteSecurityGroupRuleRequest, \
    BatchCreateSecurityGroupRulesRequest, BatchCreateSecurityGroupRulesOption, BatchCreateSecurityGroupRulesRequestBody
from huaweicloudsdkvpc.v3.region.vpc_region import VpcRegion
from huaweicloudsdkcore.exceptions import exceptions

from update_whitelist.logger import get_logger

logger = get_logger()


class HuaweiCloud(BaseCloudProvider):

    def delete_rules(self, group_id, rules) -> None:
        """
        删除规则
        """
        try:
            # 删除接口只支持单个删除
            for rule in rules:
                request = DeleteSecurityGroupRuleRequest()
                request.security_group_rule_id = rule.id
                response = self.client.delete_security_group_rule(request)
                print(response)
        except exceptions.ClientRequestException as e:
            BaseCloudProvider.log(e)
        return None

    def add_rules(self, group_id, rules, ip):
        """ 批量添加规则 """
        try:
            request = BatchCreateSecurityGroupRulesRequest()
            request.security_group_id = group_id
            rules_body = [
                BatchCreateSecurityGroupRulesOption(
                    description=f"from Wulihe{' - ' + rule['desc'] if rule.get('desc') else ''}",
                    direction="ingress",
                    protocol="tcp",
                    multiport=str(rule['port']),
                    remote_ip_prefix=str(ip)
                ) for rule in rules
            ]
            request.body = BatchCreateSecurityGroupRulesRequestBody(
                security_group_rules=rules_body
            )
            response = self.client.batch_create_security_group_rules(request)
            logger.info(f"Added {len(rules)} rules to {group_id}")
        except exceptions.ClientRequestException as e:
            BaseCloudProvider.log(e)

    def initialize_client(self):
        """ 初始化客户端 """
        credentials = BasicCredentials(self.access_key, self.secret_key)
        # 创建服务客户端
        self.client = VpcClient.new_builder() \
            .with_credentials(credentials) \
            .with_region(VpcRegion.value_of(self.region)) \
            .build()
        pass

    def get_rules(self, group_id) -> List:
        """
        获取安全组规则
        """
        try:
            request = ListSecurityGroupRulesRequest()
            group_id_list = [
                group_id
            ]
            request.security_group_id = group_id_list
            response = self.client.list_security_group_rules(request)
            rules = response.security_group_rules
            # 过滤规则
            return [
                rule for rule in rules
                if getattr(rule, 'description', None) and getattr(rule, 'description').startswith("from Wulihe") and
                   getattr(rule, 'direction', None) and getattr(rule, 'direction') == "ingress"
            ]

        except exceptions.ClientRequestException as e:
            BaseCloudProvider.log(e)
            return []

