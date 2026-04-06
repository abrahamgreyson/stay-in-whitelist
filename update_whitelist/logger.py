"""
Author: abe<wechat:abrahamgreyson>
Date: 2024/6/13 11:22:56

提供日志处理器
"""

import logging
from logging.handlers import TimedRotatingFileHandler


def get_logger(name=__name__):
    """
    获取日志对象
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # 如果日志器没有处理器，就添加一个新的处理器
    if not logger.handlers:
        # 创建一个流处理器
        ch = logging.StreamHandler()
        ch.setLevel(logging.DEBUG)

        # 创建一个文件处理器，每小时轮转一次日志文件
        fh = TimedRotatingFileHandler('update_whitelist.log', when='H', interval=24, backupCount=7)
        fh.setLevel(logging.DEBUG)

        # 创建一个格式器，并添加到处理器中
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        ch.setFormatter(formatter)
        fh.setFormatter(formatter)

        # 将处理器添加到日志器
        logger.addHandler(ch)
        logger.addHandler(fh)

    return logger


def reconfigure_logging(log_file_path: str) -> None:
    """
    Replace TimedRotatingFileHandler with new path. Safe to call multiple times.
    Called after load_config() if config.paths.log_file is specified.
    """
    for name in logging.root.manager.loggerDict:
        log = logging.getLogger(name)
        old_handlers = [h for h in log.handlers if isinstance(h, TimedRotatingFileHandler)]
        for h in old_handlers:
            h.close()
            log.removeHandler(h)
        if old_handlers:
            fh = TimedRotatingFileHandler(log_file_path, when='H', interval=24, backupCount=7)
            fh.setLevel(logging.DEBUG)
            fh.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
            log.addHandler(fh)
