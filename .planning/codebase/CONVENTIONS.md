# Coding Conventions

**Analysis Date:** 2026-04-04

## Language

**Primary:** Python 3.9+ (supports 3.9, 3.10, 3.11, 3.12)

**Style:** No formal linter or formatter is configured. No `.flake8`, `.pylintrc`, `ruff.toml`, `.pre-commit-config.yaml`, or `mypy.ini` present. Code style is consistent but enforced only by convention.

## File Header Convention

Every source file and test file begins with a multi-line docstring containing author and date metadata:

```python
"""
Author: abe<wechat:abrahamgreyson>
Date: 2024/6/13 10:30:13
"""
```

New files MUST include this header. Some files include a third line describing the file's purpose:

```python
"""
Author: abe<wechat:abrahamgreyson>
Date: 2024/6/13 11:22:56

提供日志处理器
"""
```

## Naming Patterns

**Files:**
- Snake_case: `ip_fetcher.py`, `config_loader.py`, `base_cloud_provider.py`
- Test files match source: `test_ip_fetcher.py` tests `ip_fetcher.py`

**Classes:**
- PascalCase: `BaseCloudProvider`, `TencentCloud`, `HuaweiCloud`, `Updater`
- Pydantic models also PascalCase: `Allow`, `Rule`, `Region`, `CloudProvider`, `Config`

**Functions:**
- snake_case: `get_current_ip()`, `load_cached_ip()`, `cache_ip()`, `has_ip_changed()`
- Private methods not used; no leading underscore convention observed

**Variables:**
- snake_case: `access_key`, `secret_key`, `current_ip`, `cached_ip`
- Module-level constants are UPPER_SNAKE_CASE: `IP_CACHE_FILE`

**Type annotations:**
- Used selectively on method signatures in `base_cloud_provider.py` and `updater.py`
- Not used on every function (e.g., `ip_fetcher.py` has no annotations)
- Pydantic models use full typing: `Optional[str]`, `List[Allow]`, `Union[str, int]`

## Code Style

**Formatting:** No auto-formatter configured (no Black, autopep8, or Ruff). Code follows PEP 8 informally.

**Indentation:** 4 spaces.

**Line length:** No strict limit enforced. Lines observed up to ~100 characters.

**String style:** Single quotes for short strings, f-strings for interpolation. Mix of single and double quotes across codebase.

**Trailing statements:** Some functions end with `return None` explicitly (e.g., `updater.py` lines 44, 73, 103). Some functions have trailing `pass` after try/except (e.g., `updater.py` line 57, 60).

**Blank `pass` statements:** Used after abstract method docstrings in `base_cloud_provider.py` (lines 71, 78, 85, 92). This is not needed since the `@abstractmethod` decorator makes the body unreachable, but it is the established pattern.

## Import Organization

**Order (de facto standard, not enforced by tooling):**
1. Standard library: `os`, `json`, `random`, `logging`, `abc`, `typing`
2. Third-party: `requests`, `yaml`, `pydantic`, `APScheduler`, cloud SDKs
3. Local/package: `from .logger import get_logger`, `from .config.config import config`

**Path Aliases:**
- No import aliases configured in `pyproject.toml`
- pytest uses `--import-mode=importlib` (configured in `[tool.pytest.ini_options]`)

**Example from `updater.py`:**
```python
from .cloud_providers.tencent_cloud import TencentCloud
from .cloud_providers.huawei_cloud import HuaweiCloud
from .logger import get_logger
```

**Example from `huawei_cloud.py`:**
```python
from typing import List
from .base_cloud_provider import BaseCloudProvider
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkvpc.v3 import VpcClient, ...
```

## Error Handling

**Strategy:** Broad `except Exception` catch blocks with logging. Specific exceptions are caught in some places.

**Pattern 1 -- Specific then generic catch** (see `main.py` lines 22-32):
```python
try:
    current_ip = get_current_ip()
except (requests.RequestException, requests.Timeout) as e:
    logger.error(f"网络请求失败: {type(e).__name__} - {e}")
    return False, None
except Exception as e:
    logger.error(f"获取 IP 时发生未知错误: {type(e).__name__} - {e}")
    return False, None
```

**Pattern 2 -- Catch and log via static method** (see cloud providers):
```python
try:
    # SDK operation
except exceptions.ClientRequestException as e:
    BaseCloudProvider.log(e)
```

**Pattern 3 -- Catch and return None** (see `updater.py` line 100-102):
```python
except Exception as e:
    logger.error(f"获取 {sg} 安全组规则时出错: {str(e)}")
    return None
```

