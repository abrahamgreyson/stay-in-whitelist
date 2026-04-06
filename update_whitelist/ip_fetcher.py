"""
Author: abe<wechat:abrahamgreyson>
Date: 2024/6/19 17:17:15
"""
import ipaddress
import requests
import os
from .logger import get_logger

logger = get_logger()

IP_PROVIDERS = [
    {
        "name": "ipinfo",
        "url": "https://ipinfo.io/ip",
        "needs_token": True,
    },
    {
        "name": "icanhazip",
        "url": "https://icanhazip.com",
        "needs_token": False,
    },
    {
        "name": "ipify",
        "url": "https://api.ipify.org",
        "needs_token": False,
    },
    {
        "name": "ifconfig.me",
        "url": "https://ifconfig.me",
        "needs_token": False,
    },
]


def get_current_ip(config):
    """
    Try IP detection providers in order, return first valid IP.
    Sequential fallback chain: ipinfo -> icanhazip -> ipify -> ifconfig.me
    Each provider has independent timeout.
    Returns None when all providers fail.
    """
    timeout_settings = config.timeouts.ip_detection
    timeout = (timeout_settings.connect, timeout_settings.read)

    for provider in IP_PROVIDERS:
        try:
            url = provider["url"]
            if provider["needs_token"]:
                if not config.ipinfo or not config.ipinfo.tokens:
                    logger.warning(f"Skipping {provider['name']}: no token configured")
                    continue
                url = f"{url}?token={config.ipinfo.tokens[0]}"

            logger.info(f"Trying {provider['name']} for IP detection...")
            response = requests.get(url, timeout=timeout)

            if response.status_code == 200:
                ip_str = response.text.strip()
                ipaddress.ip_address(ip_str)
                logger.info(f"Detected public IP: {ip_str} via {provider['name']}")
                return ip_str
            else:
                logger.warning(f"{provider['name']} returned status {response.status_code}")
        except requests.RequestException as e:
            logger.warning(f"Provider {provider['name']} request failed: {type(e).__name__}")
        except ValueError:
            logger.warning(f"Provider {provider['name']} returned invalid IP: {response.text.strip()[:50]}")

    logger.error("All IP detection providers failed, skipping this check cycle")
    return None


def load_cached_ip(config):
    """
    读取缓存的 IP 地址
    """
    cache_path = config.paths.ip_cache or 'ip_cache.txt'
    if os.path.exists(cache_path):
        with open(cache_path, 'r') as file:
            return file.read().strip()
    return None


def cache_ip(ip, config):
    """
    缓存当前 IP 地址
    """
    cache_path = config.paths.ip_cache or 'ip_cache.txt'
    with open(cache_path, 'w') as file:
        file.write(ip)
