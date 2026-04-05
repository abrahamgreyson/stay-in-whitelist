# Pitfalls Research

**Domain:** Dynamic IP whitelist updater for cloud security groups (systemd daemon)
**Researched:** 2026-04-04
**Confidence:** HIGH (codebase-confirmed + community-verified patterns)

## Critical Pitfalls

Mistakes that cause lockouts, silent failures, or data loss. These are the highest-priority issues to prevent.

### Pitfall 1: Delete-Before-Add Lockout (Non-Atomic Rule Update)

**What goes wrong:**
The updater deletes all existing security group rules before adding new ones. If the add API call fails (network error, rate limit, auth failure), the security group is left empty. The user is locked out of all services protected by that security group until manual intervention via cloud console.

**Why it happens:**
The "delete then add" pattern feels natural: clear old state, then write new state. It is also what the current code does in `updater.py` lines 46-63. Developers think of it as "replacing" rules without realizing the two API calls create a dangerous gap.

**How to avoid:**
Implement "add-first-then-delete" ordering: add the new rules, verify they exist, then delete the old rules. Even better: use a transactional pattern where you verify the add succeeded before proceeding to delete. If add fails, leave the old rules in place and log an error.

```
# Safe ordering:
1. Fetch existing rules
2. Add new rules (with new IP)
3. Verify new rules were created
4. Delete old rules (with old IP)
```

**Warning signs:**
- Rules are added and deleted in separate API calls with no verification between them.
- The code has `delete_rules()` followed by `add_rules()` with no intermediate check.
- Comments say "delete all, then add" or similar.

**Phase to address:**
Phase 1 (Critical fixes) -- this is the single most dangerous bug in the codebase. Must be fixed before any other work.

---

### Pitfall 2: Requests Without Timeout Cause Scheduler Hang

**What goes wrong:**
`requests.get()` in `ip_fetcher.py` line 22 has no `timeout` parameter. If the IP detection service (ipinfo.io) is unreachable, the request hangs indefinitely. APScheduler's `BlockingScheduler` runs jobs in a thread pool. With `max_instances=1` (the default), the hanging job blocks all future executions of the same job. The scheduler silently skips every subsequent check, and IP changes go undetected.

**Why it happens:**
Python's `requests` library defaults to no timeout. The documentation does not loudly warn about this. Developers test locally where ipinfo.io responds instantly, so the hang never manifests. The failure mode only appears in production on unreliable networks or when the IP service itself has an outage.

**How to avoid:**
Always set a tuple timeout `(connect_timeout, read_timeout)` on every `requests` call. For IP detection, `(3.05, 10)` is reasonable: 3 seconds to establish connection, 10 seconds to read the response. Apply the same timeout to cloud API calls. The `requests` docs explicitly recommend the tuple form to prevent DNS-resolution hangs being confused with slow responses.

```python
response = requests.get(url, timeout=(3.05, 10))
```

**Warning signs:**
- Any `requests.get()` or `requests.post()` call without a `timeout=` parameter.
- Log messages stop appearing but the process is still running.
- `ps aux` shows the process alive but no recent log entries.

**Phase to address:**
Phase 1 (Critical fixes) -- without timeouts, every other fix is moot because the scheduler hangs before it can execute them.

---

### Pitfall 3: No IP Validation Before Writing to Security Groups

**What goes wrong:**
`get_current_ip()` in `ip_fetcher.py` returns `response.text.strip()` without validating that it is a valid IP address. If the IP detection service returns an error page (HTML), a rate-limit message, or a malformed response, that raw text gets passed to security group rule creation. This creates invalid rules or, worse, deletes valid rules and replaces them with garbage.

**Why it happens:**
In development, ipinfo.io always returns a clean IP string. Developers assume the API contract holds. But rate-limited responses return JSON/HTML error pages, not IPs. The `response.status_code == 200` check catches HTTP errors but not malformed 200 responses.

