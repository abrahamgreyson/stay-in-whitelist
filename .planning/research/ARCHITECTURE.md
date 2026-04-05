# Architecture Research

**Domain:** Resilient Python daemon for cloud security group whitelist management
**Researched:** 2026-04-04
**Confidence:** HIGH

## Standard Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Process Lifecycle                            │
├─────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌──────────────────┐  ┌───────────────────┐   │
│  │ systemd Service  │  │  Watchdog (sd_   │  │  Signal Handler   │   │
│  │  (Type=notify)  │  │  notify protocol)│  │  (SIGTERM/SIGINT) │   │
│  └────────┬────────┘  └────────┬─────────┘  └─────────┬─────────┘   │
│           │                    │                       │             │
├───────────┴────────────────────┴───────────────────────┴─────────────┤
│                     Scheduler / Entry Layer                         │
├─────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │              APScheduler (BlockingScheduler)                │    │
│  │  interval=600s, misfire_grace_time=300, coalesce=True,      │    │
│  │  max_instances=1                                             │    │
│  └──────────────────────────┬──────────────────────────────────┘    │
│                             │ tick                                  │
├─────────────────────────────┴───────────────────────────────────────┤
│                       Core Orchestration                            │
├─────────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐   ┌───────────────────┐   ┌──────────────────┐   │
│  │ IP Detection │   │   IP Validation   │   │  Update Planner  │   │
│  │  (multi-     │──>│  (regex guard)    │──>│  (add-before-    │   │
│  │   provider)  │   │                   │   │   delete order)  │   │
│  └──────┬───────┘   └───────────────────┘   └────────┬─────────┘   │
│         │                                             │             │
│  ┌──────┴───────┐                                     │             │
│  │  IP Cache    │                                     │             │
│  │ (file-based) │                                     │             │
│  └──────────────┘                                     │             │
├───────────────────────────────────────────────────────┴─────────────┤
│                    Cloud Provider Layer                             │
├─────────────────────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │              Retry Wrapper (Tenacity)                         │   │
│  │  stop=stop_after_attempt(3), wait=wait_exponential(min=4,   │   │
│  │  max=30), retry=retry_if_exception_type(...)                 │   │
│  └───────────┬──────────────────────────┬───────────────────────┘   │
│              │                          │                           │
│  ┌───────────┴──────────┐   ┌───────────┴──────────────┐            │
│  │   HuaweiCloud        │   │   TencentCloud            │            │
│  │  (Strategy pattern)  │   │   (Strategy pattern)      │            │
│  └──────────────────────┘   └──────────────────────────┘            │
├─────────────────────────────────────────────────────────────────────┤
│                      Supporting Services                            │
├─────────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌───────────────┐  ┌────────────────────────┐   │
│  │  Config      │  │  Logging      │  │  Paths (absolute,      │   │
│  │  (Pydantic)  │  │  (rotating)   │  │   systemd-compatible)  │   │
│  └──────────────┘  └───────────────┘  └────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Implementation |
|-----------|----------------|----------------|
| **systemd Service** | Process lifecycle, auto-restart, health monitoring | `Type=notify`, `WatchdogSec=600`, `Restart=on-failure` |
| **Watchdog** | Signal process health to systemd | `sdnotify` pip package, send `WATCHDOG=1` after each successful check cycle |
| **Signal Handler** | Graceful shutdown on SIGTERM/SIGINT | Python `signal` module, stop scheduler cleanly |
| **APScheduler** | Periodic IP check invocation | `BlockingScheduler`, 600s interval, `misfire_grace_time=300`, `coalesce=True`, `max_instances=1` |
| **IP Detection** | Fetch current public IP with fallback chain | Iterate providers: ipinfo.io -> ipify.org -> icanhazip.com. Each with 10s timeout |
| **IP Validation** | Guard against malformed responses | Regex check `r'^\d{1,3}(\.\d{1,3}){3}$'` before accepting IP |
| **IP Cache** | Persist last known IP across restarts | File-based `ip_cache.txt`, absolute path resolved at startup |
| **Update Planner** | Orchestrate rule updates in safe order | Add new rules first, verify success, then delete old rules |
| **Retry Wrapper** | Resilient cloud API calls with backoff | Tenacity: 3 attempts, exponential backoff 4-30s, retry on SDK exceptions |
| **HuaweiCloud** | Huawei VPC security group CRUD | SDK calls through retry wrapper, filter by description prefix |
| **TencentCloud** | Tencent VPC security group CRUD | SDK calls through retry wrapper, filter by description prefix |
| **Config** | Typed config with validation | Pydantic v2 models from YAML, lazy-loaded (not module-level side effect) |
| **Logging** | Structured logs with rotation | `TimedRotatingFileHandler`, absolute path, 24h rotation, 7 backups |
| **Paths** | Absolute path resolution for systemd | Compute base dir from config file location or CLI arg, never use CWD |

