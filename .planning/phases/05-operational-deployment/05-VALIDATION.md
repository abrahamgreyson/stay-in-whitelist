# Phase 5: Operational Deployment - Validation

**Phase:** 05
**Created:** 2026-04-08
**Status:** Pre-execution

## Requirements to Test Map

| Req ID | Behavior | Test File | Test Function | Type | Wave |
|--------|----------|-----------|---------------|------|------|
| OPS-01 | Scheduler configured with misfire_grace_time=300 | tests/test_main.py | test_scheduler_configuration | unit | 0 |
| OPS-01 | configure() called before add_job() | tests/test_main.py | test_scheduler_configuration | unit | 0 |
| OPS-03 | get_logger() creates handler with backupCount=30 | tests/test_logger.py | test_get_logger_retention | unit | 0 |
| OPS-03 | reconfigure_logging() creates handler with backupCount=30 | tests/test_logger.py | test_reconfigure_logging_retention | unit | 0 |
| OPS-02 | Service template has correct structure | tests/test_systemd_config.py | test_service_template_structure | integration | 0 |
| OPS-02 | Service paths are consistent | tests/test_systemd_config.py | test_service_paths_consistency | integration | 0 |
| OPS-02 | Network dependencies configured | tests/test_systemd_config.py | test_service_network_dependencies | integration | 0 |
| OPS-02 | Restart behavior configured | tests/test_systemd_config.py | test_service_restart_configuration | integration | 0 |
| OPS-02 | Log paths use correct filename | tests/test_systemd_config.py | test_service_logging_configuration | integration | 0 |

## Success Criteria Verification

| # | Criterion | Verified By | Method |
|---|-----------|-------------|--------|
| 1 | APScheduler misfire_grace_time explicitly configured | test_scheduler_configuration | Automated |
| 2 | systemd service template references correct paths | test_service_template_structure, test_service_paths_consistency | Automated |
| 3 | Log files retained for 30 days | test_get_logger_retention, test_reconfigure_logging_retention | Automated |

## Wave 0 Gaps

- [x] tests/test_main.py::test_scheduler_configuration — covered by Plan 05-01 Task 1
- [x] tests/test_logger.py::test_get_logger_retention — covered by Plan 05-01 Task 3
- [x] tests/test_logger.py::test_reconfigure_logging_retention — covered by Plan 05-01 Task 3
- [x] tests/test_systemd_config.py — covered by Plan 05-02 Task 2

## Sampling Rate

- **Per task:** `pytest -x`
- **Per plan merge:** `pytest --cov=stay_in_whitelist --cov-report=term-missing`
- **Phase gate:** Full suite green
