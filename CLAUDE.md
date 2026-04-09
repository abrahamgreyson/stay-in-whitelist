<!-- GSD:project-start source:PROJECT.md -->
## Project

**Stay in Whitelist**

一个定时检测本地公网 IP 变化并自动更新云服务安全组白名单的工具。解决动态 IP 环境下安全访问云服务（数据库、应用端口）的问题，避免长期暴露敏感端口。支持华为云、腾讯云，可扩展其他云服务。部署为 systemd 服务长期运行。

**Core Value:** IP 变了，白名单自动跟上 — 不漏更、不挂死、不锁死。

### Constraints

- **Python 版本**: 3.9+ — 兼容性要求
- **自用工具**: 不需要考虑多用户、权限控制、Web 界面
- **运行方式**: systemd 服务长期运行，需要健壮的错误恢复
- **无堡垒机**: 这是该工具存在的原因 — 在没有堡垒机的情况下保护端口访问
- **线性架构**: 保持简单，不需要引入异步或消息队列
<!-- GSD:project-end -->

<!-- GSD:stack-start source:codebase/STACK.md -->
## Technology Stack

## Languages
- Python 3.9+ - All source code, supports 3.9, 3.10, 3.11, 3.12 (declared in `pyproject.toml`)
- YAML - Configuration files (`config.yaml`, `config.example.yaml`)
- Shell (CI) - GitLab CI and GitHub Actions pipeline definitions
## Runtime
- Python >=3.9 (enforced via `requires-python` in `pyproject.toml`)
- GitLab CI uses `atomhub.openatom.cn/amd64/python:3.12-rc` Docker image
- GitHub Actions uses `actions/setup-python@v4` with matrix: 3.9, 3.10, 3.11, 3.12
- pip with `venv` for virtual environments
- `pyproject.toml` as the single source of truth for dependencies (PEP 621)
- No lockfile present (no `requirements.lock` or `poetry.lock`)
## Frameworks
- Pydantic 2.7.4 - Configuration validation and serialization via `BaseModel` (used in `update_whitelist/config/config.py`)
- APScheduler 3.10.4 - Scheduling periodic IP checks (blocking scheduler in `main.py`)
- pytest 8.2.2 - Test runner
- pytest-mock 3.14.0 - Mocking support
- pytest-cov 5.0.0 - Coverage reporting
- setuptools (>=45) - Build backend (`pyproject.toml` `[build-system]`)
- setuptools_scm (>=6.2) - Versioning from git tags (writes to `update_whitelist/_version.py`)
- wheel - Wheel distribution support
## Key Dependencies
- `requests` 2.32.3 - HTTP client for fetching current public IP from ipinfo.io (`update_whitelist/ip_fetcher.py`)
- `huaweicloudsdkcore` 3.1.101 - Huawei Cloud SDK core (auth, exceptions, credentials)
- `huaweicloudsdkvpc` 3.1.101 - Huawei Cloud VPC SDK (security group rule CRUD)
- `tencentcloud_sdk_python_common` 3.0.1174 - Tencent Cloud SDK common (auth, exceptions)
- `tencentcloud_sdk_python_vpc` 3.0.1174 - Tencent Cloud VPC SDK (security group policy CRUD)
- `PyYAML` 6.0.1 - YAML config file parsing (`update_whitelist/config/config.py`, `update_whitelist/config/config_loader.py`)
- `pydantic` 2.7.4 - Typed config models with validation
- `setuptools_scm` - Auto-versioning from git tags, writes to `update_whitelist/_version.py`
- Python stdlib `logging` with `TimedRotatingFileHandler` - Application logging (`update_whitelist/logger.py`)
## Configuration
- Configuration is loaded from `config.yaml` at the project root
- Template provided at `config.example.yaml`
- No `.env` file support; secrets are in `config.yaml` (gitignored)
- No environment variable overrides detected
- `pyproject.toml` - Project metadata, dependencies, build system, pytest config
- `.gitlab-ci.yml` - GitLab CI pipeline (test stage with coverage)
- `.github/workflows/test.yml` - GitHub Actions CI pipeline (multi-Python matrix, Codecov upload)
## Platform Requirements
- Python 3.9+
- git (required by `setuptools_scm` for versioning)
- Virtual environment recommended (project uses `venv/`)
- Long-running process (APScheduler blocking scheduler, 180-second intervals)
- Network access to ipinfo.io (IP detection) and cloud provider APIs (Huawei Cloud, Tencent Cloud)
- Write access to working directory for `ip_cache.txt` and `update_whitelist.log` files
- Can run as a standalone process or in a container
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

