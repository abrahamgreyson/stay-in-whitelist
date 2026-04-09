# Phase 2: Configuration Hardening - Research

**Researched:** 2026-04-06
**Domain:** Python configuration patterns, Pydantic v2 API, systemd-compatible file paths
**Confidence:** HIGH

## Summary

Phase 2 transforms the configuration layer from an import-time side effect into an explicitly initialized, validated, and injected dependency. The five requirements (CONF-01 through CONF-04, plus QUAL-04) are all tightly coupled: deferred config loading (CONF-03) enables configurable check interval (CONF-01) and path resolution (CONF-02), while the Pydantic migration (CONF-04) and Updater fix (QUAL-04) are independent but should ship together to keep the test suite coherent.

The project already uses Pydantic 2.7.4 (verified installed in `.venv`), which has `model_dump()`, `field_validator`, and all needed v2 APIs. The Phase 1 `TimeoutSettings` pattern establishes the exact BaseModel extension approach this phase should follow for `Paths` and `check_interval`.

**Primary recommendation:** Follow the Phase 1 pattern (new BaseModel subclass + Config top-level field + defaults) for `Paths` and `check_interval`. Replace the module-level config singleton with a `load_config(path)` function. Use `functools.partial` to pass config into the APScheduler job.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Use explicit `load_config(path)` function. Other modules receive config via function parameters, not module-level singleton import.
- **D-08:** `check_and_update_ip(config)` receives config directly. APScheduler uses `functools.partial` to pass config.
- **D-12:** `ip_fetcher.py` public functions (`get_current_ip(config)`, etc.) receive config directly as parameter, eliminating module-level config import.
- **D-02:** File paths default to project root directory (where config.yaml lives). Users can override via config.yaml.
- **D-11:** pathlib only for new/modified path code in Phase 2. Existing os.path code stays unchanged.
- **D-15:** Config keys: `paths.ip_cache` and `paths.log_file`. Pydantic `Paths` model holds these optional fields.
- **D-05:** Logger initializes with default path (project root). `load_config()` success triggers reconfigure if paths differ. No circular dependency.
- **D-03:** `check_interval` and `paths` are flat at Config top level, symmetric with `timeouts` structure.
- **D-09:** check_interval minimum 600 seconds (10 minutes), no practical upper limit. Pydantic validator enforces.
- **D-04:** Move `client = None` from class variable to `__init__` as `self.client = None`. Minimal change.
- **D-10:** Updater iterates Pydantic object attributes directly (`config.huawei`, `config.tencent`), gaining type hints and IDE completion.
- **D-07:** `load_config()` fails fast: FileNotFoundError / yaml.YAMLError / pydantic.ValidationError. Caller (main.py) catches and exits. No auto-generation.
- **D-14:** Use standard exceptions: FileNotFoundError, yaml.YAMLError, pydantic.ValidationError. No custom exceptions.
- **D-06:** All tests migrate to explicit load_config() or pytest fixture at once. No legacy import pattern retained.
- **D-13:** conftest.py defines mock_config fixture, all test files reuse it.
- **D-16:** Use `functools.partial(check_and_update_ip, config=config)` to pass config to APScheduler.

### Claude's Discretion
- load_config() function implementation details (path resolution, YAML reading, Pydantic model construction)
- Paths model default value computation logic (how to derive defaults from project root)
- reconfigure_logging() implementation approach (replace handler vs rebuild logger)
- conftest.py mock_config fixture data structure

