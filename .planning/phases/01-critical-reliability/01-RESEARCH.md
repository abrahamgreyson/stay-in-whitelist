# Phase 1: Critical Reliability - Research

**Researched:** 2026-04-05
**Domain:** Network resilience, retry patterns, safe update ordering, IP validation
**Confidence:** HIGH

## Summary

Phase 1 addresses five core defects that can cause the daemon to hang indefinitely, lock users out of their services, or write garbage data to security group rules. The current codebase has no request timeouts, a single IP detection provider with no fallback, no IP validation before cloud API calls, no retry logic on transient failures, a dangerous delete-before-add rule update order, and missing error handling in `huawei_cloud.add_rules()`.

The existing architecture uses `requests` for HTTP, APScheduler for periodic scheduling, and a Strategy pattern for cloud providers (`BaseCloudProvider` ABC with `HuaweiCloud` and `TencentCloud` implementations). The plan needs to work within this linear, synchronous architecture -- no async or threading needed.

**Primary recommendation:** Add timeouts to all network calls using `requests` tuple syntax, implement a sequential fallback chain for IP detection using stdlib only, add `tenacity~=9.0.0` for retry on cloud API calls with exponential backoff, reverse the rule update order to add-before-delete, and wrap `huawei_cloud.add_rules()` in try/except consistent with other methods.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** IP detection and cloud API requests both need connect timeout and read timeout, configured separately
- **D-02:** Defaults: IP detection connect=3s/read=5s, cloud API connect=3s/read=10s
- **D-03:** Timeout values overridable in config.yaml, but 99% of users won't need to change them
- **D-04:** Use requests timeout tuple parameter `(connect_timeout, read_timeout)`
- **D-05:** Sequential fallback chain: ipinfo -> icanhazip -> ipify -> ifconfig.me, stop at first success
- **D-06:** ipinfo first (preserves existing token config), fallback to free providers requiring no token
- **D-07:** Each provider has independent timeout, single failure doesn't affect remaining provider time budget
- **D-08:** All providers fail -> log error, skip this check cycle (no whitelist update), retry next scheduler tick
- **D-09:** Use tenacity library for retry, 3 retries + exponential backoff (initial 1s, doubling)
- **D-10:** Only retry network errors (requests.exceptions.ConnectionError, Timeout) and 5xx server errors
- **D-11:** 4xx client errors (config errors, auth failures) not retried, fail immediately with log
- **D-12:** Retry applied to all cloud API calls: get_rules, add_rules, delete_rules
- **D-13:** Security group rule update order: add_rules (new) first -> delete_rules (old) second
- **D-14:** No verify step after add (extra API call complexity not worth it, API success = rule active)
- **D-15:** get_rules() returns empty list [] on error instead of None
- **D-16:** huawei_cloud.add_rules() must be wrapped in try/except, consistent with delete_rules error handling
- **D-17:** Phase 1 unit tests must mock cloud API calls, must NOT touch production security groups
- **D-18:** Development/debugging must use different rule prefix (e.g. "from Wulihe-dev") for isolation
- **D-19:** Configurable rule prefix (IDENT-06) belongs to Phase 4, but Phase 1 tests must observe this isolation

### Claude's Discretion
- IP detection provider specific URL formats and response parsing
- tenacity decorator specific parameter configuration (stop_after_attempt, wait_exponential)
- config.yaml timeout field naming and structure
- IP validation failure specific log format

