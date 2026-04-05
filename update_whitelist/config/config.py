"""
Author: abe<wechat:abrahamgreyson>
Date: 2024/6/13 16:40:14

定义了用于表示云提供商配置的 Pydantic 模型，并从配置文件中读取配置数据
我们暴露了 config 对象，使用时可以直接引用 config 对象获取配置数据
:example: config.huawei.regions[0].region
"""

import os
import yaml
from pydantic import BaseModel
from typing import List, Optional, Union


class Allow(BaseModel):
    port: Union[str, int]
    desc: Optional[str] = None


class Rule(BaseModel):
    sg: str
    allow: List[Allow]


class Region(BaseModel):
    region: str
    rules: List[Rule]


class CloudProvider(BaseModel):
    access_key: str
    secret_key: str
    regions: List[Region]

class IPInfo(BaseModel):
    tokens: list[str]  


class IPDetectionTimeout(BaseModel):
    connect: int = 3  # seconds
    read: int = 5     # seconds


class CloudAPITimeout(BaseModel):
    connect: int = 3  # seconds
    read: int = 10    # seconds


class TimeoutSettings(BaseModel):
    ip_detection: IPDetectionTimeout = IPDetectionTimeout()
    cloud_api: CloudAPITimeout = CloudAPITimeout()


class Config(BaseModel):
    huawei: Optional[CloudProvider] = None
    tencent: Optional[CloudProvider] = None
    aliyun: Optional[CloudProvider] = None
    ipinfo: Optional[IPInfo] = None
    timeouts: TimeoutSettings = TimeoutSettings()


# 读配置文件
current_path = os.path.dirname(os.path.abspath(__file__))
root_path = os.path.dirname(os.path.dirname(current_path))
config_path = os.path.join(root_path, 'config.yaml')
with open(config_path, 'r') as file:
    config_data = yaml.safe_load(file)
config = Config(**config_data)
