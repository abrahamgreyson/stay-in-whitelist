# Project Research Summary

**Project:** Stay in Whitelist
**Domain:** Python systemd daemon for dynamic IP detection and cloud security group whitelist management
**Researched:** 2026-04-05
**Confidence:** HIGH

## Executive Summary

Stay in Whitelist is a single-process Python daemon that polls for public IP changes and updates security group rules on Huawei Cloud and Tencent Cloud. It is not a web service, not a SaaS product, and not a distributed system. The dominant pattern in this space is a simple cron job or systemd service that runs a linear check cycle every few minutes. Competing tools (aws-sg-updater, daniloaz's bash script) are all single-cloud, single-provider bash or Python scripts with no resilience features. Stay in Whitelist already differentiates with multi-cloud support via a Strategy pattern provider abstraction and typed YAML config with Pydantic validation.

The recommended approach is a focused refactoring organized into three phases: (1) fix five critical bugs that cause lockouts, silent hangs, and rule corruption; (2) clean up operational deployment, paths, logging, and project identity; (3) harden with health checks, idempotent operations, and production observability. The stack stays conservative: Python 3.9+, APScheduler 3.11.x (not 4.x alpha), requests 2.32.x with timeouts, tenacity 8.x (not 9.x which drops Python 3.9 support), and Pydantic 2.x. No async, no task queues, no containers, no databases.

The key risk is the delete-before-add rule update ordering. If the "add new rules" API call fails after old rules are deleted, the user is locked out of all cloud services until manual console intervention. The mitigation is strict add-first-then-delete ordering with verification between the steps. The second risk is silent scheduler death: a hanging `requests.get()` without timeout causes APScheduler to skip all future checks while the process appears healthy. Both are well-understood problems with clear fixes confirmed against the actual codebase.

## Key Findings

### Recommended Stack

The stack is already mostly determined by the existing codebase. No technology changes are needed -- only version pins and one new dependency (tenacity for retry).

**Core technologies:**
- **Python >=3.9** -- Existing deployment constraint; do not drop 3.9 support. The ipaddress CVE-2021-29921 fix is in 3.9.5+, so ensure >=3.9.5.
- **APScheduler 3.11.2** -- Production/stable scheduler with `BlockingScheduler` ideal for a single-purpose daemon. APScheduler 4.x is alpha (4.0.0a6 as of Apr 2025) with a completely different async-first API; do not use it.
- **requests 2.32.5** -- HTTP client for IP detection APIs. The missing-timeout bug is not a requests problem; it is a missing `timeout=` parameter. Add `timeout=(3.05, 10)` everywhere.
- **Pydantic 2.x (latest: 2.12.5)** -- Already in use for config models. Migrate deprecated `config.dict()` to `config.model_dump()` during refactoring.
- **tenacity 8.5.0** -- Retry with exponential backoff. **Critical: pin to `>=8.4,<9`** because tenacity 9.x requires Python >=3.10, violating the 3.9+ constraint. Use `@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=30))` on cloud SDK calls.
- **PyYAML 6.0.3** -- Config file parsing. Already in use, no changes needed.

**Supporting:**
- **ipaddress (stdlib, built-in)** -- Validate IP detection responses with `ipaddress.ip_address()` before writing to security groups. Zero-dependency, part of Python since 3.3.
- **pathlib (stdlib, built-in)** -- Replace `os.path` usage with `pathlib.Path` for absolute path handling; fixes systemd WorkingDirectory bug.
- **logging (stdlib, built-in)** -- Already using `TimedRotatingFileHandler`; replace all `print()` calls with `logger.info/error`.
- **ruff** -- Recommended replacement for flake8/black as dev dependency. Single tool, very fast, Python 3.9+ compatible.

**Do not use:** APScheduler 4.x (alpha), tenacity 9.x (drops Python 3.9), asyncio/aiohttp (over-engineering for 2-3 sequential HTTP calls per cycle), Celery/dramatiq (task queues for a single-process daemon), httpx (unnecessary without async need).

See `.planning/research/STACK.md` for full version compatibility matrix and alternatives analysis.

### Expected Features

**Must have (table stakes / P1 -- addresses known bugs and operational failures):**
- Reliable IP detection with timeout on ALL network requests -- fixes the primary scheduler hang bug
- Multi-provider IP detection fallback (ipinfo -> icanhazip -> ipify -> checkip.amazonaws.com) -- fixes ipinfo rate-limit failures
- IP format validation before security group writes -- prevents garbage in security groups
- Add-before-delete rule update ordering -- prevents lockout on API failure
- Cloud API retry with exponential backoff (tenacity 8.x) -- handles transient cloud failures
- `get_rules()` returns `[]` on error, not `None` -- prevents rule accumulation
- File paths use absolute paths -- fixes systemd deployment
- Structured logging replacing all `print()` calls -- enables diagnostics
- Configurable check interval (default 600s) -- operational flexibility
- Exception handling on `HuaweiCloud.add_rules()` -- currently unhandled
- Project rename to "Stay in Whitelist" -- identity alignment

**Should have (competitive / P2 -- adds resilience):**
- Startup immediate check -- ensures tool works from second zero
- Health check / self-monitoring with consecutive failure tracking -- detects silent death
- Idempotent rule management (skip add if rule already exists) -- reduces unnecessary API calls
- IP change notification via logging (old IP -> new IP, success/failure) -- visibility
- systemd `WatchdogSec` integration -- OS-level hang detection
- Rule cleanup on startup (detect stale rules from downtime)

**Defer (v2+):**
- Webhook notifications -- only if external alerting needed
- Additional cloud providers (AWS, Azure, Alibaba) -- only if user needs them
- IPv6 support -- only when cloud providers require it
- Configuration hot-reload -- only if config changes frequently

**Anti-features to avoid:** Web UI/dashboard, async architecture, database for state, Docker deployment, multi-tenant support, secret management integration. Each adds complexity that contradicts the project's self-use, single-process daemon nature.

See `.planning/research/FEATURES.md` for full dependency graph, competitor analysis, and anti-features.

### Architecture Approach

The existing architecture is sound: a layered design with Strategy pattern for cloud providers. No structural rewrite is needed. The main work is fixing bugs within the existing layer boundaries.

**Major components (existing, to be hardened):**
1. **Scheduler / Entry Layer** (`main.py`) -- APScheduler `BlockingScheduler` with configurable interval. Needs `misfire_grace_time=None`, `coalesce=True`, and startup immediate check.
2. **IP Detection Layer** (`ip_fetcher.py`) -- Currently single-provider. Needs multi-provider fallback chain with per-provider timeout and IP validation.
3. **Updater / Orchestration Layer** (`updater.py`) -- Iterates providers/regions/SGs. Needs add-before-delete ordering, retry decoration, and `get_rules()` return value fix.
4. **Cloud Provider Layer** (`cloud_providers/`) -- Strategy pattern with `BaseCloudProvider` ABC. `HuaweiCloud.add_rules()` needs try/except. Both providers need tenacity retry on SDK calls.
5. **Configuration Layer** (`config/config.py`) -- Pydantic models with module-level singleton. Needs lazy loading (not import-time file I/O) and `model_dump()` migration.

**Key patterns to maintain:**
- Strategy pattern for cloud providers (add new providers by subclassing `BaseCloudProvider`)
- Pydantic config validation (typed access with early error detection)
- File-based IP caching (correct for single-IP state; do not replace with database)

**Key patterns to introduce:**
- Retry decorator (tenacity 8.x) on all external API calls
- Timeout tuple `(connect, read)` on all `requests` calls
- Absolute path derivation via `pathlib.Path` or config-specified base directory
- Add-first-then-delete rule update with verification between steps

See `.planning/codebase/ARCHITECTURE.md` for full layer descriptions and data flow diagrams.

### Critical Pitfalls

1. **Delete-before-add lockout** -- Current code deletes all rules before adding new ones. If the add API call fails, security group is empty and user is locked out. Fix: add new rules first, verify success, then delete old rules. (Confirmed: updater.py lines 46-63)
2. **Requests without timeout cause scheduler hang** -- `requests.get()` with no `timeout=` hangs indefinitely. APScheduler `max_instances=1` silently skips all future checks. Fix: add `timeout=(3.05, 10)` to every network call. (Confirmed: ip_fetcher.py line 22)
3. **No IP validation before writing to security groups** -- Error pages or rate-limit messages from IP providers get written as CIDR rules. Fix: validate with `ipaddress.ip_address()` before any cloud API call. (Confirmed: ip_fetcher.py)
4. **Single IP detection provider** -- When ipinfo.io quota is exhausted, tool silently stops detecting IP changes. Fix: implement fallback chain of 3-4 providers. (Confirmed: single get_current_ip() function)
5. **`get_rules()` returns `None` on error** -- Caller uses `if existed_rules:` which is falsy for both `None` and `[]`. Rules accumulate because deletion is skipped on API failure. Fix: return `[]` on error, or re-raise exception. (Confirmed: both cloud providers)

See `.planning/research/PITFALLS.md` for full analysis including warning signs, recovery strategies, and the "looks done but isn't" checklist.

## Implications for Roadmap

Based on combined research, the following three-phase structure is recommended:

### Phase 1: Critical Reliability Fixes
**Rationale:** Five pitfalls flagged as "Phase 1" in PITFALLS.md cause the tool to fail silently or destructively. The feature dependency graph confirms that all P2 features depend on timeouts and IP validation being in place first. Without timeouts, the add-before-delete fix is equally dangerous because the "add" step could hang.
**Delivers:** A daemon that does not hang, does not lock users out, and does not write garbage to security groups.
**Addresses:** Timeout on all requests, multi-provider IP fallback, IP validation, add-before-delete ordering, retry with backoff, `get_rules()` return fix, exception handling on `add_rules()`.
**Avoids:** Pitfalls 1-5 (lockout, scheduler hang, invalid IP, single provider, rule accumulation) and Pitfall 8 (APScheduler misfire configuration).
**Uses:** tenacity 8.5.0 for retry, `ipaddress` stdlib for validation, requests timeout tuples.
**Research flag:** Standard patterns. No deep research needed -- retry, validation, and fallback are well-documented.

### Phase 2: Operational Hardening and Code Quality
**Rationale:** Once the daemon is reliable, clean up the operational deployment issues (paths, logging, config) that cause problems in systemd production. These are LOW complexity but HIGH impact for day-to-day reliability.
**Delivers:** A daemon that deploys cleanly under systemd with proper logging, configurable intervals, and absolute file paths.
**Addresses:** Absolute file paths via pathlib, structured logging replacing print(), configurable check interval, project rename, Pydantic `model_dump()` migration, config lazy loading, remove dead Alibaba stub.
**Avoids:** Pitfall 6 (relative paths under systemd), technical debt patterns (module-level config loading, print statements, hardcoded interval).
**Uses:** `pathlib.Path` throughout, Python `logging` stdlib, Pydantic v2 API.
**Research flag:** Standard patterns. systemd daemon best practices are well-documented.

### Phase 3: Resilience and Self-Monitoring
**Rationale:** After the core is reliable and operationally clean, add features that make the tool self-aware of its own health. These address scenarios that happen eventually (extended downtime, repeated failures) rather than immediate bugs.
**Delivers:** A daemon that detects its own failures, runs checks immediately on startup, avoids duplicate rules, and notifies on IP changes.
**Addresses:** Startup immediate check, health check with consecutive failure tracking, idempotent rule management, IP change notification logging, systemd `WatchdogSec` integration, rule cleanup on startup.
**Avoids:** Pitfall 7 (silent death with no health check), performance traps (SDK client reuse per provider-region), security mistakes (credential exposure in logs).
**Uses:** `sd_notify` for systemd watchdog, tenacity retry on add-rules step specifically.
**Research flag:** Minor research needed on `sd_notify` Python integration for systemd watchdog. Pattern is documented but may need version-specific testing with the Python 3.9+ constraint.

### Phase Ordering Rationale

- Phase 1 comes first because the feature dependency graph shows all P2 features depend on P1 foundations (timeouts, validation, retry). Without timeouts, health checks cannot detect hangs. Without the add-before-delete fix, idempotent management is moot.
- Phase 2 comes before Phase 3 because absolute paths and structured logging are prerequisites for the health check features in Phase 3. A heartbeat file using relative paths under systemd defeats the purpose.
- Phase 3 is last because it addresses "eventually" scenarios rather than "right now" bugs. The tool works without these features; it just does not self-monitor.

### Research Flags

**Phases needing deeper research during planning:**
- **Phase 3 (systemd WatchdogSec):** The `sd_notify` Python integration needs verification against the Python 3.9+ constraint. The `systemd.daemon` module availability varies by platform. Consider whether `sd_notify` is available or if a heartbeat file is the pragmatic alternative.

**Phases with standard patterns (skip deep research):**
- **Phase 1:** Retry with exponential backoff (tenacity docs), IP validation (stdlib), add-before-delete (industry standard), multi-provider fallback (common pattern).
- **Phase 2:** Absolute paths (pathlib docs), structured logging (Python logging docs), systemd unit file configuration (systemd docs).

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All version pins verified against PyPI metadata. Python 3.9+ constraint validated against tenacity 9.x incompatibility (requires >=3.10) and APScheduler 4.x alpha status (4.0.0a6). Vendor SDKs have no alternatives. Sources: PyPI, codebase pyproject.toml. |
| Features | HIGH | 11 P1 features derived from 4 competitor tools, community reference implementations, and direct codebase bug analysis. Anti-features validated against PROJECT.md out-of-scope constraints. Dependency graph is explicit and verified. |
| Architecture | MEDIUM | The research ARCHITECTURE.md file was not generated by the researcher. Confidence is based on the codebase analysis in `.planning/codebase/ARCHITECTURE.md` which provides adequate layer descriptions and data flow. The existing Strategy pattern and layered design are sound. Gap: no research on whether IP detection providers should also use Strategy pattern or simpler list-of-callables approach. |
| Pitfalls | HIGH | All 5 critical pitfalls confirmed against actual source code with line references. 3 additional operational pitfalls documented with systemd-specific guidance. Recovery strategies derived from APScheduler GitHub issues, Stack Overflow answers, and vendor docs. The "looks done but isn't" checklist catches common shortcuts. |

**Overall confidence:** HIGH

### Gaps to Address

- **Architecture research file missing:** The research ARCHITECTURE.md was not generated. The codebase architecture analysis in `.planning/codebase/ARCHITECTURE.md` fills this gap adequately for roadmap purposes, but the roadmapper should reference it directly rather than expecting a research version.
- **Cloud SDK timeout configuration:** Research did not conclusively determine whether Huawei Cloud SDK and Tencent Cloud SDK client constructors accept timeout parameters. The STACK.md notes Huawei SDK has `connect_timeout` / `read_timeout` but this needs verification during Phase 1 implementation.
- **Tenacity integration with vendor SDK methods:** The retry decorator pattern with tenacity is well-documented for `requests` calls, but applying it to Huawei/Tencent SDK methods (which raise vendor-specific exceptions) needs the `retry_if_exception_type` parameter tuned per provider. Address during Phase 1 implementation.
- **IP detection provider availability:** The recommended 4-provider fallback chain (ipinfo, icanhazip, ipify, checkip.amazonaws.com) needs live verification at implementation time. Rate limits, response formats, and uptime may have changed.

## Sources

### Primary (HIGH confidence)
- PyPI version data: APScheduler 3.11.2 (released 2025-12-22), tenacity 8.5.0 / 9.1.4, requests 2.32.5, Pydantic 2.12.5, PyYAML 6.0.3
- APScheduler 3.x User Guide (readthedocs) -- scheduler configuration, misfire handling, coalesce behavior
- Python stdlib docs: `ipaddress`, `pathlib`, `logging` -- validation, path handling, structured logging
- Codebase analysis: `.planning/codebase/ARCHITECTURE.md`, `.planning/codebase/STRUCTURE.md`, `.planning/codebase/CONCERNS.md`
- Project requirements: `.planning/PROJECT.md`

### Secondary (MEDIUM confidence)
- APScheduler GitHub Issues #423, #450 -- scheduler hang and skipped job root causes
- Python requests timeout guide (ScrapingBee) -- tuple timeout best practice `(connect, read)`
- systemd watchdog with Python (stigok.net) -- `sd_notify` integration pattern
- systemd RestartSec and WatchdogSec guide (OneUptime) -- service reliability directives
- Huawei Cloud API rate limiting docs -- exponential backoff recommendation
- Huawei Cloud VPC security group limits -- 120 rules per SG, 500 total per account
- Competitor tools: aws-sg-updater (GitHub), daniloaz bash script, aws-ipupdater -- feature benchmarking
- CVE-2021-29921 (NVD) -- Python ipaddress validation bypass, fixed in 3.9.5

### Tertiary (LOW confidence)
- IPSpot multi-provider fallback library (GitHub) -- reference for fallback chain implementation pattern
- Reddit: Python requests hanging despite timeout -- community reports of edge cases
- Blog posts on systemd + Python daemon patterns -- general guidance

---
*Research completed: 2026-04-05*
*Ready for roadmap: yes*
