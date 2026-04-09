"""
Author: abe<wechat:abrahamgreyson>
Date: 2024/6/25 11:34:49
"""

from stay_in_whitelist.cli import has_ip_changed, check_and_update_ip, main, look_at_rules


def test_has_ip_changed(mocker, mock_config):
    # 模拟 get_current_ip 和 load_cached_ip 函数的返回值
    mocker.patch('stay_in_whitelist.cli.get_current_ip', return_value='1.1.1.1')
    mocker.patch('stay_in_whitelist.cli.load_cached_ip', return_value='1.1.1.1')

    # 测试 has_ip_changed 函数
    ip_changed, current_ip = has_ip_changed(mock_config)
    assert not ip_changed
    assert current_ip == '1.1.1.1'

    # 修改模拟函数的返回值
    mocker.patch('stay_in_whitelist.cli.get_current_ip', return_value='2.2.2.2')

    # 再次测试 has_ip_changed 函数
    ip_changed, current_ip = has_ip_changed(mock_config)
    assert ip_changed
    assert current_ip == '2.2.2.2'


def test_check_and_update_ip(mocker, mock_config):
    # 模拟 has_ip_changed 函数的返回值
    mocker.patch('stay_in_whitelist.cli.has_ip_changed', return_value=(True, '1.1.1.1'))

    # 创建一个模拟的 Updater 实例
    mock_updater = mocker.patch('stay_in_whitelist.cli.Updater').return_value

    # 测试 check_and_update_ip 函数
    check_and_update_ip(mock_config)

    # 检查 Updater 的 update_cloud_providers 方法是否被正确地调用了一次
    mock_updater.update_cloud_providers.assert_called_once()


def test_main_loads_config_and_starts_scheduler(mocker, mock_config):
    mocker.patch('stay_in_whitelist.cli.load_config', return_value=mock_config)
    mock_scheduler = mocker.MagicMock()
    mocker.patch('stay_in_whitelist.cli.BlockingScheduler', return_value=mock_scheduler)
    mocker.patch('stay_in_whitelist.cli.reconfigure_logging')
    main()
    mock_scheduler.add_job.assert_called_once()
    call_args = mock_scheduler.add_job.call_args
    assert call_args[1]['seconds'] == 600  # mock_config.check_interval
    mock_scheduler.start.assert_called_once()


def test_main_exits_on_config_error(mocker):
    mocker.patch('stay_in_whitelist.cli.load_config', side_effect=FileNotFoundError("not found"))
    mock_scheduler = mocker.patch('stay_in_whitelist.cli.BlockingScheduler')
    main()
    mock_scheduler.assert_not_called()


def test_scheduler_configuration(mocker, mock_config):
    """Verify scheduler is configured with misfire handling before jobs are added."""
    mocker.patch('stay_in_whitelist.cli.load_config', return_value=mock_config)
    mocker.patch('stay_in_whitelist.cli.reconfigure_logging')

    mock_scheduler = mocker.MagicMock()
    mocker.patch('stay_in_whitelist.cli.BlockingScheduler', return_value=mock_scheduler)

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


def test_main_look_mode_calls_look_at_rules(mocker, mock_config):
    """--look 模式：加载 config、调用 look_at_rules、不启动 scheduler"""
    mocker.patch('stay_in_whitelist.cli.load_config', return_value=mock_config)
    mocker.patch('stay_in_whitelist.cli.reconfigure_logging')
    mock_look = mocker.patch('stay_in_whitelist.cli.look_at_rules')
    mock_scheduler_cls = mocker.patch('stay_in_whitelist.cli.BlockingScheduler')

    import sys
    mocker.patch.object(sys, 'argv', ['main.py', '--look'])
    main()

    mock_look.assert_called_once()
    mock_scheduler_cls.assert_not_called()


def test_look_at_rules_tencent(mocker, mock_config):
    """look_at_rules 对 Tencent 规则（dict 格式）正常输出表格"""
    mock_updater = mocker.MagicMock()
    mock_updater.fetch_security_group_rules.return_value = [
        {
            'Port': '3306',
            'CidrBlock': '1.2.3.4/32',
            'PolicyIndex': 5,
            'PolicyDescription': 'from Wulihe - mysql',
        }
    ]

    captured = []
    mocker.patch('builtins.print', side_effect=lambda *a, **_: captured.append(' '.join(str(x) for x in a)))

    look_at_rules(mock_config, mock_updater)

    output = '\n'.join(captured)
    assert '3306' in output
    assert '1.2.3.4/32' in output
    assert 'from Wulihe' in output


def test_look_at_rules_empty_sg(mocker, mock_config):
    """look_at_rules 对空安全组打印提示而不崩溃"""
    mock_updater = mocker.MagicMock()
    mock_updater.fetch_security_group_rules.return_value = []

    captured = []
    mocker.patch('builtins.print', side_effect=lambda *a, **_: captured.append(' '.join(str(x) for x in a)))

    look_at_rules(mock_config, mock_updater)

    output = '\n'.join(captured)
    assert '无符合条件' in output