## Recommended Project Structure

```
stay_in_whitelist/
├── __init__.py
├── __main__.py               # `python -m stay_in_whitelist` entry point
├── main.py                   # Scheduler setup, signal handling, watchdog
├── config/
│   ├── __init__.py
│   └── models.py             # Pydantic models + config loading function
├── ip_detection/
│   ├── __init__.py
│   ├── detector.py           # Multi-provider IP fetch with fallback
│   ├── validators.py         # IP format validation
│   └── cache.py              # File-based IP cache (absolute paths)
├── cloud_providers/
│   ├── __init__.py
│   ├── base.py               # BaseCloudProvider ABC
│   ├── retry.py              # Tenacity retry decorator / wrapper
│   ├── huawei.py             # HuaweiCloud implementation
│   └── tencent.py            # TencentCloud implementation
├── updater.py                # Orchestration: safe rule update (add-before-delete)
├── paths.py                  # Absolute path resolution utility
└── logging_config.py         # Logger factory with absolute paths
```

### Structure Rationale

- **`ip_detection/` package:** Encapsulates all IP fetching complexity (multi-provider fallback, validation, caching) into a single cohesive unit. This is the component with the most behavioral change from the refactor (single provider -> multi-provider with fallback), so isolating it makes the diff clean.
- **`cloud_providers/retry.py`:** Extracted retry logic so both Huawei and Tencent providers share one retry configuration. Changing retry strategy is a single-file edit.
- **`config/models.py`** (renamed from `config.py`): Removes the module-level singleton side effect. Config loading becomes an explicit function call in `main.py`, making tests easier and avoiding import-order bugs.
- **`paths.py`:** Centralizes absolute path computation. Every file path (cache, log, config) goes through this module. Eliminates the systemd working directory ambiguity that causes production failures.
- **`__main__.py`:** Enables `python -m stay_in_whitelist` invocation, which is cleaner for systemd than pointing at a specific `.py` file.

## Architectural Patterns

### Pattern 1: Strategy Pattern for Cloud Providers

**What:** Abstract base class defines a uniform interface (`get_rules`, `add_rules`, `delete_rules`). Each cloud vendor implements the interface using their SDK.
**When to use:** When supporting multiple cloud vendors with the same logical operations but different SDKs and APIs.
**Trade-offs:** Clean separation but requires a disciplined dispatch mechanism. The current code uses string-based `if/elif` in `set_client()` -- acceptable for 2-3 providers, but a registry pattern is cleaner.

```python
class BaseCloudProvider(ABC):
    @abstractmethod
    def get_rules(self, group_id: str) -> list:
        ...

    @abstractmethod
    def add_rules(self, group_id: str, rules: list, ip: str) -> None:
        ...

    @abstractmethod
    def delete_rules(self, group_id: str, rules: list) -> None:
        ...

# Registry instead of if/elif
PROVIDERS: dict[str, type[BaseCloudProvider]] = {
    "huawei": HuaweiCloud,
    "tencent": TencentCloud,
}

def create_provider(name: str, **kwargs) -> BaseCloudProvider:
    return PROVIDERS[name](**kwargs)
```