### Deferred Ideas (OUT OF SCOPE)
- Configurable rule prefix (IDENT-06) -- belongs to Phase 4, but Phase 1 tests must note isolation
- Health check / heartbeat mechanism -- v2 requirement
- Idempotent rule management (skip existing rules) -- v2 requirement
- IP change notification (webhook/email) -- v2 requirement
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| REL-01 | All network requests have configurable timeouts | requests tuple timeout syntax `(connect, read)` verified; default values decided (D-02); config extension pattern via Pydantic BaseModel |
| REL-02 | Multi-provider IP detection with fallback chain | Fallback providers verified (icanhazip, ipify, ifconfig.me all return plain text IP); no token needed for fallback providers; response format documented |
| REL-03 | IP format validation using `ipaddress.ip_address()` | Python stdlib `ipaddress` available since 3.3; `ip_address()` raises `ValueError` for invalid input; handles both IPv4 and IPv6 |
| REL-04 | Cloud API retry with exponential backoff (tenacity) | tenacity 9.0.0 confirmed compatible with Python 3.9+; `retry_if_exception_type` for selective retry; `wait_exponential` for backoff; decorator and `Retrying` object patterns documented |
| REL-05 | Add-before-delete rule update order | Current code at `updater.py:46-63` does delete-then-add; reversal is straightforward line reorder; no verify step needed per D-14 |
| REL-06 | `get_rules()` returns `[]` on error instead of `None` | Both `huawei_cloud.py:82` and `tencent_cloud.py:33` implicitly return `None` on exception; change to explicit `return []`; caller logic at `updater.py:53` needs adjustment |
| REL-07 | `huawei_cloud.add_rules()` wrapped in try/except | `huawei_cloud.py:33-50` has no error handling; pattern already exists in `delete_rules()` (line 29-30) and `get_rules()` (line 81-82) to follow |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| tenacity | ~=9.0.0 | Retry with exponential backoff for cloud API calls | Decided in D-09; Python 3.9+ compatible; Apache 2.0; widely used (264M+ monthly downloads on PyPI) |
| requests | ~=2.32.3 | HTTP client for IP detection | Already in project; tuple timeout `(connect, read)` natively supported |
| ipaddress | stdlib | IP address validation | Part of Python stdlib since 3.3; no dependency needed; decided in REL-03 |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pydantic | ~=2.7.4 | Extend Config model for timeout settings | Adding optional timeout fields to existing Config hierarchy |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| tenacity | Manual retry loop | tenacity is cleaner, well-tested, handles edge cases (jitter, stop conditions); manual loop adds boilerplate and subtle bugs |
| tenacity | backoff library | tenacity has more features, larger community; both are valid but tenacity was decided in D-09 |
| tenacity 9.0.0 | tenacity 8.5.0 | 9.0.0 is last version supporting Python 3.8+; 8.5.0 also works but 9.0.0 has cleaner API and is newer |
| tenacity 9.1.x | tenacity 9.0.0 | 9.1.x drops Python 3.9 support -- incompatible with project constraint Python 3.9+ |

**Installation:**
```bash
pip install "tenacity~=9.0.0"
```

Add to `pyproject.toml` dependencies:
```toml
"tenacity~=9.0.0",
```

**Version verification:**
- tenacity latest: 9.1.4 (but drops Python 3.9 support)
- tenacity 9.0.0: last version compatible with Python 3.9+, released 2024-07-29
- requests latest: 2.33.1 (project pins ~=2.32.3)

## Architecture Patterns

### Recommended Project Structure
Changes are localized to existing files -- no new files or directories needed for Phase 1.

```
update_whitelist/
  ip_fetcher.py           -- REFACTOR: multi-provider fallback chain + timeout + IP validation
  updater.py              -- MODIFY: reverse rule update order (add-before-delete)
  config/config.py        -- EXTEND: add timeout configuration to Pydantic models
  cloud_providers/
    base_cloud_provider.py  -- EXTEND: retry decorator on abstract methods
    huawei_cloud.py         -- FIX: add try/except to add_rules; return [] from get_rules
    tencent_cloud.py        -- FIX: return [] from get_rules
config.example.yaml        -- EXTEND: add optional timeout section
tests/
  test_ip_fetcher.py       -- EXTEND: tests for fallback, timeout, validation
  test_updater.py          -- EXTEND: tests for add-before-delete order
  test_huawei_cloud.py     -- EXTEND: tests for add_rules error handling
```

