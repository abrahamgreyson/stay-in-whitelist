# Feature Research

**Domain:** Dynamic IP whitelist/security group updater for cloud services
**Researched:** 2026-04-04
**Confidence:** HIGH

## Feature Landscape

### Table Stakes (Users Expect These)

Features users assume exist in a production IP whitelist updater. Missing these = tool is unreliable and gets abandoned.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Reliable IP detection with timeout | Network calls without timeout hang indefinitely; a hung `requests.get()` is the root cause of missed IP changes in the current codebase | LOW | Add `timeout=10` to every `requests.get()` call; trivial to implement but critical |
| Multi-provider IP detection fallback | Single provider (ipinfo.io) has free tier limits and downtime; when it fails, the tool silently stops working | MEDIUM | Implement a provider chain: ipinfo -> icanhazip.com -> api.ipify.org -> ifconfig.me. Try next on failure. Each returns plain text IP. |
| IP format validation | When an IP detection provider returns an error page or rate-limit message, the tool must not write garbage into security group rules | LOW | Validate response matches IPv4 regex `^\d{1,3}(\.\d{1,3}){3}$` before accepting. Reject anything else. |
| Configurable check interval | Users need to balance responsiveness against API call frequency. 3 minutes is aggressive; 10 minutes is safer. | LOW | Add `interval_seconds` to config, default 600. Pass to APScheduler. |
| Add-before-delete rule update order | Current delete-then-add sequence creates a window where no rule exists, locking the user out. The daniloaz.com reference script and Terraform's `create_before_destroy` lifecycle both use add-first as the standard pattern. | MEDIUM | Reverse the order: call `add_rules()` first, then `delete_rules()`. Must handle "rule already exists" errors from the cloud API (idempotent add). |
| Cloud API retry with exponential backoff | Cloud providers rate-limit and have transient failures. Without retry, a single failed API call means the security group is stale for another check interval. | MEDIUM | Implement retry decorator or utility: 3 retries with base delay 1s, 2s, 4s. Add jitter to avoid thundering herd. Apply to all cloud SDK calls. |
| All network requests have timeouts | Not just IP detection -- cloud SDK calls can also hang. Without timeouts, APScheduler `max_instances=1` silently skips subsequent checks. | LOW | Set timeout on all `requests` calls. For cloud SDKs, check if their client constructors accept timeout parameters (Huawei SDK does via `connect_timeout` / `read_timeout`). |
| File paths use absolute paths | systemd `WorkingDirectory` may not match project root. Relative `ip_cache.txt` and log files end up in unexpected locations. | LOW | Use `Path(__file__).parent` or a configurable base directory. Resolve all file paths to absolute at startup. |
| Structured logging (no print statements) | `print()` calls bypass the logging system, making it impossible to diagnose issues from log files. | LOW | Replace all `print()` with `logger.info()` / `logger.error()`. Current code has `print(rules)` in `fetch_security_group_rules()`. |
| No unhandled exceptions in cloud provider methods | `HuaweiCloud.add_rules()` has no try/except, meaning SDK exceptions propagate unhandled to the scheduler loop. | LOW | Add try/except to `add_rules()` matching the pattern in `get_rules()` and `delete_rules()`. Log and re-raise or return error status. |
| Rule description prefix for identification | The tool needs a way to identify which rules it manages vs. rules created by other tools/users. | LOW | Already partially implemented via "from Wulihe" prefix. Rename to project-neutral prefix (e.g., "from StayInWhitelist") during the project rename. |

### Differentiators (Competitive Advantage)

