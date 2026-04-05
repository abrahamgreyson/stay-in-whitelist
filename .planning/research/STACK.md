# Stack Research

**Domain:** Python daemon for dynamic IP detection and cloud security group whitelist management
**Researched:** 2026-04-05
**Confidence:** HIGH

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Python | >=3.9 | Runtime | Existing constraint. The project deploys on systems where 3.9 is the floor. Do not drop 3.9 support. |
| APScheduler | 3.11.2 | Periodic task scheduling | The correct choice. Version 3.11.x is production/stable, supports Python 3.8+. APScheduler 4.x is still alpha (4.0.0a6, last updated Apr 2025) and should not be used. The BlockingScheduler is exactly what a single-purpose systemd daemon needs. |
| requests | 2.32.5 | HTTP client for IP detection APIs | Battle-tested, supports Python 3.9+. The existing timeout bug is not a requests problem -- it is a missing `timeout=` parameter on the existing `requests.get()` call. Keep requests, add timeouts everywhere. |
| Pydantic | 2.x (latest: 2.12.5) | Config validation and serialization | Already in use with v2. The project uses `BaseModel` for config models. Needs migration from deprecated `config.dict()` to `config.model_dump()` during refactoring. Pydantic v2 supports Python 3.9+. |
| PyYAML | 6.0.3 | Config file parsing | Standard YAML parser. Already in use. No reason to change. |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| tenacity | 8.5.0 | Retry with exponential backoff for cloud API calls | **CRITICAL: Use tenacity 8.x, NOT 9.x.** Tenacity 9.0+ requires Python >=3.10, which violates the project's 3.9+ constraint. Pin to `tenacity>=8.4,<9`. Use `@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=30))` on cloud API calls and IP detection requests. |
| huaweicloudsdkcore | latest 3.1.x | Huawei Cloud authentication | Vendor SDK, pin to compatible 3.1.x line. No alternative exists. |
| huaweicloudsdkvpc | latest 3.1.x | Huawei Cloud VPC/security group CRUD | Vendor SDK, pin to compatible 3.1.x line. No alternative exists. |
| tencentcloud_sdk_python_common | latest 3.0.x | Tencent Cloud authentication | Vendor SDK, pin to compatible 3.0.x line. No alternative exists. |
| tencentcloud_sdk_python_vpc | latest 3.0.x | Tencent Cloud VPC/security group CRUD | Vendor SDK, pin to compatible 3.0.x line. No alternative exists. |
| ipaddress (stdlib) | built-in | IP address format validation | Use `ipaddress.ip_address()` to validate that the IP detection response is actually an IP and not HTML error pages. Zero-dependency, part of Python stdlib since 3.3. |
| pathlib (stdlib) | built-in | File path handling for cache and logs | Replace `os.path` usage with `pathlib.Path` for cleaner absolute path handling. Fixes the systemd WorkingDirectory bug where relative paths break. |
| logging (stdlib) | built-in | Application logging with rotation | Already using `TimedRotatingFileHandler`. Keep it, but fix the relative path for the log file. Replace all `print()` calls with `logger.info/error`. |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| pytest | Test runner | Already in use at 8.2.2. Upgrade to latest 8.x is safe. |
| pytest-mock | Mocking support | Already in use. Standard for mocking `requests` and cloud SDK calls. |
| pytest-cov | Coverage reporting | Already in use. |
| setuptools + setuptools_scm | Build and versioning | Already in use. setuptools_scm reads git tags for version. |
| ruff | Linting and formatting | Recommended replacement for flake8/black. Single tool, very fast, Python 3.9+ compatible. Add to dev dependencies. |

## Installation