### Pattern 1: Multi-Provider IP Detection with Fallback
**What:** Sequential fallback chain trying multiple IP detection services
**When to use:** IP detection in `ip_fetcher.py`
**Example:**
```python
# Source: design decision D-05/D-06/D-07
import ipaddress
import requests
from typing import Optional

# Provider definitions: (name, url, needs_token)
IP_PROVIDERS = [
    {
        "name": "ipinfo",
        "url_fn": lambda token: f"https://ipinfo.io/ip?token={token}",
        "needs_token": True,
    },
    {
        "name": "icanhazip",
        "url_fn": lambda _: "https://icanhazip.com",
        "needs_token": False,
    },
    {
        "name": "ipify",
        "url_fn": lambda _: "https://api.ipify.org",
        "needs_token": False,
    },
    {
        "name": "ifconfig.me",
        "url_fn": lambda _: "https://ifconfig.me",
        "needs_token": False,
    },
]

def get_current_ip(timeout=(3, 5), tokens=None):
    """
    Try providers in order, return first valid IP.
    Each provider gets its own independent timeout.
    """
    for provider in IP_PROVIDERS:
        try:
            url = provider["url_fn"](tokens[0] if provider["needs_token"] and tokens else None)
            response = requests.get(url, timeout=timeout)
            if response.status_code == 200:
                ip_str = response.text.strip()
                # Validate before returning (REL-03)
                ipaddress.ip_address(ip_str)  # raises ValueError if invalid
                return ip_str
        except (requests.RequestException, ValueError) as e:
            logger.warning(f"Provider {provider['name']} failed: {e}")
            continue
    return None  # All providers failed
```

### Pattern 2: Retry with tenacity on Cloud API Methods
**What:** Decorator-based retry with exponential backoff on cloud provider methods
**When to use:** All cloud API calls (get_rules, add_rules, delete_rules)
**Example:**
```python
# Source: tenacity official docs + design decision D-09/D-10/D-11
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)
import requests
import logging

logger = logging.getLogger(__name__)

# Retry only on network/transient errors
RETRYABLE_EXCEPTIONS = (
    requests.exceptions.ConnectionError,
    requests.exceptions.Timeout,
)

cloud_retry = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type(RETRYABLE_EXCEPTIONS),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)

@cloud_retry
def get_rules(self, group_id):
    # ... existing implementation
```

**Important:** The cloud SDK exceptions (`ClientRequestException` for Huawei, `TencentCloudSDKException` for Tencent) need to be evaluated for retryability. 5xx-equivalent errors should be retried; 4xx-equivalent (auth failures, bad requests) should not. The retry decorator should be applied at the `updater.py` call level rather than inside each provider, so provider-specific exception classification can happen in one place.

### Pattern 3: Add-Before-Delete Rule Update
**What:** New rules are added before old rules are deleted, ensuring no access gap
**When to use:** `updater.py:update_security_group_rules()`
**Example:**
```python
# Source: design decision D-13/D-14/D-15
def update_security_group_rules(self, sg, rules, ip):
    existed_rules = self.fetch_security_group_rules(sg)

    # ADD new rules FIRST (D-13)
    logger.info(f"Adding rules to security group {sg}...")
    self.client.add_rules(sg, rules, ip)

    # DELETE old rules SECOND (only after new rules are in place)
    if existed_rules:
        logger.info(f"Deleting old rules from security group {sg}...")
        self.client.delete_rules(sg, existed_rules)
    else:
        logger.info(f"No old rules to delete in security group {sg}")
```