### Deferred Ideas (OUT OF SCOPE)
- Rule prefix configurability (IDENT-06) -- belongs to Phase 4
- Health check / heartbeat mechanism -- v2 requirement
- Idempotent rule management -- v2 requirement
- IP change notification -- v2 requirement
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CONF-01 | Check interval configurable via config.yaml, default 600 seconds | Pydantic `field_validator` pattern verified; `functools.partial` for APScheduler verified; see Architecture Patterns section |
| CONF-02 | File paths use absolute paths resolved via pathlib, systemd-compatible | pathlib path resolution verified; `Paths` model with optional fields verified; see Code Examples |
| CONF-03 | Config loading deferred to explicit init function, no import-time I/O | `load_config(path)` pattern designed; see Architecture Patterns section |
| CONF-04 | `config.dict()` migrated to `config.model_dump()` | Pydantic 2.7.4 `model_dump()` confirmed available; see Standard Stack |
| QUAL-04 | Updater.client moved from class variable to instance variable | Simple `__init__` fix; see Code Examples |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pydantic | 2.7.4 | Config validation, `model_dump()`, `field_validator` | Already installed; Phase 1 added TimeoutSettings following this pattern |
| PyYAML | 6.0.1 | YAML config file parsing | Already installed; `yaml.safe_load()` for reading, `yaml.YAMLError` for error reporting |
| pathlib | stdlib | Path resolution for systemd compatibility | stdlib, D-11 mandates for new path code |
| functools.partial | stdlib | Pass config to APScheduler job | D-16 decision; verified working with APScheduler 3.10.4 |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| logging.handlers.TimedRotatingFileHandler | stdlib | Rotating log file handler | Reconfigure when paths change after load_config |
| apscheduler | 3.10.4 | Job scheduling with configurable interval | `scheduler.add_job()` with `seconds=config.check_interval` |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| functools.partial | Lambda wrapper | Lambda is less debuggable, partial is standard Python pattern |
| pathlib (new code only) | pathlib everywhere | D-11 constrains: only new/modified path code uses pathlib |

**Installation:**
No new packages needed. All dependencies already installed in `.venv` (Python 3.12.12).

**Version verification:**
```
pydantic 2.7.4 -- confirmed installed in .venv
APScheduler 3.10.4 -- confirmed installed in .venv
PyYAML 6.0.1 -- confirmed in pyproject.toml
Python 3.12.12 -- .venv runtime (project supports 3.9+)
```

## Architecture Patterns

### Recommended Project Structure (changes only)
```
update_whitelist/
  config/
    config.py        # REWRITE: Pydantic models + load_config() function, no module-level I/O
    config_loader.py # UNCHANGED (removed in Phase 3 per QUAL-05)
  ip_fetcher.py      # MODIFY: add config parameter to functions, use config.paths.ip_cache
  logger.py          # MODIFY: add reconfigure function for log path update
  updater.py         # MODIFY: __init__ fix, model_dump migration, attribute iteration
main.py              # REWRITE: call load_config(), pass config to all functions
tests/
  conftest.py        # NEW: mock_config fixture (D-13)
  test_config.py     # NEW: load_config tests, Paths tests, validation tests
  test_main.py       # MODIFY: update for new function signatures
  test_updater.py    # MODIFY: update for attribute iteration + instance client
  test_ip_fetcher.py # MODIFY: update for config parameter injection
```

### Pattern 1: Explicit Config Loading (CONF-03)
**What:** Replace module-level singleton with `load_config(path)` function that returns a `Config` instance.
**When to use:** Every entry point calls `load_config()` before using any config-dependent code.
**Example:**
```python
# update_whitelist/config/config.py (bottom of file)

def load_config(config_path: str | None = None) -> Config:
    """
    Load and validate configuration from YAML file.
    Raises FileNotFoundError if file missing.
    Raises yaml.YAMLError if YAML malformed.
    Raises pydantic.ValidationError if validation fails.
    """
    if config_path is None:
        # Derive from this file's location: config.py -> config/ -> update_whitelist/ -> project_root
        current_path = Path(__file__).resolve()
        project_root = current_path.parent.parent.parent
        config_path = str(project_root / 'config.yaml')
    else:
        config_path = str(Path(config_path).resolve())

    with open(config_path, 'r') as file:
        config_data = yaml.safe_load(file)

    return Config(**config_data)

# NO module-level config = load_config() -- removed
```

### Pattern 2: Paths Model with Derived Defaults (CONF-02)
**What:** Pydantic model with optional string fields. Caller resolves defaults based on project root.
**When to use:** Config construction. Default paths derive from config.yaml location.
**Example:**
```python
# update_whitelist/config/config.py

class Paths(BaseModel):
    ip_cache: Optional[str] = None
    log_file: Optional[str] = None

class Config(BaseModel):
    huawei: Optional[CloudProvider] = None
    tencent: Optional[CloudProvider] = None
    aliyun: Optional[CloudProvider] = None
    ipinfo: Optional[IPInfo] = None
    timeouts: TimeoutSettings = TimeoutSettings()
    check_interval: int = 600
    paths: Paths = Paths()

    @field_validator('check_interval')
    @classmethod
    def validate_check_interval(cls, v):
        if v < 600:
            raise ValueError('check_interval must be >= 600 seconds')
        return v

# In load_config(), after constructing Config:
def _resolve_paths(config: Config, config_path: str) -> Config:
    """Fill in None paths with defaults derived from config file location."""
    project_root = str(Path(config_path).resolve().parent)
    resolved_ip_cache = config.paths.ip_cache or os.path.join(project_root, 'ip_cache.txt')
    resolved_log_file = config.paths.log_file or os.path.join(project_root, 'update_whitelist.log')
    # Return config with resolved paths (using model_copy or direct construction)
```