### Pattern 2: Fallback Chain for IP Detection

**What:** Try multiple IP detection services in priority order. If the first fails (timeout, error, invalid response), try the next. Return the first valid result or raise after all exhausted.
**When to use:** When relying on a single external service creates a single point of failure.
**Trade-offs:** Adds a small amount of latency on fallback (each failed attempt costs up to `timeout` seconds). Protects against provider outages and rate limits.

```python
PROVIDERS = [
    ("ipinfo.io", lambda token: f"https://ipinfo.io/ip?token={token}"),
    ("ipify", lambda _: "https://api.ipify.org"),
    ("icanhazip", lambda _: "https://icanhazip.com"),
]

def get_current_ip(tokens: list[str], timeout: int = 10) -> str:
    for name, url_fn in PROVIDERS:
        try:
            url = url_fn(tokens[0]) if name == "ipinfo.io" else url_fn(None)
            resp = requests.get(url, timeout=timeout)
            resp.raise_for_status()
            ip = resp.text.strip()
            if is_valid_ipv4(ip):
                return ip
        except Exception:
            continue
    raise RuntimeError("All IP detection providers failed")
```

### Pattern 3: Create-Before-Destroy for Security Rules

**What:** When updating security group rules, add new rules first, verify they exist, then delete old rules. This is the same pattern as Terraform's `create_before_destroy` lifecycle.
**When to use:** Any security-critical state mutation where partial failure could lock out access.
**Trade-offs:** Temporarily has both old and new rules active (brief double-entry window). This is acceptable for IP whitelisting -- having both IPs allowed for a few seconds is not a security concern. The alternative (delete-first) risks permanent lockout if the add operation fails.

```python
def update_security_group_rules(self, sg_id, allows, new_ip, description_prefix):
    existing = self.client.get_rules(sg_id)  # Step 1: read current state
    self.client.add_rules(sg_id, allows, new_ip)  # Step 2: ADD new rules
    # Step 3: Verify new rules exist (optional but recommended)
    # Step 4: Delete only the OLD rules, not the ones just created
    old_rules = [r for r in existing if r.ip != new_ip]
    if old_rules:
        self.client.delete_rules(sg_id, old_rules)
```

### Pattern 4: Retry with Exponential Backoff (Tenacity)

**What:** Wrap cloud SDK calls in a retry decorator that catches transient failures (rate limits, network errors) and retries with increasing delays.
**When to use:** All external API calls that can fail due to transient conditions. Do NOT retry on authentication failures or validation errors.
**Trade-offs:** Adds library dependency (`tenacity`). For a project this size, the alternative is hand-rolled retry logic which is error-prone and harder to test. Tenacity is the standard choice in the Python ecosystem.

```python
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

cloud_retry = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=30),
    retry=retry_if_exception_type((ConnectionError, TimeoutError)),
    before_sleep=lambda retry_state: logger.warning(
        f"Cloud API call failed (attempt {retry_state.attempt_number}), retrying..."
    ),
)

@cloud_retry
def add_rules(self, group_id, rules, ip):
    ...
```

### Pattern 5: systemd Watchdog Integration

**What:** The daemon periodically sends `WATCHDOG=1` to systemd via the `sd_notify` protocol. If systemd stops receiving these within `WatchdogSec`, it restarts the service.
**When to use:** Any long-running systemd service where silent hangs are unacceptable.
**Trade-offs:** Adds `sdnotify` pip dependency (pure Python, no native deps). Requires `Type=notify` in the service file. Watchdog interval must be longer than the longest expected check cycle.