Features that set the tool apart from the typical "bash script + cron" approach. Not required, but valuable.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Multi-cloud support with provider abstraction | Most tools target a single cloud (AWS only, or Huawei only). Supporting Huawei Cloud + Tencent Cloud with a clean provider interface is a real differentiator for the Chinese cloud market. | Already implemented | The `BaseCloudProvider` ABC is a strength. Maintain it as new providers are added. |
| YAML config with Pydantic validation | Most competing tools use raw env vars or flat config files. Typed config with validation gives early error detection and self-documenting configuration. | Already implemented | Maintain. The `config.example.yaml` template is good practice. |
| Configurable check interval per environment | Different environments need different polling rates (home office vs. mobile). Making this a first-class config option is uncommon. | LOW | Add `check_interval` field to the Pydantic `Config` model. |
| IP change notification (webhook/log) | Knowing when the IP changed (and whether the update succeeded) is valuable for monitoring. Most tools are silent. | MEDIUM | Log the IP change event with old IP -> new IP. Optionally support a webhook URL in config for external notification. Start with logging only. |
| Rule cleanup on startup | If the tool was offline while IP changed, stale rules with the old IP remain in security groups. Detecting and cleaning up stale rules on startup is uncommon but valuable. | MEDIUM | On startup, compare cached IP with current IP. If different, update immediately rather than waiting for the next interval tick. Already partially handled by the cache-check logic. |
| Idempotent rule management | Ensuring that running the tool multiple times with the same IP does not create duplicate rules. | LOW | Before adding rules, check if rules with the current IP already exist. Skip add if already present. Reduces unnecessary API calls. |
| Health check / self-monitoring | The tool should detect if it is "stuck" (e.g., IP checks failing repeatedly) and log warnings. This is rare in competing tools. | MEDIUM | Track consecutive failure count. Log a warning after N consecutive failures. Could integrate with systemd `WatchdogSec` via `sd_notify("WATCHDOG=1")`. |
| Startup immediate check | Run the IP check immediately on startup rather than waiting for the first interval tick. Ensures the tool is working from second zero. | LOW | Call `check_and_update_ip()` once before starting the scheduler, or use APScheduler's `misfire_grace_time` with an immediate first run. |

### Anti-Features (Commonly Requested, Often Problematic)

Features that seem good but create problems for this specific tool's context.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Web UI / dashboard | "I want to see the current status" | Adds significant complexity (web framework, auth, hosting). This is a self-use daemon tool, not a SaaS product. The systemd journal and log files already provide status visibility. | Use structured logging + `journalctl -u stay-in-whitelist -f` for monitoring. |
| Real-time IP change detection (push-based) | "Polling every 10 minutes means up to 10 min of downtime" | ISPs do not provide push notifications for IP changes. The only way to detect IP change is polling. Sub-minute polling generates unnecessary API load. | Set check interval to 5-10 minutes. Most dynamic IPs change infrequently (daily at most). The daniloaz.com script uses cron every minute, which is aggressive but acceptable for single-user. |
| Multi-user / multi-tenant support | "What if my whole team needs it?" | Fundamentally changes the architecture (auth, per-user config, state management). Each user typically has their own cloud accounts and security groups. | Each user runs their own instance with their own config.yaml. The tool is lightweight enough for per-user deployment. |
| Database for state storage | "File-based cache is fragile" | Adds operational dependency (database server, connection management, migrations). For caching a single IP string, a file is the right tool. | Keep file-based IP cache. Use absolute paths and atomic writes (write to temp file, then rename). |
| Async / event-driven architecture | "APScheduler is old-school, use asyncio" | The workload is trivially small (one HTTP call + a few cloud API calls every 10 minutes). Async adds complexity with no benefit. The PROJECT.md explicitly scopes this out. | Keep linear execution with APScheduler. Add timeouts and retries for resilience. |
| Containerization / Docker deployment | "Deploy it in a container" | Adds an unnecessary operational layer for what is a single Python script running as a systemd service. The container would need network access to cloud APIs and file access for config. | Keep systemd deployment. It is simpler, uses fewer resources, and integrates with OS-level monitoring. |
| Support for all cloud providers (AWS, Azure, GCP, Alibaba) | "More cloud support is better" | Each provider requires SDK integration, testing, and maintenance. Adding providers nobody uses is wasted effort. The PROJECT.md scopes this to Huawei + Tencent only. | Maintain the provider abstraction for easy future addition. Only implement providers you actually use. Remove the dead Alibaba stub. |
| Secret management integration (HashiCorp Vault, etc.) | "Credentials in config.yaml are insecure" | This is a self-use tool running on a personal machine. The config file is gitignored. Adding Vault integration is massive over-engineering for the threat model. | Keep credentials in config.yaml + gitignore. File permissions (chmod 600) are sufficient for this use case. |

## Feature Dependencies

```
[IP format validation]
    └──requires──> [Multi-provider IP detection fallback]
                        └──requires──> [Reliable IP detection with timeout]

[Add-before-delete rule update]
    └──requires──> [All network requests have timeouts]
    └──requires──> [Cloud API retry with exponential backoff]

[Idempotent rule management]
    └──enhances──> [Add-before-delete rule update]

[Health check / self-monitoring]
    └──requires──> [Reliable IP detection with timeout]
    └──requires──> [All network requests have timeouts]

[Startup immediate check]
    └──requires──> [File paths use absolute paths]
    └──requires──> [Reliable IP detection with timeout]

[Rule description prefix for identification]
    └──required-by──> [Idempotent rule management]
    └──required-by──> [Rule cleanup on startup]

[Structured logging (no print statements)]
    └──required-by──> [Health check / self-monitoring]
    └──required-by──> [IP change notification]
```