## Language
## File Header Convention
## Naming Patterns
- Snake_case: `ip_fetcher.py`, `config_loader.py`, `base_cloud_provider.py`
- Test files match source: `test_ip_fetcher.py` tests `ip_fetcher.py`
- PascalCase: `BaseCloudProvider`, `TencentCloud`, `HuaweiCloud`, `Updater`
- Pydantic models also PascalCase: `Allow`, `Rule`, `Region`, `CloudProvider`, `Config`
- snake_case: `get_current_ip()`, `load_cached_ip()`, `cache_ip()`, `has_ip_changed()`
- Private methods not used; no leading underscore convention observed
- snake_case: `access_key`, `secret_key`, `current_ip`, `cached_ip`
- Module-level constants are UPPER_SNAKE_CASE: `IP_CACHE_FILE`
- Used selectively on method signatures in `base_cloud_provider.py` and `updater.py`
- Not used on every function (e.g., `ip_fetcher.py` has no annotations)
- Pydantic models use full typing: `Optional[str]`, `List[Allow]`, `Union[str, int]`
## Code Style
## Import Organization
- No import aliases configured in `pyproject.toml`
- pytest uses `--import-mode=importlib` (configured in `[tool.pytest.ini_options]`)
## Error Handling
## Logging
- Level: `DEBUG` for both console and file handlers
- Console handler: `StreamHandler`
- File handler: `TimedRotatingFileHandler` rotating every 24 hours, 7 backups
- Format: `%(asctime)s - %(levelname)s - %(message)s`
- Log file: `update_whitelist.log` (gitignored)
- `logger.info()`: Normal operation flow (IP changes, security group updates)
- `logger.error()`: Exceptions and failures
## Configuration Conventions
## Git Commit Message Conventions
| Emoji | Type | Purpose |
|-------|------|---------|
| `:sparkles:` | feat | New features |
| `:bug:` | fix | Bug fixes |
| `:memo:` | docs | Documentation changes |
| `:white_check_mark:` | test | Test additions/changes |
| `:ferris_wheel:` | ci | CI/CD changes |
| `:hammer:` | chore | Maintenance tasks |
| `:lipstick:` | style | Code style changes |
- Release commits use format: `Release v0.6.4` (no emoji prefix)
- Revert commits use: `Revert ":emoji: type: description"`
- Descriptions are in Chinese for some commits, English for others
## Documentation Style
## Function Design
- Tuples for multi-value returns: `has_ip_changed()` returns `(bool, Optional[str])`
- `None` used as sentinel/error indicator
- Boolean for success/failure checks
- Cloud providers implement a consistent interface: `get_rules()`, `add_rules()`, `delete_rules()`, `initialize_client()`
- Abstract base class `BaseCloudProvider` enforces this via `@abstractmethod`
## Module Design
## Key File Paths Reference
| Purpose | Path |
|---------|------|
| Entry point | `main.py` |
| Package init | `update_whitelist/__init__.py` |
| Version | `update_whitelist/_version.py` (generated, gitignored) |
| Logger | `update_whitelist/logger.py` |
| IP fetching | `update_whitelist/ip_fetcher.py` |
| Updater logic | `update_whitelist/updater.py` |
| Config models | `update_whitelist/config/config.py` |
| Config loader | `update_whitelist/config/config_loader.py` |
| Base provider | `update_whitelist/cloud_providers/base_cloud_provider.py` |
| Tencent Cloud | `update_whitelist/cloud_providers/tencent_cloud.py` |
| Huawei Cloud | `update_whitelist/cloud_providers/huawei_cloud.py` |
| Config template | `config.example.yaml` |
| Project config | `pyproject.toml` |
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