### Anti-Patterns to Avoid
- **Retry on 4xx errors:** Auth failures and config errors are not transient. Per D-11, these must fail immediately, not waste 3 retries.
- **Shared timeout budget across providers:** Each provider must have its own independent timeout (D-07). A timeout to ipinfo must not reduce the available time for icanhazip.
- **Returning None from get_rules:** This causes rule accumulation (REL-06). Must return `[]` consistently.
- **Deleting before adding:** The current code deletes first, creating a window where no rules exist. This must be reversed.
- **tenacity >= 9.1:** This drops Python 3.9 support. Must pin to `tenacity~=9.0.0`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Retry with exponential backoff | Manual retry loop with sleep and counter | tenacity library | Handles edge cases (jitter, stop conditions, logging hooks), well-tested, 264M+ downloads |
| IP address validation | Regex or string parsing | `ipaddress.ip_address()` from stdlib | Handles all IPv4/IPv6 edge cases, maintained by Python core team, raises clear ValueError |
| HTTP timeouts | Socket-level timeout management | `requests.get(url, timeout=(connect, read))` | Built into requests, handles connect vs read distinction correctly |

**Key insight:** This phase is about defensive programming on an existing codebase. Every change should be minimal and surgical -- wrap existing calls with timeouts, add fallback providers, reverse two lines of code. No architectural changes needed.

## Common Pitfalls

### Pitfall 1: tenacity Version Incompatibility
**What goes wrong:** Using `tenacity>=9.1` (latest) which requires Python >=3.10, breaking the project's Python 3.9 compatibility.
**Why it happens:** pip will resolve to the latest version (9.1.4) by default. The version constraint in pyproject.toml must be explicit.
**How to avoid:** Pin `tenacity~=9.0.0` in pyproject.toml. The `~=` operator allows 9.0.x patch updates but blocks 9.1.x.
**Warning signs:** `pip install` fails on Python 3.9 CI with "No matching distribution found".

### Pitfall 2: Fallback Provider Timeout Bleed
**What goes wrong:** If ipinfo takes 8 seconds to timeout, the remaining providers have less time, causing cascading failures.
**Why it happens:** Using a shared `requests.Session` with a global timeout, or reusing the same response object.
**How to avoid:** Each provider call creates a fresh `requests.get()` with its own timeout tuple. No session reuse. Per D-07, each provider's timeout is independent.
**Warning signs:** All four providers fail in a single check cycle even though only ipinfo is actually down.

### Pitfall 3: get_rules() Returning None vs Empty List
**What goes wrong:** After changing get_rules() to return `[]`, the caller logic in `updater.py:53` still checks `if existed_rules:` which is truthy for a non-empty list and falsy for `[]`. This is correct behavior -- but if someone changes it back to `None`, the bug returns.
**Why it happens:** The original code returned `None` implicitly on exception, and the caller used `if existed_rules:` which is falsy for both `None` and `[]`.
**How to avoid:** Change both provider implementations to explicitly `return []` in exception handlers. Add a comment explaining why. The test `test_update_security_group_rules_without_existed_rules` already verifies `[]` behavior.
**Warning signs:** Rules accumulating in security groups (new rules added every cycle without old ones being deleted).

### Pitfall 4: Retry on Auth Failures
**What goes wrong:** Retrying a 401/403 auth failure 3 times wastes 15+ seconds and achieves nothing.
**Why it happens:** Not distinguishing between retryable (5xx, network) and non-retryable (4xx) errors in the retry predicate.
**How to avoid:** Use `retry_if_exception_type()` with only network-level exceptions (ConnectionError, Timeout). Cloud SDK exceptions that indicate 4xx should NOT be in the retry list. Per D-10 and D-11, only retry network errors and 5xx.
**Warning signs:** 15-second delays on every check cycle when credentials are wrong.

### Pitfall 5: IPinfo Token Exposure in Logs
**What goes wrong:** The current code logs the full URL including token: `logger.info(f"通过 {url} 获取 IP")`.
**Why it happens:** The URL is constructed with the token embedded.
**How to avoid:** When implementing the fallback chain, log only the provider name (e.g., "Trying ipinfo..."), not the full URL. This is already flagged in CONCERNS.md but the refactor should fix it as a side effect.
**Warning signs:** API tokens appearing in `update_whitelist.log*` files.