```python
import sdnotify

def check_and_update_ip():
    try:
        # ... existing logic ...
        n = sdnotify.SystemdNotifier()
        n.notify("WATCHDOG=1")
        n.notify("STATUS=Last check completed successfully")
    except Exception as e:
        n.notify(f"STATUS=Error: {e}")
        logger.error(f"Check cycle failed: {e}")
```

### Pattern 6: Lazy Configuration Loading

**What:** Load configuration via an explicit function call in `main()`, not as a module-level side effect. Pass the config object explicitly to components that need it.
**When to use:** Always, unless the project is a trivial script. Module-level side effects make testing painful and introduce import-order dependencies.
**Trade-offs:** Requires passing config through function arguments. Slightly more verbose but far more testable and predictable.

```python
# config/models.py
def load_config(config_path: str) -> Config:
    with open(config_path, 'r') as f:
        data = yaml.safe_load(f)
    return Config(**data)

# main.py
def main():
    config_path = resolve_config_path()
    config = load_config(config_path)
    scheduler = setup_scheduler(config.check_interval)
    # ...
```

## Data Flow

### IP Update Cycle (every 600 seconds)

```
APScheduler tick
    │
    ▼
check_and_update_ip()
    │
    ├──> IP Detection (multi-provider fallback chain)
    │         │
    │         ├── ipinfo.io (primary, with token) ──timeout 10s──> IP or fail
    │         ├── ipify.org (fallback 1)           ──timeout 10s──> IP or fail
    │         └── icanhazip.com (fallback 2)       ──timeout 10s──> IP or fail
    │         │
    │         ▼
    │     IP Validation (regex: valid IPv4?)
    │         │
    │         ├── Invalid ──> log error, return (skip this cycle)
    │         └── Valid ─────┐
    │                        │
    ├──> IP Cache (compare with ip_cache.txt)
    │         │
    │         ├── Same IP ──> log "no change", send WATCHDOG=1, return
    │         └── Changed ──> cache new IP to file
    │                        │
    ▼                        ▼
Update Planner (iterate config: provider -> region -> security group)
    │
    ├──> For each security group:
    │         │
    │         ├── Fetch existing rules (with retry) ──> list of rules
    │         ├── Add NEW rules (with retry)          ──> new rules created
    │         └── Delete OLD rules (with retry)       ──> stale rules removed
    │
    ▼
Watchdog notify (WATCHDOG=1 + STATUS message)
```

### State Management

```
config.yaml ──(load once at startup)──> Config object (immutable in memory)
                                           │
                                           ▼
ip_cache.txt ──(read each cycle)──> Compare ──(write on change)──> ip_cache.txt
                                           │
                                           ▼
                                    Cloud Security Groups
                                    (external state, mutated via API)
```

### Key Data Flows

1. **Configuration Flow:** `config.yaml` -> `load_config()` -> `Config` Pydantic model -> passed to components. Loaded once at startup, never hot-reloaded.
2. **IP Detection Flow:** Provider chain (ipinfo -> ipify -> icanhazip) -> validation -> cache comparison. Each provider has a 10-second timeout. First valid result wins.
3. **Security Group Update Flow:** Read existing rules -> add new rules -> verify success -> delete old rules. This order prevents lockout on partial failure.
4. **Health Reporting Flow:** Each successful check cycle sends `WATCHDOG=1` to systemd. Each failure updates `STATUS=` with error details. systemd restarts the service if watchdog signals stop.
5. **Logging Flow:** All components use `get_logger(name)`. Logs go to console (stdout for `journalctl`) and rotating file (absolute path). Log level configurable.

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| 1-3 cloud providers, 1-10 security groups | Current architecture is optimal. Linear execution is correct. No changes needed. |
| 5+ cloud providers, 10+ security groups | Consider batching rule operations per provider (reduce API calls). Still linear but group operations. |
| Multi-machine deployment | Out of scope per PROJECT.md. Would need distributed locking and shared state. |