## Pattern Overview
- Periodic polling via APScheduler (every 180 seconds)
- Strategy pattern for cloud provider implementations (abstract base class with concrete providers)
- Delete-and-recreate approach for security group rules (no in-place updates)
- File-based IP caching for change detection
- Pydantic models for typed configuration from YAML
## Layers
- Purpose: Orchestrates periodic IP checks and triggers updates
- Location: `main.py`
- Contains: APScheduler setup, IP change detection logic, top-level error handling
- Depends on: `update_whitelist.ip_fetcher`, `update_whitelist.updater`, `update_whitelist.config.config`
- Used by: Direct invocation (`python main.py`) or systemd service
- Purpose: Detects the machine's current public IP and compares against cached value
- Location: `update_whitelist/ip_fetcher.py`
- Contains: `get_current_ip()`, `load_cached_ip()`, `cache_ip()` functions
- Depends on: `requests` (HTTP), `ipinfo.io` API, local filesystem for cache
- Used by: `main.py`
- Purpose: Iterates config-driven cloud providers, regions, and security groups; delegates to provider clients
- Location: `update_whitelist/updater.py`
- Contains: `Updater` class with `update_cloud_providers()`, `update_security_group_rules()`, `set_client()`, `fetch_security_group_rules()`
- Depends on: `update_whitelist.cloud_providers.tencent_cloud.TencentCloud`, `update_whitelist.cloud_providers.huawei_cloud.HuaweiCloud`, `update_whitelist.config.config`
- Used by: `main.py`
- Purpose: Abstracts cloud-specific API calls into a uniform interface
- Location: `update_whitelist/cloud_providers/`
- Contains: `BaseCloudProvider` (ABC), `HuaweiCloud`, `TencentCloud` implementations
- Depends on: Vendor SDKs (`huaweicloudsdkcore`, `huaweicloudsdkvpc`, `tencentcloud_sdk_python_*`)
- Used by: `update_whitelist.updater.Updater`
- Purpose: Loads and validates YAML config into typed Pydantic models
- Location: `update_whitelist/config/config.py`, `update_whitelist/config/config_loader.py`
- Contains: Pydantic models (`Config`, `CloudProvider`, `Region`, `Rule`, `Allow`, `IPInfo`) and a legacy `load_config()` helper
- Depends on: `pydantic`, `pyyaml`
- Used by: All layers import the `config` singleton
- Purpose: Provides a module-level logger with console + rotating file handlers
- Location: `update_whitelist/logger.py`
- Contains: `get_logger()` factory function
- Depends on: Python `logging` standard library
- Used by: All modules
## Data Flow
- IP state: Persisted in `ip_cache.txt` (single line file containing last known IP)
- Configuration: Loaded once at module import time from `config.yaml` into a Pydantic `Config` singleton
- Cloud provider client: Recreated per security group via `set_client()` (instance variable on `Updater`)
## Key Abstractions
- Purpose: Defines a uniform interface for cloud security group operations
- Location: `update_whitelist/cloud_providers/base_cloud_provider.py`
- Pattern: Strategy / Template Method -- subclasses implement `initialize_client()`, `get_rules()`, `add_rules()`, `delete_rules()`
- Constructor: Accepts `access_key`, `secret_key`, `region`, and optional `**kwargs`; calls `self.initialize_client()`
- Static helper: `BaseCloudProvider.log(e)` provides cloud-aware error formatting for Huawei and Tencent SDK exceptions
- `HuaweiCloud` at `update_whitelist/cloud_providers/huawei_cloud.py` -- uses Huawei VPC SDK; filters rules by `description.startswith("from Wulihe")` and `direction == "ingress"`
- `TencentCloud` at `update_whitelist/cloud_providers/tencent_cloud.py` -- uses Tencent VPC SDK; filters rules by `PolicyDescription.startswith('from Wulihe')`
- Purpose: Typed access to YAML configuration with validation
- Location: `update_whitelist/config/config.py`
- Hierarchy: `Config` contains optional `CloudProvider` instances (huawei, tencent, aliyun) and `IPInfo`; each `CloudProvider` has `regions: List[Region]`; each `Region` has `rules: List[Rule]`; each `Rule` has `sg` (security group ID) and `allow: List[Allow]`; each `Allow` has `port` and optional `desc`
- Purpose: Orchestration layer that bridges config data and cloud provider implementations
- Location: `update_whitelist/updater.py`
- Pattern: Mediator -- holds a `client` reference that is swapped per provider/region via `set_client()`
- Client selection: Hardcoded `if/elif` dispatch in `set_client()` based on provider name string
## Entry Points
- Location: `main.py`
- Triggers: `python main.py` or systemd service
- Responsibilities: Starts APScheduler `BlockingScheduler` with 180-second interval, runs `check_and_update_ip()` on each tick
- Location: `update_whitelist/config/config.py` (bottom of file, module-level code)
- Triggers: First import of `update_whitelist.config.config`
- Responsibilities: Reads `config.yaml` from project root, parses into `Config` Pydantic model, exposes as module-level `config` variable
## Error Handling
- `main.py` wraps `has_ip_changed()` in broad `except Exception` to catch network failures, returning `(False, None)` so the scheduler loop continues
- `main.py` wraps `check_and_update_ip()` in `except Exception` to ensure one failed update does not kill the scheduler
- `BaseCloudProvider.log()` provides structured error formatting per cloud SDK exception type
- `Updater.fetch_security_group_rules()` catches exceptions and returns `None` (treated as "no existing rules")
- Cloud provider methods (`get_rules`, `delete_rules`) catch SDK-specific exceptions and log via `BaseCloudProvider.log()`
## Cross-Cutting Concerns
- Console stream handler (DEBUG level)
- `TimedRotatingFileHandler` writing to `update_whitelist.log` (rotates every 24 hours, keeps 7 backups)
- Format: `%(asctime)s - %(levelname)s - %(message)s`
- Factory: `get_logger(name=__name__)` in `update_whitelist/logger.py` with handler deduplication (only adds handlers if none exist)
- Primary config file: `config.yaml` (gitignored, contains real credentials)
- Template: `config.example.yaml` (committed, contains placeholder values)
- Module-level singleton: `config` object in `update_whitelist/config/config.py` loaded once at import time
- Legacy helper: `update_whitelist/config/config_loader.py` contains `load_config()` function that is not used by the main flow (superseded by the Pydantic-based config)
<!-- GSD:architecture-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd:quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd:debug` for investigation and bug fixing
- `/gsd:execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->



<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd:profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