### Pitfall 6: Huawei Cloud SDK Retry Behavior
**What goes wrong:** Huawei Cloud SDK raises `ClientRequestException` for both 4xx and 5xx errors, but the exception has `status_code` and `error_code` fields to distinguish them.
**Why it happens:** Not inspecting the exception details before deciding to retry.
**How to avoid:** If applying tenacity at the provider method level, create a custom retry predicate that checks `e.status_code >= 500` for Huawei exceptions. Alternatively, apply retry at the updater level and handle provider-specific exception parsing there. The CONTEXT.md discretion area allows Claude to decide the best approach.
**Warning signs:** Retrying 401 auth failures on Huawei Cloud.

## Code Examples

### Timeout Configuration in Pydantic Config Model
```python
# Source: design decisions D-01/D-02/D-03
# Adding to update_whitelist/config/config.py

class TimeoutConfig(BaseModel):
    connect: int = 3  # seconds
    read: int = 5     # seconds

class IPDetectionConfig(BaseModel):
    connect: int = 3  # seconds
    read: int = 5     # seconds

class CloudAPITimeoutConfig(BaseModel):
    connect: int = 3  # seconds
    read: int = 10    # seconds

class TimeoutSettings(BaseModel):
    ip_detection: IPDetectionConfig = IPDetectionConfig()
    cloud_api: CloudAPITimeoutConfig = CloudAPITimeoutConfig()

class Config(BaseModel):
    huawei: Optional[CloudProvider] = None
    tencent: Optional[CloudProvider] = None
    aliyun: Optional[CloudProvider] = None
    ipinfo: Optional[IPInfo] = None
    timeouts: TimeoutSettings = TimeoutSettings()  # optional, has sensible defaults
```

### Timeout in config.example.yaml
```yaml
# Optional: timeout settings (defaults shown, most users don't need to change)
# timeouts:
#   ip_detection:
#     connect: 3
#     read: 5
#   cloud_api:
#     connect: 3
#     read: 10
```

### IP Validation Pattern
```python
# Source: Python stdlib docs + REL-03
import ipaddress

def validate_ip(ip_str: str) -> str:
    """
    Validate that a string is a valid IPv4 or IPv6 address.
    Returns the validated IP string.
    Raises ValueError if invalid.
    """
    ipaddress.ip_address(ip_str)  # Raises ValueError for invalid IPs
    return ip_str

# Usage in get_current_ip:
# ip_str = response.text.strip()
# validate_ip(ip_str)  # Rejects HTML error pages, rate-limit messages, etc.
# return ip_str
```

### tenacity Retry Applied at Updater Level
```python
# Source: tenacity docs + design decisions D-09/D-10/D-11/D-12
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type, before_sleep_log

# Applied in updater.py, wrapping the cloud API calls
# This keeps retry logic centralized and allows provider-specific error handling

class Updater:
    def update_security_group_rules(self, sg, rules, ip):
        existed_rules = self.fetch_security_group_rules(sg)

        # Add new rules first (D-13)
        self._retryable_call(lambda: self.client.add_rules(sg, rules, ip))

        # Delete old rules after (D-13)
        if existed_rules:
            self._retryable_call(lambda: self.client.delete_rules(sg, existed_rules))

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((ConnectionError, Timeout)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    def _retryable_call(self, fn):
        return fn()
```