### Scaling Priorities

1. **First bottleneck:** IP detection provider rate limits. Mitigated by multi-provider fallback and 600-second intervals.
2. **Second bottleneck:** Cloud API rate limits. Mitigated by exponential backoff retry. If this becomes chronic, batch multiple security group updates into fewer API calls per provider.

**This project does not need scaling architecture.** It is a single-machine daemon managing a handful of rules. The complexity budget should go into reliability, not throughput.

## Anti-Patterns

### Anti-Pattern 1: Module-Level Side Effects for Config

**What people do:** Load config at module import time (e.g., `config = Config(**yaml.safe_load(...))` at module level).
**Why it is wrong:** (a) Importing the module for testing triggers config loading from filesystem. (b) Import order matters -- if module A imports config and module B imports module A, config loads before B can override paths. (c) Cannot test with different configs without filesystem tricks.
**Do this instead:** Provide a `load_config(path)` function. Call it explicitly in `main()`. Pass the config object to components.

### Anti-Pattern 2: Delete-Before-Add Rule Updates

**What people do:** Delete existing security group rules first, then add new ones.
**Why it is wrong:** If the add operation fails (network error, API rate limit, SDK exception), the security group is empty. The user is locked out of their own infrastructure with no automated recovery path.
**Do this instead:** Add new rules first. Verify they exist. Then delete old rules. The brief overlap period (both old and new IPs allowed) is harmless for IP whitelisting.

### Anti-Pattern 3: No Timeout on External Requests

**What people do:** Call `requests.get(url)` without a `timeout` parameter.
**Why it is wrong:** The request can hang indefinitely. With APScheduler's `max_instances=1`, a hung request blocks all subsequent scheduled checks. The daemon silently stops updating.
**Do this instead:** Every `requests.get()` and cloud SDK call must have a timeout. For HTTP: 10 seconds. For cloud SDK: use the SDK's built-in timeout configuration or wrap in `threading.Timer` / `signal.alarm`.

### Anti-Pattern 4: Relative Paths for Runtime Files

**What people do:** Open files like `open('ip_cache.txt')` or `TimedRotatingFileHandler('update_whitelist.log')`.
**Why it is wrong:** systemd's `WorkingDirectory` may not match the project directory. The cache file gets written to an unexpected location, or fails silently. On next restart, the cache is "lost" and the daemon does a full update cycle.
**Do this instead:** Resolve all file paths absolutely at startup. Compute a base directory from the config file location or a CLI argument. Pass absolute paths to file handlers.

### Anti-Pattern 5: Swallowing Errors as None

**What people do:** Catch exceptions and return `None`, then callers check `if result:` to decide behavior.
**Why it is wrong:** The current code's `fetch_security_group_rules()` returns `None` on error, and the caller treats `None` as "no existing rules" -- causing rule accumulation (new rules added without old ones deleted).
**Do this instead:** Raise exceptions for actual failures. Return empty list `[]` for "no rules found" (which is a valid state). Distinguish "nothing there" from "something went wrong."

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| ipinfo.io | HTTP GET with token, 10s timeout | Primary IP detection. Free tier has monthly limits. |
| ipify.org | HTTP GET, 10s timeout | Fallback IP detection. No token needed. Reliable. |
| icanhazip.com | HTTP GET, 10s timeout | Fallback IP detection. Run by Cloudflare. |
| ifconfig.me | HTTP GET, 10s timeout | Additional fallback. Can be slow. |
| Huawei Cloud VPC API | SDK (`huaweicloudsdkcore` + `huaweicloudsdkvpc`), retry wrapper | Filter rules by description prefix. SDK has its own connection management. |
| Tencent Cloud VPC API | SDK (`tencentcloud-sdk-python-vpc`), retry wrapper | Filter rules by description prefix. SDK has its own connection management. |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| main.py <-> Scheduler | Function callback (APScheduler invokes `check_and_update_ip`) | Scheduler owns the thread. Callback must not raise. |
| main.py <-> Config | Function argument (config passed explicitly) | Config loaded once, treated as immutable. |
| IP Detection <-> Config | Config passed to detector (provider tokens) | Detector reads token list from config. |
| Updater <-> Cloud Providers | Method calls on provider instances | Provider instantiated per region. Updater orchestrates add-before-delete. |
| Cloud Providers <-> Retry | Decorator pattern (Tenacity) | Retry logic is transparent to provider implementation. |
| All Components <-> Logger | `get_logger(name)` factory | Each module gets its own named logger. Shared handlers. |
| All Components <-> Paths | `paths.py` utility module | All file paths resolved through this module. |