**How to avoid:**
Validate the IP address using Python's `ipaddress.ip_address()` before using it. This catches both format errors and type mismatches (e.g., a URL or HTML snippet). Note: Python 3.9.5+ fixes CVE-2021-29921 (leading-zero octet bypass), so ensure Python >= 3.9.5.

```python
import ipaddress
def validate_ip(ip_str: str) -> str:
    ipaddress.ip_address(ip_str)  # raises ValueError if invalid
    return ip_str
```

Additionally: strip whitespace, reject empty strings, and log the raw response when validation fails for debugging.

**Warning signs:**
- Security group rules contain non-IP values (HTML fragments, JSON, "Unauthorized").
- The `get_current_ip` function does not call any validation on the response body.
- Log entries show IP values that look wrong (contain angle brackets, quotes, etc.).

**Phase to address:**
Phase 1 (Critical fixes) -- this directly protects security group integrity.

---

### Pitfall 4: Single Point of Failure in IP Detection

**What goes wrong:**
The tool relies exclusively on ipinfo.io for IP detection. When ipinfo.io's free tier is exhausted (monthly quota), the API returns a 429 rate-limit response. The current code raises an exception for non-200 status codes, which is caught at the top level and logged as a generic error. No IP check occurs until the quota resets. During this time, IP changes go undetected.

