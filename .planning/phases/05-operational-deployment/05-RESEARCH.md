# Phase 5: Operational Deployment - Research

**Researched:** 2026-04-07
**Domain:** Python daemon deployment with APScheduler, systemd service management, logging infrastructure
**Confidence:** HIGH

## Summary

This phase ensures the Stay in Whitelist daemon runs reliably as a systemd service with proper scheduler configuration and sufficient log retention for security auditing. The research covers three critical areas: APScheduler misfire handling to prevent silent job skipping, systemd service configuration best practices for Python daemons, and log rotation strategy for 30-day audit trails.

**Primary recommendation:** Configure APScheduler with explicit `misfire_grace_time` via `job_defaults`, update systemd service template with correct paths for the renamed project, and change TimedRotatingFileHandler to rotate daily at midnight with `backupCount=30` for 30-day retention.

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| OPS-01 | APScheduler configured with explicit `misfire_grace_time` — prevents silent job skipping | APScheduler job_defaults configuration, misfire handling patterns |
| OPS-02 | systemd service unit template updated with correct `WorkingDirectory` and `StandardOutput`/`StandardError` paths | systemd Python daemon best practices, path configuration |
| OPS-03 | Log retention period increased from 7 to 30 days — improves audit trail for security tool | TimedRotatingFileHandler configuration, rotation strategies |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| APScheduler | 3.10.4 (project) / 3.11.2 (latest) | Periodic job scheduling | Industry-standard Python scheduler; BlockingScheduler for daemon processes |
| Python logging.handlers.TimedRotatingFileHandler | stdlib | Log rotation | Built-in, no dependencies, reliable time-based rotation |
| systemd | Linux standard | Service management | Native Linux service orchestration with auto-restart, logging integration |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytz | Optional | Timezone support for scheduler | Only if timezone-aware scheduling needed (not required for this project) |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| TimedRotatingFileHandler | systemd journal with StandardOutput=journal | Journal is modern best practice, but current architecture uses file-based logging; migration to journal is deferred to v2 |
| APScheduler | cron/systemd timers | APScheduler provides Python-native scheduling with better error handling and job introspection |

**Installation:**
```bash
# APScheduler already installed in project
# No new dependencies required for this phase
```

**Version verification:**
- APScheduler 3.10.4: Currently in `pyproject.toml`
- Latest stable: 3.11.2 (verified 2026-04-07 via pip)
- Recommendation: Keep 3.10.4 for stability; upgrade is optional

## Architecture Patterns

### Recommended Project Structure (Current)
```
stay-in-whitelist/
├── main.py                        # Entry point, APScheduler setup
├── config.yaml                    # Configuration (gitignored)
├── stay_in_whitelist/
│   ├── logger.py                  # TimedRotatingFileHandler setup
│   ├── ip_fetcher.py              # IP detection logic
│   ├── updater.py                 # Cloud provider orchestration
│   └── config/
│       └── config.py              # Pydantic config models
└── stay-in-whitelist.service      # systemd service template (to be created)
```

### Pattern 1: APScheduler Configuration with Misfire Handling

**What:** Configure scheduler with explicit `job_defaults` to prevent silent job skipping when the system is busy or recovering from sleep/hibernation.

**When to use:** All long-running daemon processes with periodic jobs where missed executions are unacceptable.

**Example:**
```python
from apscheduler.schedulers.blocking import BlockingScheduler

# Current implementation (main.py line 79-81)
scheduler = BlockingScheduler()
job = partial(check_and_update_ip, config=config)
scheduler.add_job(job, 'interval', seconds=config.check_interval)

# RECOMMENDED: Add explicit job_defaults
scheduler = BlockingScheduler()
scheduler.configure(job_defaults={
    'misfire_grace_time': 300,  # 5 minutes - allow late execution
    'coalesce': True,           # Combine multiple missed runs into one
    'max_instances': 1          # Prevent overlapping executions
})

job = partial(check_and_update_ip, config=config)
scheduler.add_job(job, 'interval', seconds=config.check_interval)
```

