"""
Author: abe<wechat:abrahamgreyson>
Date: 2024/6/13 16:40:14

程序入口，用于定期检查 IP 地址变化，并更新云提供商的白名单
"""

from functools import partial

from apscheduler.schedulers.blocking import BlockingScheduler

from stay_in_whitelist.config.config import load_config
from stay_in_whitelist.ip_fetcher import get_current_ip, load_cached_ip, cache_ip
from stay_in_whitelist.updater import Updater
from stay_in_whitelist.logger import get_logger, reconfigure_logging
import requests

logger = get_logger()


def has_ip_changed(config):
    """
    检查本级 IP 地址是否变化
    """
    try:
        current_ip = get_current_ip(config)
        if not current_ip:
            logger.error("获取 IP 失败：IP 为空")
            return False, None
    except (requests.RequestException, requests.Timeout) as e:
        logger.error(f"网络请求失败: {type(e).__name__} - {e}")
        return False, None
    except Exception as e:
        logger.error(f"获取 IP 时发生未知错误: {type(e).__name__} - {e}")
        return False, None

    cached_ip = load_cached_ip(config)

    if current_ip != cached_ip:
        cache_ip(current_ip, config)
        return True, current_ip
    return False, current_ip


def check_and_update_ip(config):
    """
    检查 IP 地址是否变化，如果变化则更新云服务的白名单
    """
    try:
        ip_changed, current_ip = has_ip_changed(config)
        if ip_changed:
            logger.info(f"IP 地址已经更改：{current_ip}. 更新云服务白名单.")
            updater = Updater()
            updater.update_cloud_providers(current_ip, config)
            logger.info("云服务白名单更新成功.")
        else:
            logger.info("IP 地址没有更改，无需更新云服务白名单")
    except Exception as e:
        logger.error(f"更新云服务白名单出错: {e}")


def main():
    """
    启动定时任务
    """
    try:
        config = load_config()
    except (FileNotFoundError, ValueError) as e:
        logger.error(f"配置加载失败: {e}")
        return
    except Exception as e:
        logger.error(f"配置加载出错: {e}")
        return

    # Reconfigure logger if custom log path specified
    if config.paths.log_file:
        reconfigure_logging(config.paths.log_file)

    scheduler = BlockingScheduler()

    # Configure misfire handling to prevent silent job skipping
    scheduler.configure(job_defaults={
        'misfire_grace_time': 300,  # 5 minutes grace for 10-minute intervals
        'coalesce': True,           # Combine missed runs into one
        'max_instances': 1          # Prevent overlapping executions
    })

    job = partial(check_and_update_ip, config=config)
    scheduler.add_job(job, 'interval', seconds=config.check_interval)

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        pass


if __name__ == "__main__":
    main()