### Dependency Notes

- **IP format validation requires multi-provider fallback**: Validation only matters if there are multiple providers that could return different (potentially malformed) responses. With a single provider, validation catches rate-limit pages but the fallback chain makes validation truly necessary.
- **Add-before-delete requires timeouts and retry**: Without timeouts, the "add" step could hang indefinitely, never reaching the "delete" step, leaving duplicate rules. Without retry, a transient failure on "add" means the old rules remain plus potentially partial new rules.
- **Idempotent rule management enhances add-before-delete**: If the add step is idempotent (skip if rule already exists), the add-before-delete sequence can be safely retried without creating duplicates.
- **Rule description prefix required by idempotent management**: To determine if a rule "already exists," you need to identify which rules belong to this tool. The description prefix is that identifier.
- **Structured logging required by health check**: The self-monitoring feature needs consistent, parseable log output to detect patterns like "N consecutive failures."

## MVP Definition

### Launch With (v1 -- Current Refactoring)

The minimum needed to make the existing tool production-reliable.

- [x] Multi-cloud support (Huawei + Tencent) -- already implemented
- [x] YAML config with Pydantic validation -- already implemented
- [x] Log rotation -- already implemented
- [ ] Reliable IP detection with timeout on ALL network requests -- fixes the primary bug
- [ ] Multi-provider IP detection fallback -- fixes the ipinfo rate-limit issue
- [ ] IP format validation -- prevents garbage in security groups
- [ ] Add-before-delete rule update order -- prevents lockout
- [ ] Cloud API retry with exponential backoff -- handles transient failures
- [ ] File paths use absolute paths -- fixes systemd deployment issue
- [ ] Structured logging (no print statements) -- diagnostic capability
- [ ] No unhandled exceptions in cloud provider methods -- resilience
- [ ] Configurable check interval -- operational flexibility
- [ ] Project rename to "Stay in Whitelist" -- identity alignment

### Add After Validation (v1.x)

Features to add once the core is reliable.

- [ ] Health check / self-monitoring (consecutive failure tracking) -- triggered by production observation
- [ ] Startup immediate check -- triggered by wanting faster recovery after restart
- [ ] Idempotent rule management -- triggered by observing duplicate rules in practice
- [ ] IP change notification via logging (old IP -> new IP, success/failure) -- triggered by wanting visibility
- [ ] systemd WatchdogSec integration -- triggered by wanting OS-level hang detection
- [ ] Rule cleanup on startup (detect stale rules from downtime) -- triggered by extended downtime scenarios

### Future Consideration (v2+)

Features to defer until there is a concrete need.

- [ ] Webhook notification support -- only if external alerting is needed
- [ ] Alibaba Cloud support -- only if user needs it
- [ ] AWS/Azure support -- only if user needs it
- [ ] IPv6 support -- only when cloud providers require it
- [ ] Configuration hot-reload (no restart needed) -- only if config changes frequently

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Reliable IP detection with timeout | HIGH | LOW | P1 |
| All network requests have timeouts | HIGH | LOW | P1 |
| IP format validation | HIGH | LOW | P1 |
| Multi-provider IP detection fallback | HIGH | MEDIUM | P1 |
| Add-before-delete rule update order | HIGH | MEDIUM | P1 |
| Cloud API retry with exponential backoff | HIGH | MEDIUM | P1 |
| File paths use absolute paths | HIGH | LOW | P1 |
| Structured logging (no print) | MEDIUM | LOW | P1 |
| Configurable check interval | MEDIUM | LOW | P1 |
| No unhandled exceptions in cloud methods | HIGH | LOW | P1 |
| Project rename | LOW | LOW | P1 |
| Rule description prefix update | LOW | LOW | P1 |
| Startup immediate check | MEDIUM | LOW | P2 |
| Health check / self-monitoring | MEDIUM | MEDIUM | P2 |
| Idempotent rule management | MEDIUM | LOW | P2 |
| IP change notification (logging) | LOW | LOW | P2 |
| systemd WatchdogSec integration | MEDIUM | MEDIUM | P2 |
| Rule cleanup on startup | LOW | MEDIUM | P2 |
| Webhook notification | LOW | MEDIUM | P3 |
| Additional cloud provider support | LOW | HIGH | P3 |