**Source:** [APScheduler User Guide - Missed job executions and coalescing](https://apscheduler.readthedocs.io/en/3.x/userguide.html)

**Rationale:**
- `misfire_grace_time=300`: With 600-second (10-minute) check intervals, a 5-minute grace period ensures jobs execute even if slightly delayed by system load or network latency
- `coalesce=True`: If multiple executions are missed (e.g., during system sleep), run only the most recent instead of queuing all missed runs
- `max_instances=1`: Prevent overlapping security group updates which could cause race conditions

### Pattern 2: systemd Service Configuration for Python Daemons

**What:** Create a systemd service unit file following best practices for Python daemon deployment.

**When to use:** All Python services deployed on Linux systems with systemd.

**Example:**
```ini
[Unit]
Description=Stay in Whitelist - Auto-update cloud security group whitelists
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=%USER%
Group=%GROUP%
WorkingDirectory=/path/to/stay-in-whitelist
Environment="PATH=/path/to/stay-in-whitelist/venv/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=/path/to/stay-in-whitelist/venv/bin/python /path/to/stay-in-whitelist/main.py
StandardOutput=append:/path/to/stay-in-whitelist/stay_in_whitelist.log
StandardError=append:/path/to/stay-in-whitelist/stay_in_whitelist.log
Restart=on-failure
RestartSec=10

# Security hardening
ProtectSystem=strict
ProtectHome=read-only
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

**Sources:**
- [systemd.exec man page - StandardOutput/StandardError](https://www.freedesktop.org/software/systemd/man/systemd.exec.html)
- [Python systemd logging best practices](https://github.com/torfsen/python-systemd-tutorial)

**Key Configuration Decisions:**
- `Type=simple`: Correct for BlockingScheduler (runs in foreground)
- `After=network-online.target`: Wait for network to be available before starting
- `WorkingDirectory`: **MUST** be updated from old `update_whitelist` to `stay_in_whitelist`
- `StandardOutput=append:/path/to/stay_in_whitelist.log`: Append to log file (systemd v240+)
  - Alternative: `StandardOutput=journal` to use systemd journal instead
- `Restart=on-failure`: Auto-restart on crashes, but not on clean exits
- `RestartSec=10`: Delay before restart to prevent rapid crash loops

**Migration Note:**
The project was renamed from `update_whitelist` to `stay_in_whitelist`. The systemd template must reference:
- `WorkingDirectory=/path/to/stay-in-whitelist` (directory name unchanged)
- `ExecStart` path with `stay-in-whitelist` directory
- `StandardOutput`/`StandardError` pointing to `stay_in_whitelist.log` (new log filename)

### Pattern 3: Log Rotation for Audit Trails

**What:** Configure TimedRotatingFileHandler for daily rotation with 30-day retention to support security audit requirements.

**When to use:** Security tools requiring sufficient log history for incident investigation.

**Example:**
```python
from logging.handlers import TimedRotatingFileHandler

# Current implementation (logger.py line 26)
fh = TimedRotatingFileHandler('stay_in_whitelist.log', when='H', interval=24, backupCount=7)

# RECOMMENDED: Rotate at midnight, keep 30 days
fh = TimedRotatingFileHandler(
    filename='stay_in_whitelist.log',
    when='midnight',      # Rotate at midnight each day
    interval=1,           # Every 1 day (redundant with 'midnight' but explicit)
    backupCount=30        # Keep 30 backup files (30 days of logs)
)
```

**Sources:**
- [Python docs: logging.handlers.TimedRotatingFileHandler](https://docs.python.org/3/library/logging.handlers.html#timedrotatingfilehandler)
- [GitHub Gist: TimedRotatingFileHandler example](https://gist.github.com/adejones/71c36c8a32990f9d6adf27758aec146b)

**Rationale:**
- `when='midnight'`: Clear daily rotation boundary; easier to find logs for specific dates
- `backupCount=30`: 30 days provides sufficient audit trail for a security tool while limiting disk usage
  - At ~1-10 MB/day (typical for this daemon), 30 days = 30-300 MB total
  - 7-day retention (current) is insufficient for security incident investigation
- Old log files are automatically deleted when `backupCount` limit is reached

**Important:** The `reconfigure_logging()` function (logger.py line 53) must also update `backupCount=30` when creating new handlers.

### Anti-Patterns to Avoid

1. **Missing misfire_grace_time configuration**
   - **Why it's bad:** Jobs silently skip when system is busy or recovering from sleep, leading to missed IP change detections
   - **What to do instead:** Always configure explicit `misfire_grace_time` in `job_defaults`

2. **Using StandardOutput=journal with file-based logging in Python**
   - **Why it's bad:** Duplicates logs (Python writes to file via TimedRotatingFileHandler, systemd also captures stdout)
   - **What to do instead:** Either use journal exclusively (modern approach) or file exclusively (current approach); don't mix both

3. **Setting misfire_grace_time too high (e.g., hours)**
   - **Why it's bad:** Stale jobs run unexpectedly long after they should have been skipped
   - **What to do instead:** Set to reasonable fraction of interval (e.g., 5 minutes for 10-minute intervals)

4. **Using Type=forking with BlockingScheduler**
   - **Why it's bad:** BlockingScheduler runs in foreground; `Type=simple` is correct
   - **What to do instead:** Use `Type=simple` for all Python daemons using BlockingScheduler

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Log rotation | Custom file rotation with os.rename/ cron jobs | TimedRotatingFileHandler | Built-in, handles edge cases (midnight rollover, concurrent writes), automatic cleanup |
| Scheduler with misfire handling | Custom time-based loop with threading.Timer | APScheduler with job_defaults | Proven library handles coalescing, misfire grace time, thread safety |
| systemd service template from scratch | Guessing service configuration | Established patterns from documentation | systemd has many security/hardening options; incorrect config leads to subtle failures |
| Log aggregation | Custom script to merge log files | journalctl or external tools (if using journal) | Built-in query capabilities, structured metadata |

**Key insight:** Operational deployment infrastructure (scheduling, logging, service management) is deceptively complex. Use battle-tested libraries and patterns instead of custom implementations.

## Common Pitfalls

### Pitfall 1: Silent Job Skipping Due to Missing misfire_grace_time

**What goes wrong:** Jobs don't run when expected, no error messages, IP changes are missed.

**Why it happens:** APScheduler's default `misfire_grace_time` is 1 second. If the system is busy (e.g., during boot, after wake from sleep, high CPU load), jobs are considered "misfired" and skipped.

**How to avoid:**
1. Configure explicit `misfire_grace_time` in scheduler `job_defaults`
2. Set to reasonable value (e.g., 300 seconds = 5 minutes for 10-minute intervals)
3. Enable `coalesce=True` to combine multiple missed runs into one execution

**Warning signs:**
- Gaps in log timestamps longer than expected interval
- IP changes not detected for extended periods
- Log messages like "Job ... missed" (if DEBUG logging enabled)

**Detection:**
```bash
# Check for gaps in log timestamps
grep "IP 地址没有更改" stay_in_whitelist.log | tail -20

# If gaps > check_interval, misfiring is occurring
```

### Pitfall 2: Incorrect WorkingDirectory in systemd Service

**What goes wrong:** Service fails to start with "cannot find module" or "file not found" errors.

**Why it happens:** After project rename from `update_whitelist` to `stay_in_whitelist`, systemd template still references old paths.

**How to avoid:**
1. Use absolute paths for all directories in systemd unit file
2. Verify `WorkingDirectory` matches actual project directory
3. Test service with `systemctl start stay-in-whitelist` before enabling

**Warning signs:**
- `systemctl status stay-in-whitelist` shows exit code 1-5
- Journal logs: "ModuleNotFoundError: No module named 'stay_in_whitelist'"
- File path errors in StandardOutput/StandardError

**Fix:**
```ini
# WRONG (old project name)
WorkingDirectory=/home/user/update_whitelist
ExecStart=/home/user/update_whitelist/venv/bin/python main.py

# CORRECT (new project name)
WorkingDirectory=/home/user/stay-in-whitelist
ExecStart=/home/user/stay-in-whitelist/venv/bin/python main.py
```

### Pitfall 3: Log Rotation Not Working (backupCount Not Applied)

**What goes wrong:** Log files accumulate indefinitely, consuming disk space, or rotation doesn't happen.

**Why it happens:**
1. `backupCount` set but rotation never triggers (wrong `when`/`interval` combination)
2. Permission issues preventing file deletion
3. Using `when='H'` with `interval=24` instead of `when='midnight'` (confusing semantics)

**How to avoid:**
1. Use `when='midnight'` for daily rotation (clearest semantics)
2. Set `backupCount` explicitly
3. Verify rotation works by checking for multiple log files after 24 hours

**Warning signs:**
- Only one log file exists after days/weeks of running
- Log file grows indefinitely (GB size)
- No `.1`, `.2`, `.3` suffix files

**Test:**
```bash
# After running for 2+ days
ls -lh stay_in_whitelist.log*
# Should see: stay_in_whitelist.log, stay_in_whitelist.log.1, etc.
```

### Pitfall 4: Service Doesn't Restart After Crash

**What goes wrong:** Daemon crashes and stays down, requiring manual restart.

**Why it happens:** `Restart=` not configured in systemd service unit, or set to `Restart=no`.

**How to avoid:**
```ini
[Service]
Restart=on-failure
RestartSec=10
```

**Warning signs:**
- Service status shows "inactive (dead)" after crash
- No automatic recovery after transient failures (network outages, API rate limits)

### Pitfall 5: Overlapping Job Executions Causing Race Conditions

**What goes wrong:** Multiple instances of `check_and_update_ip()` run simultaneously, causing duplicate security group rules or API conflicts.

**Why it happens:** `max_instances` not set, and job execution takes longer than interval (e.g., slow cloud API responses).

**How to avoid:**
```python
scheduler.configure(job_defaults={
    'max_instances': 1  # Only one instance of each job at a time
})
```

**Warning signs:**
- Duplicate security group rules with same IP
- API rate limit errors
- Log entries showing overlapping timestamps for same job

## Code Examples

### APScheduler Configuration with Misfire Handling

```python
# Source: APScheduler 3.x documentation
# https://apscheduler.readthedocs.io/en/3.x/userguide.html

from apscheduler.schedulers.blocking import BlockingScheduler
from functools import partial

def main():
    # ... config loading ...

    # Create scheduler with explicit misfire handling
    scheduler = BlockingScheduler()

    # Configure job defaults (applies to all jobs unless overridden)
    scheduler.configure(job_defaults={
        'misfire_grace_time': 300,  # 5 minutes grace period
        'coalesce': True,           # Combine missed executions
        'max_instances': 1          # Prevent overlapping runs
    })

    # Add job
    job = partial(check_and_update_ip, config=config)
    scheduler.add_job(job, 'interval', seconds=config.check_interval)

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        pass
```

### TimedRotatingFileHandler for 30-Day Retention

```python
# Source: Python logging.handlers documentation
# https://docs.python.org/3/library/logging.handlers.html#timedrotatingfilehandler

import logging
from logging.handlers import TimedRotatingFileHandler

def get_logger(name=__name__):
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    if not logger.handlers:
        # Console handler
        ch = logging.StreamHandler()
        ch.setLevel(logging.DEBUG)

        # File handler - daily rotation at midnight, 30-day retention
        fh = TimedRotatingFileHandler(
            filename='stay_in_whitelist.log',
            when='midnight',      # Rotate at midnight
            interval=1,           # Every day
            backupCount=30        # Keep 30 days of logs
        )
        fh.setLevel(logging.DEBUG)

        # Formatter
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        ch.setFormatter(formatter)
        fh.setFormatter(formatter)

        logger.addHandler(ch)
        logger.addHandler(fh)

    return logger

def reconfigure_logging(log_file_path: str) -> None:
    """Replace TimedRotatingFileHandler with new path and 30-day retention."""
    for name in logging.root.manager.loggerDict:
        log = logging.getLogger(name)
        old_handlers = [h for h in log.handlers if isinstance(h, TimedRotatingFileHandler)]
        for h in old_handlers:
            h.close()
            log.removeHandler(h)
        if old_handlers:
            fh = TimedRotatingFileHandler(
                filename=log_file_path,
                when='midnight',
                interval=1,
                backupCount=30  # 30-day retention
            )
            fh.setLevel(logging.DEBUG)
            fh.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
            log.addHandler(fh)
```

### systemd Service Unit Template

```ini
# stay-in-whitelist.service

[Unit]
Description=Stay in Whitelist - Auto-update cloud security group whitelists
Documentation=https://github.com/your-org/stay-in-whitelist
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=%USER%
Group=%GROUP%
WorkingDirectory=/absolute/path/to/stay-in-whitelist
Environment="PATH=/absolute/path/to/stay-in-whitelist/venv/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=/absolute/path/to/stay-in-whitelist/venv/bin/python /absolute/path/to/stay-in-whitelist/main.py

# Logging - append to log file (Python's TimedRotatingFileHandler manages rotation)
StandardOutput=append:/absolute/path/to/stay-in-whitelist/stay_in_whitelist.log
StandardError=append:/absolute/path/to/stay-in-whitelist/stay_in_whitelist.log

# Restart behavior
Restart=on-failure
RestartSec=10

# Security hardening
ProtectSystem=strict
ProtectHome=read-only
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

**Usage:**
```bash
# Copy template and replace placeholders
sudo cp stay-in-whitelist.service /etc/systemd/system/
sudo sed -i 's|%USER%|yourusername|g' /etc/systemd/system/stay-in-whitelist.service
sudo sed -i 's|%GROUP%|yourgroup|g' /etc/systemd/system/stay-in-whitelist.service
sudo sed -i 's|/absolute/path/to|/home/yourusername|g' /etc/systemd/system/stay-in-whitelist.service

# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable stay-in-whitelist
sudo systemctl start stay-in-whitelist

# Check status
sudo systemctl status stay-in-whitelist
journalctl -u stay-in-whitelist -f
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual cron jobs | systemd timers or APScheduler | 2020s | Better error handling, logging, restart behavior |
| Log to file with logrotate | Log to systemd journal | ~2018 | Centralized log management, structured metadata |
| Type=forking daemons | Type=simple with supervisor | ~2015 | Simpler service code, better process management |
| No misfire handling | Explicit misfire_grace_time | APScheduler 3.x | Prevents silent job skipping |

**Deprecated/outdated:**
- **Type=forking for Python daemons**: Use `Type=simple` with BlockingScheduler or BackgroundScheduler
- **StandardOutput=file with logrotate**: Use `StandardOutput=journal` or `append:` (systemd v240+)
- **Default APScheduler misfire_grace_time (1 sec)**: Too aggressive for production; always configure explicitly

## Open Questions

1. **Should we migrate from file-based logging to systemd journal?**
   - **What we know:** Journal is modern best practice, provides structured logging, better querying
   - **What's unclear:** Migration effort, impact on existing log analysis workflows
   - **Recommendation:** Defer to v2 requirements; for v1, keep file-based logging with 30-day retention to minimize changes

2. **What value for misfire_grace_time is optimal?**
   - **What we know:** Default (1 sec) is too aggressive; need to balance between catching missed jobs and not running very stale jobs
   - **What's unclear:** Exact value depends on system load patterns and network latency
   - **Recommendation:** Start with 300 seconds (5 minutes) for 600-second intervals; monitor logs and adjust if needed

3. **Should we add systemd watchdog (WatchdogSec) for health monitoring?**
   - **What we know:** systemd can monitor service health via sd_notify; requires code changes
   - **What's unclear:** Implementation complexity vs. value for this use case
   - **Recommendation:** Defer to v2 requirements (listed in ROADMAP.md as "systemd WatchdogSec integration via sd_notify")

## Environment Availability

> This phase has external dependencies on systemd and Python 3.9+ runtime.

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.9+ | Runtime | ✓ | 3.13.11 (verified) | — |
| systemd | Service management | ✓ (Linux standard) | — | Manual execution via `python main.py` |
| git | setuptools_scm versioning | ✓ | — | — |
| pip/venv | Package installation | ✓ | — | — |

**Missing dependencies with no fallback:**
- None — all required tools available

**Missing dependencies with fallback:**
- None

**Verification:**
```bash
# Check Python version
python3 --version  # Output: Python 3.13.11

# Check systemd availability
systemctl --version  # Expected: systemd 245+ on modern Linux

# Check project installation
pip3 show stay-in-whitelist  # Verify package metadata
```

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.2.2 |
| Config file | pyproject.toml `[tool.pytest.ini_options]` |
| Quick run command | `pytest -x` |
| Full suite command | `pytest --cov=stay_in_whitelist --cov-report=term-missing` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| OPS-01 | Scheduler configured with misfire_grace_time | unit | `pytest tests/test_main.py::test_scheduler_configuration -x` | ❌ Wave 0 (new test) |
| OPS-02 | Service unit template has correct paths | integration | `pytest tests/test_systemd_config.py -x` | ❌ Wave 0 (new test) |
| OPS-03 | Logger configured with backupCount=30 | unit | `pytest tests/test_logger.py::test_log_retention -x` | ❌ Wave 0 (new test) |

### Sampling Rate
- **Per task commit:** `pytest -x` (fail fast on first error)
- **Per wave merge:** `pytest --cov=stay_in_whitelist --cov-report=term-missing` (full suite with coverage)
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_main.py::test_scheduler_configuration` — verifies scheduler.configure() is called with misfire_grace_time, coalesce, max_instances
- [ ] `tests/test_logger.py::test_log_retention` — verifies TimedRotatingFileHandler backupCount=30
- [ ] `tests/test_systemd_config.py` — verifies service template contains correct WorkingDirectory and StandardOutput paths
- [ ] Framework install: `pip install -e .[dev]` — ensures pytest and coverage tools available

**Note:** Existing test infrastructure (conftest.py, test_main.py, test_config.py, etc.) provides good foundation. Wave 0 needs 3 new tests to cover phase-specific requirements.

## Sources

### Primary (HIGH confidence)
- [APScheduler 3.x User Guide](https://apscheduler.readthedocs.io/en/3.x/userguide.html) - Official documentation on misfire handling, job_defaults, coalescing
- [Python logging.handlers.TimedRotatingFileHandler](https://docs.python.org/3/library/logging.handlers.html#timedrotatingfilehandler) - Official documentation on when, interval, backupCount parameters
- [systemd.exec - Service Execution Configuration](https://www.freedesktop.org/software/systemd/man/systemd.exec.html) - Official systemd documentation on StandardOutput, StandardError, WorkingDirectory

### Secondary (MEDIUM confidence)
- [GitHub: python-systemd-tutorial](https://github.com/torfsen/python-systemd-tutorial) - Comprehensive tutorial on Python daemon deployment with systemd
- [Stack Overflow: APScheduler missing jobs after adding misfire_grace_time](https://stackoverflow.com/questions/41428118/apscheduler-missing-jobs-after-adding-misfire-grace-time) - Community discussion on misfire handling
- [GitHub Gist: TimedRotatingFileHandler example](https://gist.github.com/adejones/71c36c8a32990f9d6adf27758aec146b) - Practical example code for daily rotation with backupCount

### Tertiary (LOW confidence)
- [KubeBlogs: APScheduler Task Scheduling](https://www.kubeblogs.com/how-to-schedule-simple-tasks-using-apscheduler-a-devops-focused-guide/) - Blog post on APScheduler configuration (marked for validation)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All libraries are well-established with stable APIs (APScheduler, Python stdlib logging, systemd)
- Architecture: HIGH - Patterns are documented in official sources and widely adopted in production
- Pitfalls: HIGH - Based on official documentation and community-reported issues with known solutions

**Research date:** 2026-04-07
**Valid until:** 2026-10-07 (6 months - stable domain, but verify APScheduler versions periodically)