**Why it happens:**
Single-provider IP detection works perfectly during development and initial use. The rate limit only manifests after sustained use (typically 50,000 requests/month on ipinfo's free tier). At one check every 10 minutes, that is about 4,320 requests/month -- seemingly safe, but development restarts, testing, and multiple deployments can exhaust the quota faster than expected.

**How to avoid:**
Implement a fallback chain of IP detection providers. At minimum three providers with different rate limits and uptime characteristics. Shuffle the order periodically to distribute load.

Recommended provider chain:
1. **ipinfo.io/ip** -- primary (token-authenticated, higher rate limit)
2. **icanhazip.com** -- fallback (no auth needed, generous rate limit, Cloudflare-backed)
3. **api.ipify.org** -- secondary fallback (no auth, 1,000 requests/month free)
4. **checkip.amazonaws.com** -- tertiary (AWS-backed, very reliable)

For each provider: set a per-request timeout of 5 seconds, validate the response, and fall through to the next on failure.

**Warning signs:**
- Logs show repeated "IP获取失败" (IP fetch failed) messages.
- The same provider is used for every check with no fallback logic.
- Rate limit headers (`X-RateLimit-Remaining`) are never checked.

**Phase to address:**
Phase 1 (Critical fixes) -- IP detection is the foundation; without reliable detection, nothing else matters.

---

### Pitfall 5: get_rules() Returns None on Error, Causing Rule Accumulation

**What goes wrong:**
Both `huawei_cloud.py` and `tencent_cloud.py` catch exceptions in `get_rules()` and implicitly return `None`. The caller in `updater.py` checks `if existed_rules:` which is falsy for both `None` and `[]`. When `get_rules()` returns `None` (API failure), the code skips deletion and proceeds directly to adding new rules. Over time, rules accumulate because old rules are never cleaned up.

**Why it happens:**
Python functions return `None` by default when no explicit return is provided. The exception handler logs the error but falls through without returning. The caller uses truthiness checks that conflate `None` (error) with `[]` (no rules). This is a subtle but dangerous semantic difference.

**How to avoid:**
Two fixes needed:
1. `get_rules()` should **return an empty list `[]` on error**, not `None`. This distinguishes "no matching rules" from "API call failed."
2. Better yet, `get_rules()` should **re-raise exceptions** so the caller can decide whether to proceed. If we cannot read current rules, we should not modify them.

```python
def get_rules(self, group_id) -> List:
    try:
        # ... API call ...
        return filtered_rules
    except Exception as e:
        BaseCloudProvider.log(e)
        return []  # Return empty list, not None
```

**Warning signs:**
- Exception handlers in provider methods have no explicit return statement.
- Callers use truthiness (`if rules:`) instead of explicit checks.
- Security groups have many duplicate rules with different IPs.

**Phase to address:**
Phase 1 (Critical fixes) -- this bug silently degrades security posture over time.

---

## Technical Debt Patterns

Shortcuts that seem reasonable but create long-term problems.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Module-level config loading (import-time file I/O) | Simple access to `config` anywhere | Cannot import modules without `config.yaml` present; breaks testing, breaks packaging | Never -- use lazy loading or explicit init |
| `print()` instead of `logger` | Quick debugging output | Output lost in systemd (stdout goes to /dev/null); bypasses log rotation; no timestamps or severity | Only during active development, never in production code |
| Hardcoded check interval (180s) | No config complexity | Cannot adjust without code change and redeploy | MVP only -- make configurable immediately |
| Relative paths for `ip_cache.txt` and logs | Works in development | Fails under systemd where cwd is `/` or arbitrary | Never -- always use absolute paths derived from config or script location |
| `client = None` as class variable | Fewer lines in `__init__` | Shared state bug if multiple `Updater` instances exist | Never -- move to `__init__` |
| Exact version pinning (`pydantic==2.7.4`) | Reproducible builds | Security patches not picked up; dependency rot | Acceptable with periodic update discipline (monthly) |
| Catching bare `Exception` in `check_and_update_ip` | Prevents scheduler crash from any error | Config errors and programming bugs silently swallowed | Never -- catch specific exceptions and let programming errors crash loudly |

## Integration Gotchas

Common mistakes when connecting to external services.

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| **Huawei Cloud VPC API** | Using `batch_create_security_group_rules` without error handling | Wrap in try/except with `ClientRequestException`; add retry with exponential backoff |
| **Tencent Cloud VPC API** | Using `PolicyIndex` for deletion which can shift if rules change between get and delete | Fetch rules, identify by description + IP match, delete immediately in same operation |
| **ipinfo.io** | No timeout, no rate limit awareness, no fallback | Set timeout (3.05, 10), parse rate-limit headers, chain to fallback providers |
| **APScheduler** | Default `max_instances=1` with `BlockingScheduler` means one hanging job blocks all future jobs | Set `misfire_grace_time` to a generous value; set timeouts on all network calls so jobs cannot hang; consider `coalesce=True` |
| **systemd** | Not setting `WorkingDirectory` or using absolute paths for ExecStart | Always use absolute paths in unit file; set `WorkingDirectory=` explicitly; use `Environment=PYTHONUNBUFFERED=1` |
| **Cloud SDK clients** | Creating a new client object for every security group operation | Initialize client once per provider-region pair; reuse across operations within a check cycle |

## Performance Traps

Patterns that work at small scale but fail as usage grows.

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Sequential API calls to all cloud providers/regions | Single check cycle takes 10+ seconds if one API is slow | Current scale (2 providers, 4 regions) is tolerable; add timeout ceiling per API call (5s) | At 5+ providers or 10+ regions |
| Creating new SDK client per security group | Client initialization is expensive (auth, region lookup) | Initialize client once per provider-region, reuse for all security groups in that region | At 3+ security groups per region |
| Rule-by-rule deletion (Huawei Cloud) | One API call per rule to delete; O(n) API calls | Use batch operations where available; Huawei only supports single-delete, so minimize rules | At 10+ rules per security group |
| No cache TTL on IP detection | Every check cycle hits external API | Cache IP for the check interval; only call external API if cache is stale | Not a concern at current scale (10-min intervals) |

## Security Mistakes

Domain-specific security issues beyond general web security.

| Mistake | Risk | Prevention |
|---------|------|------------|
| **Logging API tokens in URLs** | ipinfo tokens written to log files; any log reader gets the token | Strip token from URL before logging; log `https://ipinfo.io/ip` not the full URL with token |
| **Plaintext cloud credentials in config.yaml** | Filesystem compromise gives full security group control | Use environment variables or OS keychain; at minimum, `chmod 600` on config.yaml |
| **Wildcard port range (1-65535)** | Undermines whitelist purpose; if IP update fails, all ports exposed to stale IP | Restrict to only needed ports; document if all-port access is intentional |
| **No IP validation before security group write** | Invalid response (HTML, error text) written as CIDR block; may create rules that match nothing or match everything | Validate with `ipaddress.ip_address()` before any cloud API call |
| **No rollback mechanism** | Bad update (wrong IP) requires manual console intervention | Store previous rule state; add rollback command or automatic revert on verification failure |
| **Description-based rule matching ("from Wulihe")** | Any rule with matching prefix is deleted; could delete manually-created rules | Use more specific description pattern including tool identifier and timestamp or unique ID |

## Operational Pitfalls

Mistakes specific to running as a long-lived systemd daemon.

### Pitfall 6: Relative Paths Break Under systemd

**What goes wrong:**
`ip_cache.txt` (relative path in `ip_fetcher.py` line 11) and `update_whitelist.log` (relative path in `logger.py` line 26) resolve relative to the current working directory. When systemd starts the service, the default cwd is `/` unless `WorkingDirectory` is explicitly set. The cache file and logs end up in `/ip_cache.txt` and `/update_whitelist.log`, or wherever systemd happens to set the working directory.

**Why it happens:**
Developers run the script from the project directory during testing, where relative paths resolve correctly. The systemd unit file may or may not set `WorkingDirectory`. This is one of the most common systemd deployment mistakes for Python services.

**How to avoid:**
Derive all file paths from an absolute base path. Use either:
1. An explicit base path from configuration or environment variable.
2. `pathlib.Path(__file__).parent.parent` to resolve relative to the script location.
3. System standard locations: `/var/lib/stay-in-whitelist/` for state, `/var/log/stay-in-whitelist/` for logs.

**Warning signs:**
- File paths in code are bare filenames without directory components.
- systemd unit file has no `WorkingDirectory=` directive.
- Cache or log files appear in unexpected locations (`/`, `/root/`, etc.).

**Phase to address:**
Phase 2 (Refactoring) -- part of the broader path handling cleanup.

---

### Pitfall 7: No Health Check or Silent Death Detection

**What goes wrong:**
If the scheduler process is alive but the check function is silently failing (hanging requests, caught exceptions, corrupted config), there is no external signal that the tool is not working. The user only discovers the failure when they get locked out of their cloud services.

**Why it happens:**
The `except Exception` catch in `check_and_update_ip()` (main.py line 55) swallows all errors. The process stays alive, systemd sees a healthy process, and the user assumes everything is fine. There is no heartbeat file, no health endpoint, no monitoring integration.

**How to avoid:**
1. Write a heartbeat timestamp to a file on every successful check cycle.
2. Use systemd's `WatchdogSec` with `sd_notify()` to signal liveness.
3. Catch specific exceptions instead of bare `Exception`; let programming errors crash the process so systemd can restart it.
4. Log clearly at ERROR level when an IP check cycle fails completely.

**Warning signs:**
- The process is running but no log entries appear for hours or days.
- `systemctl status` shows the service as "active (running)" but no recent log output.
- No heartbeat file exists, or its timestamp is stale.

**Phase to address:**
Phase 2 (Refactoring) -- add heartbeat mechanism alongside the other reliability improvements.

---

### Pitfall 8: APScheduler Misconfiguration Leads to Skipped Jobs

**What goes wrong:**
APScheduler's `BlockingScheduler` with default settings (`max_instances=1`, default `misfire_grace_time`) will silently skip scheduled jobs if the previous job is still running. Combined with Pitfall 2 (no timeout on requests), a single hanging HTTP request can cause all subsequent IP checks to be skipped indefinitely.

**Why it happens:**
APScheduler is designed to prevent job pile-up. If a job is still running when the next execution time arrives, it skips the new execution. This is a feature, not a bug -- but it becomes catastrophic when combined with unbounded network calls. The user sees the process running and assumes checks are happening, but they have been silently skipped.

**How to avoid:**
1. Fix the root cause: set timeouts on all network calls (Pitfall 2).
2. Set `misfire_grace_time` to a generous value (e.g., `None` to never skip, or at least 300 seconds).
3. Set `coalesce=True` to merge multiple missed runs into one execution.
4. Log a warning when misfires occur (APScheduler emits `EVENT_JOB_MISSED` events).
5. Ensure each check cycle completes well within the interval (10-minute interval, check cycle should complete in <30 seconds).

```python
scheduler.add_job(
    check_and_update_ip,
    'interval',
    seconds=600,
    misfire_grace_time=None,  # never skip
    coalesce=True,
)
```

**Warning signs:**
- Log shows "Execution of job skipped: maximum number of running instances exceeded" messages.
- Log shows "Run time of job was missed by" messages.
- IP cache file timestamp does not advance despite the process being alive.

**Phase to address:**
Phase 1 (Critical fixes) -- configure alongside timeout fixes.

---

## "Looks Done But Isn't" Checklist

Things that appear complete but are missing critical pieces.

- [ ] **IP detection:** Often missing response validation -- verify `ipaddress.ip_address()` is called before any cloud API use
- [ ] **Retry logic:** Often missing retry on the ADD step specifically -- verify `add_rules()` has retry, not just `get_rules()` and `delete_rules()`
- [ ] **Timeouts:** Often missing on cloud SDK calls, not just IP detection -- verify Huawei/Tencent SDK clients also have timeouts configured
- [ ] **Atomic updates:** "Add before delete" is not enough -- verify the add actually succeeded before deleting old rules
- [ ] **Logging:** Replacing `print()` with `logger` is not enough -- verify log files use absolute paths so they work under systemd
- [ ] **Config validation:** Pydantic validates types but not semantics -- verify security group IDs exist, ports are valid ranges, credentials are non-empty
- [ ] **systemd unit:** A unit file that starts the process is not enough -- verify it has `WorkingDirectory`, `Restart=on-failure`, `RestartSec`, and `WatchdogSec`
- [ ] **Error handling:** Catching exceptions is not enough -- verify errors in `add_rules()` (Huawei) actually have a try/except block
- [ ] **IP caching:** Writing the new IP to cache is not enough -- verify cache is written AFTER successful cloud API update, not before
- [ ] **Cache file:** Writing to a file is not enough -- verify the cache file uses an absolute path and has appropriate permissions (0600)

## Recovery Strategies

When pitfalls occur despite prevention, how to recover.

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Delete-before-add lockout | HIGH | Log into cloud console manually; add IP rule via web UI; fix code to add-before-delete; redeploy |
| Scheduler hang (no timeout) | LOW | `systemctl restart stay-in-whitelist`; fix timeout in code; redeploy |
| Invalid IP in security group | MEDIUM | Cloud console: delete invalid rule; add correct IP rule manually; fix validation in code |
| IP detection failure (single provider) | LOW | Service continues running; IP changes missed temporarily; add fallback providers in next deploy |
| Rule accumulation (get_rules returns None) | MEDIUM | Cloud console: audit and clean up duplicate rules; fix return value; redeploy |
| Relative path under systemd | LOW | Files are in wrong location but recoverable; fix to absolute paths; redeploy |
| Silent death (no health check) | HIGH | May go undetected for days; add heartbeat file; set up external monitoring of heartbeat |
| Rate limit on IP detection | LOW | Checks resume when quota resets; add fallback providers to prevent recurrence |
| Cloud API rate limit | LOW | Retry with backoff handles transient limits; permanent limits require adjusting check interval |

## Pitfall-to-Phase Mapping

How roadmap phases should address these pitfalls.

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Delete-before-add lockout | Phase 1: Critical Fixes | Write test that simulates add-rules failure and verifies old rules survive |
| Requests without timeout | Phase 1: Critical Fixes | Grep codebase for `requests.get(` without `timeout=`; verify none exist |
| No IP validation | Phase 1: Critical Fixes | Write test passing HTML/JSON/empty string to IP validation; verify rejection |
| Single IP provider | Phase 1: Critical Fixes | Simulate primary provider failure; verify fallback to secondary within 5s |
| get_rules() returns None | Phase 1: Critical Fixes | Write test for API failure in get_rules; verify it returns `[]` not `None` |
| APScheduler misconfiguration | Phase 1: Critical Fixes | Verify `misfire_grace_time` and `coalesce` are set in scheduler config |
| Relative paths under systemd | Phase 2: Refactoring | Verify all file paths are absolute; test by running from `/` as cwd |
| No health check | Phase 2: Refactoring | Verify heartbeat file is written on each cycle; verify timestamp is recent |
| print() instead of logger | Phase 2: Refactoring | Grep for `print(` in production code; verify all replaced with logger calls |
| Module-level side effects | Phase 2: Refactoring | Verify modules can be imported without `config.yaml` present |
| Cloud SDK client reuse | Phase 3: Hardening | Verify client is initialized once per provider-region, not per security group |
| Rate limit handling | Phase 3: Hardening | Verify exponential backoff is applied on 429 responses |
| No rollback mechanism | Phase 3: Hardening | Verify previous rule state is logged/stored before modification |
| Credential exposure in logs | Phase 3: Hardening | Grep log output for API tokens and keys; verify they are stripped |

## Sources

- [APScheduler User Guide (3.x)](https://apscheduler.readthedocs.io/en/3.x/userguide.html) -- max_instances, misfire_grace_time, coalesce configuration
- [APScheduler Migration Guide (v3 to v4)](https://apscheduler.readthedocs.io/en/master/migration.html) -- v3 is stable, v4 is alpha; stay on v3
- [APScheduler GitHub Issue #423](https://github.com/agronholm/apscheduler/issues/423) -- "Execution of job skipped" root cause analysis
- [APScheduler GitHub Issue #450](https://github.com/agronholm/apscheduler/issues/450) -- Process hanging when executed by APScheduler
- [Python requests hanging despite timeout (Reddit)](https://www.reddit.com/r/Python/comments/bfuboa/python_requests_hanging_requests_despite_setting/) -- Community reports of timeout not working as expected
- [Python requests timeout guide (ScrapingBee)](https://www.scrapingbee.com/blog/python-requests-timeout/) -- Best practice: use tuple `(connect, read)` timeout
- [systemd watchdog with Python (stigok.net)](https://blog.stigok.com/2020/01/26/sd-notify-systemd-watchdog-python-3.html) -- Python-specific sd_notify integration
- [systemd RestartSec and WatchdogSec guide (OneUptime)](https://oneuptime.com/blog/post/2026-03-02-configure-systemd-restartsec-watchdogsec-ubuntu/view) -- systemd reliability directives
- [Stack Overflow: systemd working directory](https://stackoverflow.com/questions/75217744/how-to-set-os-path-correctly-shows-a-different-path-when-ran-by-systemd-service) -- Relative paths fail under systemd
- [Huawei Cloud API rate limiting](https://support.huaweicloud.com/intl/en-us/api-astrozero/astrozero_api_0101.html) -- Exponential backoff recommendation
- [Huawei Cloud VPC security group limits](https://support.huaweicloud.com/intl/en-us/usermanual-vpc/en-us_topic_0073379079.html) -- 120 rules per security group, 500 total per account
- [Stack Overflow: Methods to detect public IP](https://stackoverflow.com/questions/14594151/methods-to-detect-a-public-ip-address-in-bash) -- Multiple fallback providers recommended
- [Baeldung: Get External IP in Shell Script](https://www.baeldung.com/linux/get-external-ip-shell-script) -- HTTP, DNS, and STUN methods compared
- [CVE-2021-29921 (NVD)](https://nvd.nist.gov/vuln/detail/cve-2021-29921) -- Python ipaddress validation bypass; fixed in 3.9.5
- [Codebase CONCERNS.md](file:///Users/abrahamgreyson/Code/stay-in-whitelist/.planning/codebase/CONCERNS.md) -- Known issues audit (2026-04-04)
- [Codebase PROJECT.md](file:///Users/abrahamgreyson/Code/stay-in-whitelist/.planning/PROJECT.md) -- Project context and active requirements

---
*Pitfalls research for: Dynamic IP whitelist updater (Stay in Whitelist)*
*Researched: 2026-04-04*