## Build Order Implications

The component dependencies suggest this build order for the roadmap:

```
Phase 1: Foundation (no behavioral changes, enables everything else)
  ├── paths.py (absolute path resolution)
  ├── config refactor (lazy loading, remove module-level singleton)
  └── logging fix (absolute paths for log file)

Phase 2: IP Detection Hardening (fix the root cause of missed updates)
  ├── ip_detection/validators.py (IP format validation)
  ├── ip_detection/detector.py (multi-provider fallback)
  ├── ip_detection/cache.py (absolute paths for cache file)
  └── timeout on all HTTP requests

Phase 3: Cloud API Resilience (fix lockout risk and transient failures)
  ├── cloud_providers/retry.py (Tenacity wrapper)
  ├── updater.py refactor (add-before-delete order)
  ├── Fix fetch_security_group_rules error handling
  └── Add exception handling to HuaweiCloud.add_rules

Phase 4: Daemon Integration (systemd hardening)
  ├── sdnotify watchdog integration
  ├── Signal handling for graceful shutdown
  ├── Configurable check interval (600s default)
  └── systemd service file update (Type=notify, WatchdogSec)

Phase 5: Rename and Cleanup
  ├── Package rename to stay_in_whitelist
  ├── Replace print() with logger
  ├── Remove dead code (config_loader.py, aliyun stub)
  └── Update all description prefixes and comments
```

**Rationale for this order:**
- Phase 1 first because absolute paths and lazy config are prerequisites for correct systemd behavior. Every subsequent phase depends on these.
- Phase 2 second because it fixes the primary user-visible bug (missed IP changes). The multi-provider fallback and timeout fixes are the core reliability improvement.
- Phase 3 third because it fixes the secondary critical bug (lockout risk). The add-before-delete pattern is the most architecturally significant change to the updater.
- Phase 4 fourth because systemd watchdog is only useful once the core logic is reliable. Adding watchdog to a flaky daemon just causes unnecessary restarts.
- Phase 5 last because rename and cleanup are cosmetic. They do not affect reliability and can be done in a single pass without behavioral risk.

## Sources

- APScheduler 3.x documentation: `misfire_grace_time`, `coalesce`, `max_instances` configuration -- HIGH confidence (official docs)
- Tenacity library: standard Python retry with `stop_after_attempt`, `wait_exponential`, `retry_if_exception_type` -- HIGH confidence (Context7 + PyPI)
- `sdnotify` pip package: pure Python systemd notify protocol implementation -- HIGH confidence (PyPI + GitHub)
- systemd `Type=notify` + `WatchdogSec`: standard daemon watchdog mechanism -- HIGH confidence (systemd official docs)
- Terraform `create_before_destroy` lifecycle pattern: inspiration for add-before-delete security group updates -- HIGH confidence (HashiCorp docs)
- Multi-provider IP detection fallback: common pattern in dynamic DNS clients and cloud tooling -- HIGH confidence (multiple open-source implementations)
- `requests.get()` timeout parameter: prevents indefinite hangs -- HIGH confidence (requests official docs)

---
*Architecture research for: resilient Python daemon for cloud security group management*
*Researched: 2026-04-04*
