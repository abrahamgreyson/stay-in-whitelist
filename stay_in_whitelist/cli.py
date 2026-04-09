"""
Stay in Whitelist CLI - 自动更新云服务安全组白名单
"""

import argparse
import fcntl
import os
from functools import partial

from apscheduler.schedulers.blocking import BlockingScheduler

from stay_in_whitelist.config.config import load_config
from stay_in_whitelist.ip_fetcher import get_current_ip, load_cached_ip, cache_ip
from stay_in_whitelist.updater import Updater, CLOUD_PROVIDER_FIELDS
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
            # Cache new IP only AFTER successful update
            cache_ip(current_ip, config)
            logger.info("云服务白名单更新成功.")
        else:
            logger.info("IP 地址没有更改，无需更新云服务白名单")
    except Exception as e:
        logger.error(f"更新云服务白名单出错: {e}")


def look_at_rules(config, updater):
    """
    只读模式：枚举所有已配置的安全组现有规则并以表格形式打印到 stdout。
    不修改任何规则，不影响 IP 缓存，不启动调度器。
    """
    for provider_name in CLOUD_PROVIDER_FIELDS:
        provider_config = getattr(config, provider_name, None)
        if provider_config is None:
            continue

        access_key = provider_config.access_key
        secret_key = provider_config.secret_key

        for region_config in provider_config.regions:
            region = region_config.region
            for rule in region_config.rules:
                sg = rule.sg
                print(f"Provider: {provider_name}  Region: {region}  SG: {sg}")

                updater.set_client(provider_name, access_key, secret_key, region, config.rule_prefix)
                rules = updater.fetch_security_group_rules(sg)

                if not rules:
                    print("  (无符合条件的规则)")
                    continue

                # Determine column widths dynamically
                rows = []
                for r in rules:
                    if isinstance(r, dict):
                        port = str(r.get('Port', '-'))
                        cidr = str(r.get('CidrBlock', '-'))
                        index = str(r.get('PolicyIndex', '-'))
                        desc = str(r.get('PolicyDescription', '-'))
                    else:
                        port = str(getattr(r, 'multiport', '-'))
                        cidr = str(getattr(r, 'remote_ip_prefix', '-'))
                        index = str(getattr(r, 'id', '-'))
                        desc = str(getattr(r, 'description', '-'))
                    rows.append((port, cidr, index, desc))

                headers = ('Port', 'IP/CIDR', 'Index', 'Description')
                col_widths = [
                    max(len(headers[i]), max(len(row[i]) for row in rows))
                    for i in range(4)
                ]

                def fmt_row(fields):
                    return '| ' + ' | '.join(
                        f.ljust(col_widths[i]) for i, f in enumerate(fields)
                    ) + ' |'

                separator = '+-' + '-+-'.join('-' * w for w in col_widths) + '-+'
                print(separator)
                print(fmt_row(headers))
                print(separator)
                for row in rows:
                    print(fmt_row(row))
                print(separator)


def main():
    """
    启动定时任务
    """
    parser = argparse.ArgumentParser(description='Stay in Whitelist - 自动更新云服务安全组白名单')
    parser.add_argument('--debug', action='store_true', help='调试模式：跳过定时器，直接执行一次检查后退出')
    parser.add_argument('--force', action='store_true', help='强制更新：清空 IP 缓存，强制触发白名单更新')
    parser.add_argument('--look', action='store_true', help='查看模式：打印所有安全组现有规则后退出')
    args, _ = parser.parse_known_args()

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

    # Look mode: read-only, enumerate all rules and exit.
    # Must be checked BEFORE --force to ensure full mutual exclusivity.
    if args.look:
        updater = Updater()
        look_at_rules(config, updater)
        return

    # Force mode: clear IP cache to trigger update
    if args.force:
        cache_path = config.paths.ip_cache or 'ip_cache.txt'
        if os.path.exists(cache_path):
            os.remove(cache_path)
            logger.info("已清空 IP 缓存")

    # Debug mode: run once and exit
    if args.debug:
        logger.info("调试模式：执行一次检查后退出")
        check_and_update_ip(config)
        return

    logger.info(f"Stay in Whitelist 已启动，每 {config.check_interval} 秒检查一次 IP 变化")

    # 防止多进程并发：抢占文件锁，已有实例运行时直接退出
    lock_path = '/tmp/stay-in-whitelist.lock'
    lock_file = open(lock_path, 'w')
    try:
        fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        logger.error("另一个 Stay in Whitelist 实例正在运行，退出")
        lock_file.close()
        return

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
        logger.info("Stay in Whitelist 已停止")
