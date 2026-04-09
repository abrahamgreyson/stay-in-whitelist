# Architecture

**Analysis Date:** 2026-04-04

## Pattern Overview

**Overall:** Scheduled daemon with Strategy pattern for multi-cloud support

**Key Characteristics:**
- Periodic polling via APScheduler (every 180 seconds)
- Strategy pattern for cloud provider implementations (abstract base class with concrete providers)
- Delete-and-recreate approach for security group rules (no in-place updates)
- File-based IP caching for change detection
- Pydantic models for typed configuration from YAML

## Layers

**Scheduler / Entry Layer:**
- Purpose: Orchestrates periodic IP checks and triggers updates
- Location: `main.py`
- Contains: APScheduler setup, IP change detection logic, top-level error handling
- Depends on: `update_whitelist.ip_fetcher`, `update_whitelist.updater`, `update_whitelist.config.config`
- Used by: Direct invocation (`python main.py`) or systemd service

**IP Detection Layer:**
- Purpose: Detects the machine's current public IP and compares against cached value
- Location: `update_whitelist/ip_fetcher.py`
- Contains: `get_current_ip()`, `load_cached_ip()`, `cache_ip()` functions
- Depends on: `requests` (HTTP), `ipinfo.io` API, local filesystem for cache
- Used by: `main.py`

**Updater / Orchestration Layer:**
- Purpose: Iterates config-driven cloud providers, regions, and security groups; delegates to provider clients
- Location: `update_whitelist/updater.py`
- Contains: `Updater` class with `update_cloud_providers()`, `update_security_group_rules()`, `set_client()`, `fetch_security_group_rules()`
- Depends on: `update_whitelist.cloud_providers.tencent_cloud.TencentCloud`, `update_whitelist.cloud_providers.huawei_cloud.HuaweiCloud`, `update_whitelist.config.config`
- Used by: `main.py`

**Cloud Provider Layer:**
- Purpose: Abstracts cloud-specific API calls into a uniform interface
- Location: `update_whitelist/cloud_providers/`
- Contains: `BaseCloudProvider` (ABC), `HuaweiCloud`, `TencentCloud` implementations
- Depends on: Vendor SDKs (`huaweicloudsdkcore`, `huaweicloudsdkvpc`, `tencentcloud_sdk_python_*`)
- Used by: `update_whitelist.updater.Updater`

**Configuration Layer:**
- Purpose: Loads and validates YAML config into typed Pydantic models
- Location: `update_whitelist/config/config.py`, `update_whitelist/config/config_loader.py`
- Contains: Pydantic models (`Config`, `CloudProvider`, `Region`, `Rule`, `Allow`, `IPInfo`) and a legacy `load_config()` helper
- Depends on: `pydantic`, `pyyaml`
- Used by: All layers import the `config` singleton

**Logging Layer:**
- Purpose: Provides a module-level logger with console + rotating file handlers
- Location: `update_whitelist/logger.py`
- Contains: `get_logger()` factory function
- Depends on: Python `logging` standard library
- Used by: All modules

## Data Flow

**IP Update Cycle (every 180 seconds):**

1. APScheduler triggers `check_and_update_ip()` in `main.py`
2. `has_ip_changed()` calls `get_current_ip()` in `update_whitelist/ip_fetcher.py`
3. `get_current_ip()` makes HTTP GET to `ipinfo.io/ip?token=<random_token>` using a randomly selected token from config
4. Response is compared to cached IP from `ip_cache.txt` (loaded via `load_cached_ip()`)
5. If IP changed: new IP is cached to `ip_cache.txt` via `cache_ip()`
6. If IP changed: `Updater()` is instantiated and `update_cloud_providers(current_ip, config)` is called
7. `Updater.update_cloud_providers()` iterates over each cloud provider in config (skipping `ipinfo` and `None` entries)
8. For each provider, for each region, for each security group rule: `set_client()` creates the appropriate cloud SDK client
9. `update_security_group_rules(sg, allows, ip)` is called for each security group
10. Existing rules matching the "from Wulihe" prefix are fetched via `client.get_rules(sg)`
11. All matching existing rules are deleted via `client.delete_rules(sg, rules)`
12. New rules are created via `client.add_rules(sg, allows, ip)` with the current IP

**State Management:**
- IP state: Persisted in `ip_cache.txt` (single line file containing last known IP)
- Configuration: Loaded once at module import time from `config.yaml` into a Pydantic `Config` singleton
- Cloud provider client: Recreated per security group via `set_client()` (instance variable on `Updater`)

