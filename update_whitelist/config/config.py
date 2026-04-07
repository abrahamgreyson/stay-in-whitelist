"""
Author: abe<wechat:abrahamgreyson>
Date: 2024/6/13 16:40:14

Pydantic models for cloud provider configuration and a load_config() function
for loading configuration from a YAML file.

Usage:
    from update_whitelist.config.config import load_config
    config = load_config()          # uses default config.yaml path
    config = load_config("/path")   # uses explicit path

Importing this module does NOT trigger file I/O. Call load_config() explicitly.
"""

from pathlib import Path
from typing import List, Optional, Union

import yaml
from pydantic import BaseModel, field_validator


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


class Paths(BaseModel):
    ip_cache: Optional[str] = None
    log_file: Optional[str] = None


class Config(BaseModel):
    huawei: Optional[CloudProvider] = None
    tencent: Optional[CloudProvider] = None
    aliyun: Optional[CloudProvider] = None
    ipinfo: Optional[IPInfo] = None
    timeouts: TimeoutSettings = TimeoutSettings()
    check_interval: int = 600
    paths: Paths = Paths()
    rule_prefix: str = "from Wulihe"

    @field_validator('check_interval')
    @classmethod
    def validate_check_interval(cls, v):
        if v < 600:
            raise ValueError('check_interval must be >= 600 seconds')
        return v


def load_config(config_path: Optional[str] = None) -> Config:
    """
    Load and validate configuration from a YAML file.

    Args:
        config_path: Path to config YAML file. Defaults to config.yaml
                     in the project root (parent of update_whitelist/).

    Returns:
        Config: Validated Pydantic Config object.

    Raises:
        FileNotFoundError: If the config file does not exist.
        yaml.YAMLError: If the YAML is malformed.
        pydantic.ValidationError: If validation fails.
        ValueError: If the config file is empty.
    """
    if config_path is None:
        project_root = Path(__file__).resolve().parent.parent.parent
        config_path = str(project_root / 'config.yaml')
    else:
        config_path = str(Path(config_path).resolve())

    if not Path(config_path).exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with open(config_path, 'r') as f:
        config_data = yaml.safe_load(f)

    if config_data is None:
        raise ValueError(f"Configuration file is empty: {config_path}")

    return Config(**config_data)