### Huawei Cloud add_rules Fix (REL-07)
```python
# Source: existing pattern from huawei_cloud.py:delete_rules (lines 22-31)

def add_rules(self, group_id, rules, ip):
    """Batch add rules"""
    try:
        request = BatchCreateSecurityGroupRulesRequest()
        request.security_group_id = group_id
        rules_body = [
            BatchCreateSecurityGroupRulesOption(
                description=f"from Wulihe{' - ' + rule['desc'] if rule.get('desc') else ''}",
                direction="ingress",
                protocol="tcp",
                multiport=str(rule['port']),
                remote_ip_prefix=str(ip)
            ) for rule in rules
        ]
        request.body = BatchCreateSecurityGroupRulesRequestBody(
            security_group_rules=rules_body
        )
        response = self.client.batch_create_security_group_rules(request)
        logger.info(f"Added {len(rules)} rules to {group_id}")
    except exceptions.ClientRequestException as e:
        BaseCloudProvider.log(e)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| No timeout on requests | `timeout=(connect, read)` tuple | N/A (always available in requests) | Prevents indefinite hangs |
| Single IP provider | Multi-provider fallback chain | This phase | Resilience against provider outages |
| No IP validation | `ipaddress.ip_address()` validation | This phase | Prevents garbage in security groups |
| No retry | tenacity retry with backoff | This phase | Handles transient API failures |
| Delete-before-add | Add-before-delete | This phase | Prevents lockout during updates |
| tenacity >= 9.1 (latest) | tenacity ~= 9.0.0 | tenacity 9.1 dropped Python 3.9 (2025) | Must pin for Python 3.9 compat |

**Deprecated/outdated:**
- `config.dict()` in Pydantic v2: should use `config.model_dump()` (noted in CONCERNS.md, deferred to Phase 2 as CONF-04)

## Open Questions

1. **Where to apply tenacity retry decorator -- provider level or updater level?**
   - What we know: Cloud SDK exceptions differ between Huawei (`ClientRequestException`) and Tencent (`TencentCloudSDKException`). Both have status codes to distinguish 4xx from 5xx.
   - What's unclear: Whether the retry predicate should inspect provider-specific exception fields.
   - Recommendation: Apply retry at the updater call level with a generic predicate. Provider methods already catch their own SDK exceptions and log them. If they re-raise instead of swallowing, the updater can decide whether to retry. This keeps provider code simple and retry policy centralized.

2. **Should fallback providers use `requests.get()` directly or share a `requests.Session`?**
   - What we know: Sessions provide connection pooling which is beneficial for repeated calls.
   - What's unclear: Whether session reuse affects timeout independence between providers.
   - Recommendation: Use `requests.get()` directly (no session) for IP detection. These are different hosts (ipinfo.io, icanhazip.com, etc.) so connection pooling provides no benefit. Each call gets a fresh timeout.

3. **How to handle Huawei Cloud SDK exceptions that don't inherit from standard Python exceptions?**
   - What we know: `ClientRequestException` is a custom SDK exception, not a subclass of `ConnectionError` or `Timeout`.
   - What's unclear: Whether Huawei SDK throws `ConnectionError` for network-level failures or wraps them in `ClientRequestException`.
   - Recommendation: Test this during implementation. If Huawei SDK wraps network errors in `ClientRequestException`, the retry predicate needs to check `e.status_code` to distinguish network errors (retry) from auth errors (don't retry). The `before_sleep` log will help diagnose this.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.9+ | Runtime | Yes (dev: 3.13.11) | 3.13.11 | CI tests 3.9-3.12 |
| requests | IP detection + SDK | Yes | ~=2.32.3 | -- |
| tenacity | Retry logic | No (not yet installed) | 9.0.0 (to install) | -- |
| pytest | Testing | Yes | ~=8.2.2 | -- |
| pytest-mock | Testing | Yes | ~=3.14.0 | -- |
| ipaddress | IP validation | Yes | stdlib | -- |

**Missing dependencies with no fallback:**
- tenacity: Must be added to `pyproject.toml` dependencies before implementation.

**Missing dependencies with fallback:**
- None.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.2.2 |
| Config file | pyproject.toml [tool.pytest.ini_options] |
| Quick run command | `pytest tests/ -x -q` |
| Full suite command | `pytest tests/ -v --tb=short` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| REL-01 | IP detection requests timeout after configured duration | unit | `pytest tests/test_ip_fetcher.py -x -q` | Yes (extend existing) |
| REL-01 | Cloud API requests timeout after configured duration | unit | `pytest tests/test_huawei_cloud.py tests/test_tencent_cloud.py -x -q` | Yes (extend existing) |
| REL-02 | Fallback to next provider when primary fails | unit | `pytest tests/test_ip_fetcher.py::test_fallback -x -q` | No (Wave 0) |
| REL-02 | Return None when all providers fail | unit | `pytest tests/test_ip_fetcher.py::test_all_providers_fail -x -q` | No (Wave 0) |
| REL-03 | Invalid IP rejected before cloud API call | unit | `pytest tests/test_ip_fetcher.py::test_ip_validation -x -q` | No (Wave 0) |
| REL-04 | Cloud API calls retry on transient failure | unit | `pytest tests/test_updater.py -x -q` | Yes (extend existing) |
| REL-04 | Cloud API calls do NOT retry on 4xx errors | unit | `pytest tests/test_updater.py::test_no_retry_on_auth_error -x -q` | No (Wave 0) |
| REL-05 | Rules added before old rules deleted | unit | `pytest tests/test_updater.py::test_add_before_delete -x -q` | Yes (modify existing) |
| REL-06 | get_rules() returns [] on error | unit | `pytest tests/test_huawei_cloud.py tests/test_tencent_cloud.py -x -q` | Yes (modify existing) |
| REL-07 | huawei_cloud.add_rules() catches exceptions | unit | `pytest tests/test_huawei_cloud.py::test_add_rules_error -x -q` | No (Wave 0) |

### Sampling Rate
- **Per task commit:** `pytest tests/ -x -q`
- **Per wave merge:** `pytest tests/ -v --tb=short`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_ip_fetcher.py` -- tests for: multi-provider fallback, all-providers-fail returning None, IP validation rejecting invalid input, timeout behavior
- [ ] `tests/test_updater.py` -- modify `test_update_security_group_rules_with_existed_rules` to verify add-before-delete order (currently tests delete-before-add)
- [ ] `tests/test_huawei_cloud.py` -- test for `add_rules()` error handling (currently only happy path)
- [ ] `tests/test_huawei_cloud.py` -- test for `get_rules()` returning `[]` on error (currently no error case test)
- [ ] `tests/test_tencent_cloud.py` -- test for `get_rules()` returning `[]` on error