## Key Abstractions

**BaseCloudProvider (Abstract Base Class):**
- Purpose: Defines a uniform interface for cloud security group operations
- Location: `update_whitelist/cloud_providers/base_cloud_provider.py`
- Pattern: Strategy / Template Method -- subclasses implement `initialize_client()`, `get_rules()`, `add_rules()`, `delete_rules()`
- Constructor: Accepts `access_key`, `secret_key`, `region`, and optional `**kwargs`; calls `self.initialize_client()`
- Static helper: `BaseCloudProvider.log(e)` provides cloud-aware error formatting for Huawei and Tencent SDK exceptions

**Concrete Providers:**
- `HuaweiCloud` at `update_whitelist/cloud_providers/huawei_cloud.py` -- uses Huawei VPC SDK; filters rules by `description.startswith("from Wulihe")` and `direction == "ingress"`
- `TencentCloud` at `update_whitelist/cloud_providers/tencent_cloud.py` -- uses Tencent VPC SDK; filters rules by `PolicyDescription.startswith('from Wulihe')`

**Config Pydantic Models:**
- Purpose: Typed access to YAML configuration with validation
- Location: `update_whitelist/config/config.py`
- Hierarchy: `Config` contains optional `CloudProvider` instances (huawei, tencent, aliyun) and `IPInfo`; each `CloudProvider` has `regions: List[Region]`; each `Region` has `rules: List[Rule]`; each `Rule` has `sg` (security group ID) and `allow: List[Allow]`; each `Allow` has `port` and optional `desc`

**Updater:**
- Purpose: Orchestration layer that bridges config data and cloud provider implementations
- Location: `update_whitelist/updater.py`
- Pattern: Mediator -- holds a `client` reference that is swapped per provider/region via `set_client()`
- Client selection: Hardcoded `if/elif` dispatch in `set_client()` based on provider name string

## Entry Points

**CLI / Direct Execution:**
- Location: `main.py`
- Triggers: `python main.py` or systemd service
- Responsibilities: Starts APScheduler `BlockingScheduler` with 180-second interval, runs `check_and_update_ip()` on each tick

**Module Init (config singleton):**
- Location: `update_whitelist/config/config.py` (bottom of file, module-level code)
- Triggers: First import of `update_whitelist.config.config`
- Responsibilities: Reads `config.yaml` from project root, parses into `Config` Pydantic model, exposes as module-level `config` variable

## Error Handling

**Strategy:** Catch-and-log at each layer; never propagate fatal errors upward in the scheduler loop

**Patterns:**
- `main.py` wraps `has_ip_changed()` in broad `except Exception` to catch network failures, returning `(False, None)` so the scheduler loop continues
- `main.py` wraps `check_and_update_ip()` in `except Exception` to ensure one failed update does not kill the scheduler
- `BaseCloudProvider.log()` provides structured error formatting per cloud SDK exception type
- `Updater.fetch_security_group_rules()` catches exceptions and returns `None` (treated as "no existing rules")
- Cloud provider methods (`get_rules`, `delete_rules`) catch SDK-specific exceptions and log via `BaseCloudProvider.log()`

**Gap:** `HuaweiCloud.add_rules()` does not have try/except -- any SDK exception will propagate unhandled to the caller

## Cross-Cutting Concerns

**Logging:** Python `logging` module with dual handlers:
- Console stream handler (DEBUG level)
- `TimedRotatingFileHandler` writing to `update_whitelist.log` (rotates every 24 hours, keeps 7 backups)
- Format: `%(asctime)s - %(levelname)s - %(message)s`
- Factory: `get_logger(name=__name__)` in `update_whitelist/logger.py` with handler deduplication (only adds handlers if none exist)

**Validation:** Pydantic models validate config structure at load time. No runtime input validation beyond this.

**Authentication:** Cloud credentials stored directly in `config.yaml` (access_key / secret_key per provider). The `ipinfo` section holds API tokens for the IP detection service.

**Configuration Management:**
- Primary config file: `config.yaml` (gitignored, contains real credentials)
- Template: `config.example.yaml` (committed, contains placeholder values)
- Module-level singleton: `config` object in `update_whitelist/config/config.py` loaded once at import time
- Legacy helper: `update_whitelist/config/config_loader.py` contains `load_config()` function that is not used by the main flow (superseded by the Pydantic-based config)

---

*Architecture analysis: 2026-04-04*
