"""
Author: abe<wechat:abrahamgreyson>
Date: 2024/6/25 11:34:49
"""

import pytest
from main import has_ip_changed, check_and_update_ip, main


def test_has_ip_changed(mocker, mock_config):
    # 模拟 get_current_ip 和 load_cached_ip 函数的返回值
    mocker.patch('main.get_current_ip', return_value='1.1.1.1')
    mocker.patch('main.load_cached_ip', return_value='1.1.1.1')

    # 测试 has_ip_changed 函数
    ip_changed, current_ip = has_ip_changed(mock_config)
    assert not ip_changed
    assert current_ip == '1.1.1.1'

    # 修改模拟函数的返回值
    mocker.patch('main.get_current_ip', return_value='2.2.2.2')

    # 再次测试 has_ip_changed 函数
    ip_changed, current_ip = has_ip_changed(mock_config)
    assert ip_changed
    assert current_ip == '2.2.2.2'


def test_check_and_update_ip(mocker, mock_config):
    # 模拟 has_ip_changed 函数的返回值
    mocker.patch('main.has_ip_changed', return_value=(True, '1.1.1.1'))

    # 创建一个模拟的 Updater 实例
    mock_updater = mocker.patch('main.Updater').return_value

    # 测试 check_and_update_ip 函数
    check_and_update_ip(mock_config)

    # 检查 Updater 的 update_cloud_providers 方法是否被正确地调用了一次
    mock_updater.update_cloud_providers.assert_called_once()


def test_main_loads_config_and_starts_scheduler(mocker, mock_config):
    mocker.patch('main.load_config', return_value=mock_config)
    mock_scheduler = mocker.MagicMock()
    mocker.patch('main.BlockingScheduler', return_value=mock_scheduler)
    mocker.patch('main.reconfigure_logging')
    main()
    mock_scheduler.add_job.assert_called_once()
    call_args = mock_scheduler.add_job.call_args
    assert call_args[1]['seconds'] == 600  # mock_config.check_interval
    mock_scheduler.start.assert_called_once()


def test_main_exits_on_config_error(mocker):
    mocker.patch('main.load_config', side_effect=FileNotFoundError("not found"))
    mock_scheduler = mocker.patch('main.BlockingScheduler')
    main()
    mock_scheduler.assert_not_called()


def test_scheduler_configuration(mocker, mock_config):
    """Verify scheduler is configured with misfire handling before jobs are added."""
    mocker.patch('main.load_config', return_value=mock_config)
    mocker.patch('main.reconfigure_logging')

    mock_scheduler = mocker.MagicMock()
    mocker.patch('main.BlockingScheduler', return_value=mock_scheduler)

    # Prevent actual scheduler start which blocks
    mock_scheduler.start.side_effect = KeyboardInterrupt

    main()

    # Verify configure() called with correct job_defaults
    mock_scheduler.configure.assert_called_once()
    configure_kwargs = mock_scheduler.configure.call_args[1]
    job_defaults = configure_kwargs['job_defaults']
    assert job_defaults['misfire_grace_time'] == 300
    assert job_defaults['coalesce'] is True
    assert job_defaults['max_instances'] == 1

    # Verify configure() called before add_job()
    call_order = [str(c) for c in mock_scheduler.method_calls]
    configure_idx = next(i for i, c in enumerate(call_order) if 'configure' in c)
    add_job_idx = next(i for i, c in enumerate(call_order) if 'add_job' in c)
    assert configure_idx < add_job_idx, "configure() must be called before add_job()"