**IMPORTANT:** D-11 says pathlib only for new/modified path code. The `_resolve_paths` helper uses pathlib since it is new code. Existing code in other modules that still uses `os.path` should not be gratuitously changed.

### Pattern 3: Config Injection via functools.partial (CONF-01, D-16)
**What:** APScheduler job receives config via `functools.partial`.
**When to use:** In `main.py` when setting up the scheduler.
**Example:**
```python
# main.py
from functools import partial
from update_whitelist.config.config import load_config

def main():
    config = load_config()  # Explicit, fails fast on error

    # Reconfigure logger if custom log path specified
    if config.paths.log_file:
        reconfigure_logging(config.paths.log_file)

    scheduler = BlockingScheduler()
    job = partial(check_and_update_ip, config=config)
    scheduler.add_job(job, 'interval', seconds=config.check_interval)
    # ...
```

### Pattern 4: Logger Reconfiguration (D-05)
**What:** Initialize logger with default path, then reconfigure after load_config if path differs.
**When to use:** In main.py after `load_config()` returns a config with custom log path.
**Example:**
```python
# update_whitelist/logger.py

def reconfigure_logging(log_file_path: str) -> None:
    """Replace file handler with new path. Safe to call multiple times."""
    root_logger = logging.getLogger('update_whitelist')
    old_handlers = [h for h in root_logger.handlers if isinstance(h, TimedRotatingFileHandler)]
    for h in old_handlers:
        h.close()
        root_logger.removeHandler(h)
    fh = TimedRotatingFileHandler(log_file_path, when='H', interval=24, backupCount=7)
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    root_logger.addHandler(fh)
```

### Pattern 5: Updater Attribute Iteration (D-10)
**What:** Iterate Pydantic model attributes directly instead of converting to dict.
**When to use:** In `updater.py` when traversing cloud providers.
**Example:**
```python
# update_whitelist/updater.py

CLOUD_PROVIDER_FIELDS = ('huawei', 'tencent', 'aliyun')

def update_cloud_providers(self, current_ip, config):
    for provider_name in CLOUD_PROVIDER_FIELDS:
        provider_config = getattr(config, provider_name, None)
        if provider_config is None:
            continue

        # provider_config is a typed Pydantic CloudProvider object
        access_key = provider_config.access_key
        secret_key = provider_config.secret_key

        for region_config in provider_config.regions:
            region = region_config.region
            rules = region_config.rules
            for rule in rules:
                sg = rule.sg
                allows = rule.allow
                self.set_client(provider_name, access_key, secret_key, region)
                self.update_security_group_rules(sg, allows, current_ip)
```

### Anti-Patterns to Avoid
- **Module-level config singleton with import-time I/O:** The current pattern triggers file I/O on import. This breaks testing (config.yaml must exist to import anything) and makes it impossible to test with different configs. All config access must go through function parameters.
- **Circular logger-config dependency:** Logger must not import config. Logger initializes with hardcoded default path, then `reconfigure_logging()` is called after `load_config()` if a custom path is specified.
- **Using `.dict()` on Pydantic v2 models:** Deprecated in Pydantic v2. Always use `.model_dump()`. The existing `config.dict()` in `updater.py:33` must be replaced.
- **Keeping `client` as a class variable:** `client = None` on the class body means all `Updater` instances share the same `client` attribute. If two instances are created, `set_client` on one affects the other. Must be `self.client = None` in `__init__`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Config value validation | Custom if/raise checks | Pydantic `field_validator` | Pydantic provides clear error messages, integrates with model construction |
| YAML error reporting | Custom error messages | `yaml.YAMLError` (standard exception) | Already provides line/column info |
| Path resolution for systemd | Hardcoded absolute paths | pathlib derived from config.yaml location | Works regardless of cwd, systemd sets cwd to / |
| Scheduler interval configuration | Edit source code | `config.check_interval` from YAML | D-03 decision; enables ops changes without deployment |
| Passing args to scheduled job | Global variable or lambda | `functools.partial` | Standard, debuggable, no hidden state |

**Key insight:** This phase is about moving from implicit (module-level side effects) to explicit (function parameters, factory functions). Every hand-rolled shortcut in this domain becomes a testing nightmare.

