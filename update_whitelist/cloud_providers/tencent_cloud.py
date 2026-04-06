"""
Author: abe<wechat:abrahamgreyson>
Date: 2024/6/13 11:00:59
"""

from .base_cloud_provider import BaseCloudProvider
import json
import types
from tencentcloud.common import credential
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.vpc.v20170312 import vpc_client, models

from update_whitelist.logger import get_logger

logger = get_logger()


class TencentCloud(BaseCloudProvider):
    def get_rules(self, group_id):
        """
        获取安全组下符合条件的规则
        """
        # 实例化一个请求对象,每个接口都会对应一个request对象
        try:
            req = models.DescribeSecurityGroupPoliciesRequest()
            params = {
                "SecurityGroupId": str(group_id)
            }
            req.from_json_string(json.dumps(params))
            # 返回的resp是一个DescribeSecurityGroupPoliciesResponse的实例，与请求对象对应
            resp = self.client.DescribeSecurityGroupPolicies(req)
            # 输出json格式的字符串回包
            rules = json.loads(resp.to_json_string()).get("SecurityGroupPolicySet").get("Ingress")
            filtered_rules = [rule for rule in rules if rule['PolicyDescription'].startswith('from Wulihe')]
            return filtered_rules
        except TencentCloudSDKException as err:
            BaseCloudProvider.log(err)
            return []

    def add_rules(self, group_id, rules, ip):
        """ 添加安全组规则 """
        try:
            req = models.CreateSecurityGroupPoliciesRequest()
            params = {
                "SecurityGroupId": group_id,
                "SecurityGroupPolicySet": {
                    "Ingress": [
                        {
                            "Protocol": "tcp",
                            "Port": str(rule['port']),
                            "CidrBlock": ip,
                            "Action": "accept",
                            "PolicyDescription": f"from Wulihe{' - ' + rule['desc'] if rule.get('desc') else ''}"
                        } for rule in rules
                    ]
                }
            }
            req.from_json_string(json.dumps(params))
            resp = self.client.CreateSecurityGroupPolicies(req)
            logger.debug(resp.to_json_string())
            # 输出json格式的字符串回包
        except TencentCloudSDKException as err:
            BaseCloudProvider.log(err)

    def delete_rules(self, group_id, rules):
        """ 删除安全组规则 """
        # 实例化一个请求对象,每个接口都会对应一个request对象
        try:
            req = models.DeleteSecurityGroupPoliciesRequest()
            params = {
                "SecurityGroupId": str(group_id),
                "SecurityGroupPolicySet": {
                    "Ingress": [
                        {
                            "PolicyIndex": rule['PolicyIndex']
                        } for rule in rules
                    ]
                }
            }
            req.from_json_string(json.dumps(params))
            resp = self.client.DeleteSecurityGroupPolicies(req)
            logger.debug(resp.to_json_string())
        except TencentCloudSDKException as err:
            BaseCloudProvider.log(err)

    def initialize_client(self):
        cred = credential.Credential(self.access_key, self.secret_key)
        self.client = vpc_client.VpcClient(cred, self.region)