## Sources

### Primary (HIGH confidence)
- tenacity official docs (tenacity.readthedocs.io) -- API, decorator parameters, retry predicates
- Python stdlib `ipaddress` docs (docs.python.org/3/library/ipaddress.html) -- ip_address() validation
- requests official docs (requests.readthedocs.io) -- timeout tuple parameter
- Source code read: all files in `update_whitelist/` and `tests/`

### Secondary (MEDIUM confidence)
- PyPI tenacity package info (pypi.org/project/tenacity/) -- version metadata
- GitHub jd/tenacity releases page -- version history and Python support timeline
- ipify official docs (ipify.org) -- API response format (plain text)
- icanhazip.com and ifconfig.me -- community-verified plain text IP response format

### Tertiary (LOW confidence)
- Web search results on provider reliability -- while all four providers are well-known, their exact uptime SLAs are not formally documented

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- tenacity verified compatible with Python 3.9 at version 9.0.0; ipaddress is stdlib; requests timeout is well-documented
- Architecture: HIGH -- changes are minimal and surgical; existing Strategy pattern is preserved; no new files needed
- Pitfalls: HIGH -- tenacity version incompatibility is a verified, documented risk; other pitfalls are direct observations from the existing codebase

**Research date:** 2026-04-05
**Valid until:** 2026-05-05 (30 days -- stable domain with mature libraries)