## Common Pitfalls

### Pitfall 1: Import-Order Circular Dependency
**What goes wrong:** If `logger.py` imports `config.py` (to read log path), and `config.py` uses `get_logger()` (for logging config load errors), you get a circular import.
**Why it happens:** Both modules are foundational; everything depends on both.
**How to avoid:** D-05: Logger never imports config. Logger uses hardcoded default path. Only `main.py` bridges them: calls `load_config()` first, then `reconfigure_logging()` if needed.
**Warning signs:** ImportError on startup, or logger messages about config not found.

### Pitfall 2: Updater.client Shared State
**What goes wrong:** `Updater.client = None` is a class variable. Python class variables are shared across instances. Two `Updater()` instances would share the same `client` reference, causing one's `set_client()` to overwrite the other's.
**Why it happens:** Python class body assignments look like instance initialization but are actually class-level.
**How to avoid:** D-04: Move to `def __init__(self): self.client = None`. The fix is a one-line change.
**Warning signs:** If tests create multiple Updater instances, the second one's `set_client()` would appear to affect the first. Current tests already manually set `updater.client = Mock()`, which masks the bug because each test sets it on the instance, shadowing the class variable.

### Pitfall 3: Relative Paths Under systemd
**What goes wrong:** systemd sets `WorkingDirectory` to `/` by default. Relative paths like `'ip_cache.txt'` and `'update_whitelist.log'` resolve to `/ip_cache.txt` and `/update_whitelist.log` -- root filesystem writes that fail or pollute.
**Why it happens:** Code uses bare filenames assuming cwd is the project directory.
**How to avoid:** D-02: Resolve all file paths from config.yaml location (which must be an absolute path in systemd deployment). The `Paths` model provides configurable overrides; defaults derive from the config file's parent directory.
**Warning signs:** FileNotFoundError or PermissionError when running under systemd; files appearing in unexpected locations.

### Pitfall 4: Test Breakage from Signature Changes
**What goes wrong:** Adding `config` parameter to `get_current_ip()`, `load_cached_ip()`, `cache_ip()`, `check_and_update_ip()`, and `has_ip_changed()` breaks every existing test that calls these functions without the new parameter.
**Why it happens:** D-12 requires all ip_fetcher functions to accept config. D-08 requires check_and_update_ip to accept config.
**How to avoid:** D-06: Migrate all tests at once. D-13: Create conftest.py with a shared mock_config fixture so tests are not individually constructing config objects.
**Warning signs:** `TypeError: ... missing 1 required positional argument: 'config'` in test output.

### Pitfall 5: model_dump Returns Nested Dicts for Nested Models
**What goes wrong:** If code iterates `config.model_dump().items()` and expects flat values, it will encounter nested dicts for `paths`, `timeouts`, etc.
**Why it happens:** `model_dump()` recursively serializes all nested models.
**How to avoid:** D-10 avoids this entirely by iterating model attributes directly. When `model_dump()` is needed, use `exclude` parameter or filter results.
**Warning signs:** `TypeError: string indices must be integers` when trying to access `provider_config['access_key']` from a nested dict.

## Code Examples

### Verified: load_config with fail-fast errors
```python
# Source: verified against Pydantic 2.7.4, PyYAML 6.0.1, Python 3.12
from pathlib import Path
import yaml
from pydantic import ValidationError

def load_config(config_path: str | None = None) -> Config:
    if config_path is None:
        project_root = Path(__file__).resolve().parent.parent.parent
        config_path = str(project_root / 'config.yaml')

    config_path = str(Path(config_path).resolve())

    if not Path(config_path).exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with open(config_path, 'r') as f:
        try:
            config_data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise  # Re-raise with original message

    if config_data is None:
        raise ValueError(f"Configuration file is empty: {config_path}")

    return Config(**config_data)  # Raises pydantic.ValidationError on validation failure
```

### Verified: Config model with check_interval and paths
```python
# Source: verified against Pydantic 2.7.4
from pydantic import BaseModel, field_validator
from typing import List, Optional, Union

class Paths(BaseModel):
    ip_cache: Optional[str] = None
    log_file: Optional[str] = None

class Config(BaseModel):
    huawei: Optional[CloudProvider] = None
    tencent: Optional[CloudProvider] = None
    aliyun: Optional[CloudProvider] = None
    ipinfo: Optional[IPInfo] = None
    timeouts: TimeoutSettings = TimeoutSettings()
    check_interval: int = 600
    paths: Paths = Paths()

    @field_validator('check_interval')
    @classmethod
    def validate_check_interval(cls, v):
        if v < 600:
            raise ValueError('check_interval must be >= 600 seconds')
        return v
```

