---
status: testing
phase: 05-operational-deployment
source: [05-01-SUMMARY.md, 05-02-SUMMARY.md, 05-03-SUMMARY.md, 05-04-SUMMARY.md]
started: 2026-04-08T06:00:00Z
updated: 2026-04-08T06:30:00Z
---

## Current Test

number: 2
name: Scheduler Misfire Recovery
expected: |
  When the scheduled job misses its execution time (e.g., system was suspended), the job runs within 5 minutes of the scheduled time instead of being silently skipped. Check the logs to confirm the misfire_grace_time=300 configuration is active.
awaiting: user response

## Tests

### 1. Cold Start Smoke Test
expected: Kill any running server/service. Clear ephemeral state (temp DBs, caches, lock files). Start the application from scratch. Server boots without errors, any seed/migration completes, and a primary query (health check, homepage load, or basic API call) returns live data.
result: pass
resolution: "Fixed by plan 05-04: upgraded pydantic to 2.9.2 for Python 3.13+ support. Application now starts successfully on Python 3.13.11 without PyO3 errors."

### 2. Scheduler Misfire Recovery
expected: When the scheduled job misses its execution time (e.g., system was suspended), the job runs within 5 minutes of the scheduled time instead of being silently skipped. Check the logs to confirm the misfire_grace_time=300 configuration is active.
result: issue
reported: "应用启动后 IP 检测和云 API 调用正常，但添加安全组规则时报错 'Allow' object has no attribute 'get'。同时 IP 检测结果不一致（requests 检测到 50.7.158.254，curl 显示 119.119.70.48），可能是 Clash 代理导致。"
severity: blocker

### 3. 30-Day Log Retention
expected: Log files are retained for 30 days and rotate daily at midnight. Check that the logger configuration uses backupCount=30 and when='midnight' rotation. Older log files beyond 30 days are automatically deleted.
result: [pending]

### 4. Systemd Service Deployment
expected: The stay-in-whitelist.service template can be deployed to /etc/systemd/system/. After customizing paths (WorkingDirectory, ExecStart, StandardOutput, StandardError), the service starts successfully with `systemctl start stay-in-whitelist` and shows active status.
result: [pending]

### 5. Network Dependency Configuration
expected: The systemd service unit includes After=network-online.target and Wants=network-online.target dependencies. Service waits for network to be ready before starting, preventing IP detection failures on boot.
result: [pending]

### 6. Service Restart on Failure
expected: The systemd service is configured with Restart=on-failure and RestartSec=5s. When the main process exits with a non-zero status, systemd automatically restarts it after a 5-second delay.
result: [pending]

### 7. README Deployment Documentation
expected: README.md contains a comprehensive deployment section between Configuration and Architecture. It includes service installation steps, path customization instructions, management commands (start/stop/restart/status), log management with 30-day retention, and troubleshooting guide.
result: [pending]

## Summary

total: 7
passed: 1
issues: 1
pending: 5
skipped: 0
blocked: 0

## Gaps

- truth: "Application can start from scratch on any Python 3.9+ environment including 3.13 and 3.14 (current stable in 2026)"
  status: resolved
  reason: "User reported: Python 3.13/3.14 不兼容 - pydantic 2.7.4 的依赖链 (pydantic-core 2.18.4 → PyO3 0.21.2) 只支持到 Python 3.12。pyproject.toml 声明 requires-python='>=3.9' 无上限，但 classifiers 只列到 3.12。2026年应支持 3.13/3.14。"
  severity: major
  test: 1
  artifacts: [pyproject.toml, pyproject.toml#L20]
  missing: ["pydantic version that supports Python 3.13+"]
  resolution: "Upgraded pydantic to 2.9.2 via gap closure plan 05-04. All 73 tests pass on Python 3.13.11. Application imports successfully. Python 3.13, 3.14 added to classifiers."
  resolved_by: 05-04-PLAN.md

- truth: "Security group rules can be added without errors"
  status: failed
  reason: "User reported: 'Allow' object has no attribute 'get' when adding security group rules. Likely caused by pydantic 2.9.2 upgrade - Pydantic BaseModel no longer has .get() method."
  severity: blocker
  test: 2
  artifacts: []
  missing: []