```bash
# Core dependencies (update versions in pyproject.toml)
pip install "APScheduler~=3.11.2" \
  "requests~=2.32.5" \
  "pydantic~=2.7" \
  "PyYAML~=6.0.3" \
  "tenacity>=8.4,<9" \
  "huaweicloudsdkcore~=3.1.99" \
  "huaweicloudsdkvpc~=3.1.99" \
  "tencentcloud_sdk_python_common~=3.0.1174" \
  "tencentcloud_sdk_python_vpc~=3.0.1174"

# Dev dependencies
pip install -D "pytest~=8.2" "pytest-mock~=3.14" "pytest-cov~=5.0" "ruff"
```

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| APScheduler 3.11.x | APScheduler 4.x | Never in this project. 4.x is alpha, API is completely different, and the 3.x BlockingScheduler is perfect for a single-purpose daemon. |
| tenacity 8.x | tenacity 9.x | Only if the project drops Python 3.9 support. 9.x requires >=3.10 and adds no features critical to this use case. |
| requests 2.32.x | httpx | If the project needed async HTTP. It does not -- the constraint is linear execution. requests is simpler and already integrated with cloud SDKs. |
| tenacity | hand-rolled retry loop | If you want zero new dependencies. A simple retry loop with `time.sleep(2 ** attempt)` works for 2-3 retries. But tenacity 8.x is a single pure-Python file with no transitive deps, and provides `stop_after_attempt`, `wait_exponential`, and `retry_if_exception_type` out of the box. Use tenacity. |
| Pydantic v2 | dataclasses + manual validation | If you wanted to remove the Pydantic dependency entirely. Not worth it -- Pydantic is already integrated, provides runtime validation on config load, and the models are already written. |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| tenacity 9.x | Requires Python >=3.10, violates the project's 3.9+ requirement | tenacity 8.5.0 (last 8.x release, supports 3.6+) |
| APScheduler 4.x | Still alpha (4.0.0a6). API is async-first and completely different from 3.x. Migration would be a rewrite for no benefit. | APScheduler 3.11.2 (stable, maintained, supports Python 3.8+) |
| asyncio / aiohttp | The project constraint is linear execution. Adding async complexity for 2-3 sequential HTTP calls per check cycle is over-engineering. | Linear execution with requests + timeouts |
| Celery / dramatiq | Task queues are for distributed workloads. This is a single-process daemon checking one IP every 10 minutes. | APScheduler BlockingScheduler |
| print() for logging | Already a known issue. print() goes to stdout which systemd captures, but without timestamps, log levels, or rotation control. | `logging` stdlib with `logger.info/error/warning` |
| config.dict() | Deprecated in Pydantic v2, will be removed in a future version. Already used in updater.py. | `config.model_dump()` (Pydantic v2 API) |
| relative file paths | Break under systemd when WorkingDirectory differs from project root. Already causing the ip_cache.txt and log file path bugs. | `pathlib.Path` with absolute paths derived from config or environment |

## Stack Patterns by Variant

**If Python 3.9 support can be dropped (unlikely):**
- Upgrade tenacity to 9.x for latest bug fixes
- All other stack choices remain identical

**If a new cloud provider is added (e.g., AWS, Alibaba):**
- Follow the existing BaseCloudProvider ABC pattern
- Install the vendor-specific SDK (boto3 for AWS, aliyun-python-sdk for Alibaba)
- Implement `initialize_client`, `get_rules`, `add_rules`, `delete_rules`
- Wrap all SDK calls with tenacity retry decorator

**If IP detection needs more resilience:**
- Add multiple providers in a fallback chain: ipinfo.io -> ipify.org -> ifconfig.me
- Each provider gets its own `get_current_ip()` implementation behind a common interface
- Wrap the chain with tenacity retry that advances to next provider on failure

## Version Compatibility

| Package A | Compatible With | Notes |
|-----------|-----------------|-------|
| tenacity 8.x | Python >=3.6 | Last version supporting 3.9. Pin to `>=8.4,<9`. |
| tenacity 9.x | Python >=3.10 | **INCOMPATIBLE** with this project's 3.9+ requirement. |
| APScheduler 3.11.x | Python >=3.8 | Stable. 4.x is alpha with no release timeline. |
| Pydantic 2.x | Python >=3.9 | v2 API. `model_dump()` replaces deprecated `dict()`. |
| requests 2.32.x | Python >=3.9 | Stable, maintained by PSF. |
| PyYAML 6.0.x | Python >=3.8 | Stable, no breaking changes expected. |

## Sources

- PyPI: APScheduler 3.11.2 (released 2025-12-22), verified stable, requires Python >=3.8 -- https://pypi.org/project/APScheduler/
- PyPI: APScheduler 4.0.0a6 (released 2025-04-27), pre-release, do not use -- https://pypi.org/project/APScheduler/#history
- PyPI: tenacity 9.1.4 (released 2026-02-07), requires Python >=3.10 -- https://pypi.org/project/tenacity/
- PyPI: requests 2.32.5 (released 2025-08-18), requires Python >=3.9 -- https://pypi.org/project/requests/
- PyPI: pydantic 2.12.5 (latest stable) -- https://pypi.org/project/pydantic/
- PyPI: PyYAML 6.0.3 (latest stable) -- https://pypi.org/project/PyYAML/
- Codebase analysis: `.planning/codebase/STACK.md`, `pyproject.toml`, source files in `update_whitelist/`

---
*Stack research for: Stay in Whitelist -- Python daemon for dynamic IP whitelist management*
*Researched: 2026-04-05*