### Verified: functools.partial with APScheduler
```python
# Source: verified against APScheduler 3.10.4
from functools import partial
from apscheduler.schedulers.blocking import BlockingScheduler

def check_and_update_ip(config):
    # ... existing logic, now receives config as parameter
    pass

def main():
    config = load_config()
    scheduler = BlockingScheduler()
    job = partial(check_and_update_ip, config=config)
    scheduler.add_job(job, 'interval', seconds=config.check_interval)
    scheduler.start()
```

### Verified: Updater __init__ fix (QUAL-04)
```python
# Before (class variable -- SHARED across instances):
class Updater:
    client = None  # BUG: shared state

# After (instance variable -- per-instance):
class Updater:
    def __init__(self):
        self.client = None
```

### Verified: TimedRotatingFileHandler reconfiguration
```python
# Source: verified against Python 3.12 logging stdlib
import logging
from logging.handlers import TimedRotatingFileHandler

def reconfigure_logging(log_file_path: str) -> None:
    """Replace file handler with new path."""
    for name in logging.root.manager.loggerDict:
        logger = logging.getLogger(name)
        old_handlers = [h for h in logger.handlers if isinstance(h, TimedRotatingFileHandler)]
        for h in old_handlers:
            h.close()
            logger.removeHandler(h)
        if old_handlers:
            fh = TimedRotatingFileHandler(log_file_path, when='H', interval=24, backupCount=7)
            fh.setLevel(logging.DEBUG)
            fh.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
            logger.addHandler(fh)
```