**Priority key:**
- P1: Must have for reliable operation -- addresses known bugs and operational failures
- P2: Should have, adds resilience -- addresses scenarios that will happen eventually
- P3: Nice to have, future consideration -- addresses hypothetical needs

## Competitor Feature Analysis

| Feature | aws-sg-updater | daniloaz bash script | aws-ipupdater | Stay in Whitelist (current) | Stay in Whitelist (target) |
|---------|----------------|---------------------|---------------|---------------------------|---------------------------|
| IP detection | ipinfo.io | dig + opendns | ifconfig.me | ipinfo.io only | Multi-provider fallback chain |
| Timeout on requests | Unknown (not documented) | N/A (dig command) | Unknown | NO (root cause of primary bug) | YES (all network calls) |
| IP format validation | Unknown | NO | Unknown | NO | YES (regex validation) |
| Multi-cloud support | AWS only | AWS only | AWS only | Huawei + Tencent | Huawei + Tencent |
| Config format | YAML rules file | Hardcoded in script | CLI args | YAML + Pydantic validation | YAML + Pydantic validation |
| Update order | Unknown | Delete then add | Unknown | Delete then add | Add then delete |
| Retry mechanism | NO | NO | NO | NO | YES (exponential backoff) |
| Scheduling | Cron | Cron | Manual | APScheduler (systemd) | APScheduler (systemd) |
| Multi-region | Via profiles | Hardcoded list | NO | YES (config-driven) | YES (config-driven) |
| Multi-SG per region | YES (rules.yml) | YES (iterates) | NO | YES (config-driven) | YES (config-driven) |
| State caching | ip.txt file | ~/.my_public_ip | NO | ip_cache.txt | ip_cache.txt (absolute path) |
| Logging | File logging | echo to stdout | Unknown | Rotating file + console | Rotating file + console |
| Error recovery | Unknown | Exit on error | Unknown | Catch-and-log (partially) | Catch-and-log + retry |

**Key insight:** The competitive landscape is dominated by simple, single-cloud bash scripts with no resilience features. Stay in Whitelist already differentiates with multi-cloud support and structured config. The primary gap is operational reliability (timeouts, retries, fallback), which no competitor handles well.

## Sources

- [aws-sg-updater](https://github.com/shugyosha89/aws-sg-updater) -- AWS-only Python tool, cron-based, YAML config, single provider
- [daniloaz.com: Auto-update AWS security groups](https://www.daniloaz.com/en/how-to-automatically-update-all-your-aws-ec2-security-groups-when-your-dynamic-ip-changes) -- Bash script reference, delete-then-add pattern, cron every minute, OpenDNS-based IP detection
- [aws-ipupdater](https://github.com/azumafuji/aws-ipupdater) -- Simple single-purpose AWS security group updater
- [IPSpot (multi-provider fallback library)](https://github.com/openscilab/ipspot) -- Reference implementation for multi-provider IP detection with fallback
- [Huawei Cloud API rate limiting docs](https://support.huaweicloud.com/intl/en-us/api-astrozero/astrozero_api_0101.html) -- Official guidance on exponential backoff for rate-limited APIs
- [AWS: Managing and Monitoring API Throttling](https://aws.amazon.com/blogs/mt/managing-monitoring-api-throttling-in-workloads/) -- Cloud API throttling management patterns
- [systemd WatchdogSec and RestartSec](https://oneuptime.com/blog/post/2026-03-02-configure-systemd-restartsec-watchdogsec-ubuntu/view) -- systemd service resilience configuration
- [Red Hat: Self-healing services with systemd](https://www.redhat.com/en/blog/systemd-automate-recovery) -- systemd restart policies and rate limiting
- [Writing a secure Systemd daemon with Python](https://blog.hqcodeshop.fi/archives/569-Writing-a-secure-Systemd-daemon-with-Python.html) -- Python systemd daemon best practices
- [IP Whitelisting Guide 2025 (StrongDM)](https://www.strongdm.com/blog/ip-whitelisting) -- Modern IP whitelisting approaches and alternatives
- Project source code analysis (main.py, ip_fetcher.py, updater.py, config.example.yaml) -- Current implementation and identified gaps

---
*Feature research for: Dynamic IP whitelist updater (Stay in Whitelist)*
*Researched: 2026-04-04*