**NotImplementedError for unimplemented providers** (see `updater.py` line 85):
```python
raise NotImplementedError("阿里云安全组规则获取尚未实现")
```

**Exception logging uses f-strings with Chinese text.** Error messages are bilingual (code identifiers in English, user-facing messages in Chinese).

## Logging

**Framework:** Python `logging` module with custom `get_logger()` wrapper.

**Configuration:** `update_whitelist/logger.py`
- Level: `DEBUG` for both console and file handlers
- Console handler: `StreamHandler`
- File handler: `TimedRotatingFileHandler` rotating every 24 hours, 7 backups
- Format: `%(asctime)s - %(levelname)s - %(message)s`
- Log file: `update_whitelist.log` (gitignored)

**Usage pattern** -- get a module-level logger instance:
```python
from update_whitelist.logger import get_logger
logger = get_logger()
```

**Log levels used:**
- `logger.info()`: Normal operation flow (IP changes, security group updates)
- `logger.error()`: Exceptions and failures

**Note:** Some code also uses `print()` for debug output (e.g., `updater.py` line 98, `tencent_cloud.py` lines 55/77, `huawei_cloud.py` lines 28/50). This is inconsistent with the logging framework.

## Configuration Conventions

**Config file:** `config.yaml` (YAML format, gitignored)
**Template:** `config.example.yaml` (committed to repo)
**Loading:** Pydantic models in `update_whitelist/config/config.py` parse YAML into typed objects.

**Config models** (Pydantic v2 `BaseModel`):
```python
class Config(BaseModel):
    huawei: Optional[CloudProvider] = None
    tencent: Optional[CloudProvider] = None
    aliyun: Optional[CloudProvider] = None
    ipinfo: Optional[IPInfo] = None
```

**Global config singleton:** `update_whitelist/config/config.py` creates a module-level `config` object:
```python
config = Config(**config_data)
```
Import as: `from update_whitelist.config.config import config`

**Environment variables:** No `.env` file. No environment variable loading. All configuration comes from `config.yaml`.

**Version management:** `setuptools_scm` generates `update_whitelist/_version.py` from git tags. Version imported in `__init__.py`:
```python
from ._version import version as __version__
```

## Git Commit Message Conventions

**Format:** Emoji prefix + colon + conventional commit type + colon + description

Pattern: `:emoji: type: description`

**Observed types and their emojis:**
| Emoji | Type | Purpose |
|-------|------|---------|
| `:sparkles:` | feat | New features |
| `:bug:` | fix | Bug fixes |
| `:memo:` | docs | Documentation changes |
| `:white_check_mark:` | test | Test additions/changes |
| `:ferris_wheel:` | ci | CI/CD changes |
| `:hammer:` | chore | Maintenance tasks |
| `:lipstick:` | style | Code style changes |

**Special patterns:**
- Release commits use format: `Release v0.6.4` (no emoji prefix)
- Revert commits use: `Revert ":emoji: type: description"`
- Descriptions are in Chinese for some commits, English for others

**When writing commit messages:** Use the emoji + conventional commit format. Descriptions may be in Chinese or English. Keep descriptions concise.

## Documentation Style

**Module docstrings:** Present on every file (author/date header serves as docstring on some).

**Function docstrings:** Present on most functions in Chinese:
```python
def get_current_ip():
    """
    通过 ipinfo.io 获取当前 IP 地址
    """
```

**Inline comments:** Primarily in Chinese. Used to explain logic flow:
```python
# 遍历每个云服务提供商
for provider_name, provider_config in config.dict().items():
```

**No JSDoc/TSDoc equivalent:** No Sphinx or other documentation generation tool configured.

**README:** `README.md` exists at project root. Contains usage instructions and badges.

## Function Design

**Size:** Functions are small, typically 10-30 lines.

**Parameters:** Mix of typed and untyped. Pydantic models used for complex config structures.

**Return values:**
- Tuples for multi-value returns: `has_ip_changed()` returns `(bool, Optional[str])`
- `None` used as sentinel/error indicator
- Boolean for success/failure checks

**Methods on classes:**
- Cloud providers implement a consistent interface: `get_rules()`, `add_rules()`, `delete_rules()`, `initialize_client()`
- Abstract base class `BaseCloudProvider` enforces this via `@abstractmethod`

## Module Design

**Exports:** Modules export classes and functions directly. No `__all__` used.

**Barrel files:** `update_whitelist/__init__.py` exports version only:
```python
from ._version import version as __version__
```

`update_whitelist/cloud_providers/__init__.py` is empty (just docstring header).

**Circular imports avoided** by having cloud provider implementations import from base, and updater import concrete providers.

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

---

*Convention analysis: 2026-04-04*