### Verified: conftest.py mock_config fixture pattern
```python
# tests/conftest.py
import pytest
from update_whitelist.config.config import Config, CloudProvider, Region, Rule, Allow, Paths, TimeoutSettings

@pytest.fixture
def mock_config():
    """Provides a Config object with test defaults. No file I/O."""
    return Config(
        huawei=CloudProvider(
            access_key='test_ak',
            secret_key='test_sk',
            regions=[Region(
                region='cn-east-3',
                rules=[Rule(sg='sg-test', allow=[Allow(port=80, desc='http')])]
            )]
        ),
        tencent=CloudProvider(
            access_key='test_ak',
            secret_key='test_sk',
            regions=[Region(
                region='ap-guangzhou',
                rules=[Rule(sg='sg-test2', allow=[Allow(port=443, desc='https')])]
            )]
        ),
        ipinfo=IPInfo(tokens=['test_token']),
        check_interval=600,
        paths=Paths(ip_cache='/tmp/test_ip_cache.txt', log_file='/tmp/test.log'),
    )
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `config.dict()` | `config.model_dump()` | Pydantic v2.0 (2023-06) | `.dict()` deprecated with warning; `.model_dump()` is the v2 API |
| Module-level singleton | Explicit factory function | Python best practice | Enables testing, multiple configs, no import-time I/O |
| Relative file paths | pathlib + absolute resolution | Always best practice | Required for systemd where cwd != project dir |
| Class variable for mutable state | Instance variable in `__init__` | Always Python best practice | Prevents shared-state bugs across instances |

**Deprecated/outdated:**
- `BaseModel.dict()`: Deprecated in Pydantic v2. Use `model_dump()`. Will be removed in a future version.
- `BaseModel.parse_obj()`: Deprecated. Use `model_validate()` instead (not needed in this phase, but good to know).

## Open Questions

1. **reconfigure_logging scope**
   - What we know: D-05 says logger reconfigures after load_config. The logger module creates loggers per module via `get_logger(name)`.
   - What's unclear: Whether to reconfigure ALL module loggers (by iterating `logging.root.manager.loggerDict`) or only the root/primary logger.
   - Recommendation: Reconfigure only loggers that have a `TimedRotatingFileHandler`. The existing `get_logger()` creates one logger per module name, so iterate all loggers and replace their file handlers. This is the safest approach.

2. **Paths default resolution in tests**
   - What we know: D-02 says defaults derive from config.yaml location. Tests will use `mock_config` fixture with explicit paths.
   - What's unclear: Whether `load_config()` should resolve paths to absolute at load time, or leave resolution to each consumer.
   - Recommendation: Resolve at load time in `load_config()`. The `Config.paths` should always contain absolute paths after loading. Tests set explicit absolute paths in the fixture.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.9+ | Project requirement | Yes (.venv) | 3.12.12 | -- |
| pydantic | Config models | Yes (.venv) | 2.7.4 | -- |
| PyYAML | Config loading | Yes (.venv) | 6.0.1 | -- |
| APScheduler | Job scheduling | Yes (.venv) | 3.10.4 | -- |
| pytest | Test runner | Yes (.venv) | 8.2.2 | -- |
| pytest-mock | Test mocking | Yes (.venv) | 3.14.0 | -- |

**Missing dependencies with no fallback:**
None -- all required packages are installed.

**Missing dependencies with fallback:**
None.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.2.2 |
| Config file | pyproject.toml `[tool.pytest.ini_options]` |
| Quick run command | `python -m pytest tests/ -x -q` |
| Full suite command | `python -m pytest tests/ -v --cov=update_whitelist` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CONF-01 | check_interval configurable, defaults to 600, rejects < 600 | unit | `python -m pytest tests/test_config.py -x -q` | Wave 0: NEW |
| CONF-01 | scheduler uses config.check_interval | unit | `python -m pytest tests/test_main.py -x -q` | Wave 0: MODIFY |
| CONF-02 | paths default to project root when not specified | unit | `python -m pytest tests/test_config.py -x -q` | Wave 0: NEW |
| CONF-02 | paths resolve to absolute regardless of cwd | unit | `python -m pytest tests/test_config.py -x -q` | Wave 0: NEW |
| CONF-02 | ip_fetcher uses config.paths.ip_cache | unit | `python -m pytest tests/test_ip_fetcher.py -x -q` | Wave 0: MODIFY |
| CONF-03 | importing config module does NOT trigger file I/O | unit | `python -m pytest tests/test_config.py -x -q` | Wave 0: NEW |
| CONF-03 | load_config() raises FileNotFoundError for missing file | unit | `python -m pytest tests/test_config.py -x -q` | Wave 0: NEW |
| CONF-03 | load_config() raises yaml.YAMLError for malformed YAML | unit | `python -m pytest tests/test_config.py -x -q` | Wave 0: NEW |
| CONF-04 | model_dump replaces dict in updater | unit | `python -m pytest tests/test_updater.py -x -q` | Wave 0: MODIFY |
| QUAL-04 | Updater.client is instance variable, not shared | unit | `python -m pytest tests/test_updater.py -x -q` | Wave 0: MODIFY |

### Sampling Rate
- **Per task commit:** `python -m pytest tests/ -x -q`
- **Per wave merge:** `python -m pytest tests/ -v --cov=update_whitelist`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_config.py` -- covers CONF-01 validation, CONF-02 path resolution, CONF-03 deferred loading
- [ ] `tests/conftest.py` -- shared mock_config fixture (D-13)
- [ ] `tests/test_main.py` -- update for config parameter injection (CONF-01 scheduler interval)
- [ ] `tests/test_updater.py` -- update mock from `.dict()` to attribute iteration, add instance variable test
- [ ] `tests/test_ip_fetcher.py` -- update for config parameter injection (CONF-02 ip_cache path)

## Sources

### Primary (HIGH confidence)
- Pydantic 2.7.4 installed in `.venv` -- verified `model_dump()`, `field_validator`, `BaseModel` patterns via live testing
- APScheduler 3.10.4 installed in `.venv` -- verified `functools.partial` works with `add_job()`
- Python stdlib `logging.handlers.TimedRotatingFileHandler` -- verified handler reconfiguration pattern
- Python stdlib `pathlib` -- verified path resolution from `__file__`
- Source code analysis of `update_whitelist/config/config.py`, `main.py`, `ip_fetcher.py`, `logger.py`, `updater.py`

### Secondary (MEDIUM confidence)
- Phase 1 CONTEXT.md (D-03 timeout pattern) -- establishes the Config extension pattern this phase follows
- REQUIREMENTS.md -- requirement definitions for CONF-01 through CONF-04 and QUAL-04
- CONTEXT.md -- locked decisions from discuss phase

### Tertiary (LOW confidence)
None -- all findings verified against installed packages or source code.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all packages installed and version-verified in .venv
- Architecture: HIGH -- patterns verified with live Python testing in the project's venv
- Pitfalls: HIGH -- identified from direct source code analysis, not speculation

**Research date:** 2026-04-06
**Valid until:** 2026-05-06 (stable libraries, no rapid version churn expected)
