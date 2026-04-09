# Phase 4: Project Identity - Research

**Researched:** 2026-04-06
**Domain:** Python package rename, config schema extension, documentation rewrite
**Confidence:** HIGH

## Summary

Phase 4 is a rename-and-extend phase with three distinct work streams: (1) renaming the Python package directory from `update_whitelist/` to `stay_in_whitelist/` and updating all import paths, CI configs, and build metadata; (2) extracting the hardcoded `"from Wulihe"` rule description prefix into a configurable `rule_prefix` field on the `Config` model with `"from Wulihe"` as the default; and (3) rewriting README.md with updated project identity. The rename is mechanically straightforward but touches 30+ files including every Python source file, every test file, both CI pipelines, pyproject.toml, .gitignore, and config.example.yaml. The rule_prefix change requires threading config through `Updater.set_client()` into `BaseCloudProvider.__init__()` so cloud providers can use it for both writing and filtering rules.

**Primary recommendation:** Execute the rename in three atomic steps: (1) update all string references (imports, docstrings, CI, config) while keeping the directory name, (2) rename the directory, (3) reinstall the package and run tests. This avoids the "half-renamed" state where Python cannot find either package. For rule_prefix, add the field to Config, thread it through Updater to cloud providers, and update tests to verify configurable prefix matching.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Rule description prefix extracted to Config top-level field `rule_prefix`, default value `"from Wulihe"` (Wulihe is company location, stays unchanged)
- **D-02:** dev/prod environment isolation through different config files (e.g., config.dev.yaml with `rule_prefix: "from Wulihe-dev"`), code does not need environment awareness
- **D-03:** `rule_prefix` placed at Config top level, same level as `check_interval`/`paths`, all cloud providers share one prefix. Config key name: `rule_prefix`
- **D-04:** All hardcoded `"from Wulihe"` in huawei_cloud.py and tencent_cloud.py replaced with reading config's `rule_prefix`
- **D-05:** `startswith("from Wulihe")` rule filtering logic changed to `startswith(rule_prefix)`, supporting correct matching after custom prefix
- **D-06:** README.md full rewrite, in Chinese, update badge URLs, directory references, project name, architecture description
- **D-07:** Badge URLs need updating to correct GitHub repo path (currently points to abrahamgreyson/update-whitelist)
- **D-08:** Default log filename in logger.py changed from `update_whitelist.log` to `stay_in_whitelist.log`
- **D-09:** Already-deployed environments unaffected (config.yaml paths.log_file overrides default)
- **D-10:** Existing config.yaml keys (huawei/tencent/ipinfo/timeouts/paths/check_interval etc.) all remain unchanged -- they are cloud provider identifiers, not project identity
- **D-11:** config.example.yaml only updates comment references to old project name (e.g., `update_whitelist.log` to `stay_in_whitelist.log`) and adds `rule_prefix` field documentation
- **D-12:** Directory `update_whitelist/` renamed as a whole to `stay_in_whitelist/`
- **D-13:** pyproject.toml `name` changed to `"stay-in-whitelist"`, setuptools_scm `write_to` changed to `"stay_in_whitelist/_version.py"`
- **D-14:** CI files `--cov=update_whitelist` changed to `--cov=stay_in_whitelist`
- **D-15:** All Python import statements `update_whitelist` replaced with `stay_in_whitelist`
- **D-16:** Test file mocker.patch paths also need synchronized update

### Claude's Discretion
- Package rename execution order (directory first vs imports first)
- How BaseCloudProvider receives rule_prefix (constructor parameter vs class attribute)
- README specific content structure and detail level
- _version.py gitignore entry update
- Whether to add migration guide (notifying deployed users)

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| IDENT-01 | Python package renamed from `update_whitelist` to `stay_in_whitelist` -- all imports and entry points updated | Rename inventory below: 30+ files with import paths, CI configs, build metadata |
| IDENT-02 | All user-facing strings, log messages, and comments updated to "Stay in Whitelist" branding | grep audit found: logger.py hardcoded log filename, docstrings referencing old name, test docstrings |
| IDENT-03 | Config YAML keys updated for new naming (where applicable) | D-10 decision: existing keys remain unchanged; only rule_prefix added and comment references updated |
| IDENT-04 | README.md rewritten to reflect new project name and updated architecture | D-06/D-07: full rewrite in Chinese with updated badges and architecture |
| IDENT-05 | Security group rule description prefix updated from "from Wulihe" to configurable prefix | D-01/D-04/D-05: 4 locations in huawei_cloud.py and tencent_cloud.py, plus 2 test assertions |
| IDENT-06 | Rule description prefix is configurable via config.yaml -- isolates dev/prod environments | D-02/D-03: new top-level Config field, threaded through Updater to cloud providers |
</phase_requirements>
</user_constraints>

## Standard Stack

### Core (unchanged from prior phases)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Pydantic | 2.7.4 | Config model with `rule_prefix` field addition | Already in use for Config BaseModel |
| setuptools_scm | >=6.2 | Auto-versioning, `write_to` path must update | Must change target path in pyproject.toml |
| pytest | 8.2.2 | Test runner for verifying rename | All tests must pass after rename |
| pytest-mock | 3.14.0 | mocker.patch paths must update | All patch targets use old package name |

### Supporting

No new dependencies needed. This phase modifies existing code only.

**Installation:**
No new installs. After rename, reinstall the package:
```bash
pip install -e ".[dev]"
```

## Architecture Patterns

### Recommended Rename Execution Order

**Strategy: "string references first, directory last"** avoids the broken-import state where neither old nor new package can be found.

```
Wave 1: rule_prefix feature (no rename, add field to Config)
Wave 2: string-only updates (docstrings, comments, log filename, CI configs, config.example.yaml)
Wave 3: Python import rename (all .py files update import paths AND directory renamed atomically)
Wave 4: README rewrite (can run in parallel with any wave)
Wave 5: reinstall + test
```

The key insight: Python imports resolve at runtime by directory name. If you rename the directory before updating imports, every import fails. If you update imports before renaming the directory, every import fails. They must happen in the same atomic commit, OR you use a transitional approach.

**Recommended atomic approach:** In a single commit, use `git mv update_whitelist stay_in_whitelist`, then update all import references. Git handles the rename detection.

### Pattern 1: Config Field Addition (rule_prefix)

**What:** Add `rule_prefix: str = "from Wulihe"` to Config model
**When to use:** Per D-03, at Config top level alongside check_interval/paths
**Example:**
```python
class Config(BaseModel):
    huawei: Optional[CloudProvider] = None
    tencent: Optional[CloudProvider] = None
    aliyun: Optional[CloudProvider] = None
    ipinfo: Optional[IPInfo] = None
    timeouts: TimeoutSettings = TimeoutSettings()
    check_interval: int = 600
    paths: Paths = Paths()
    rule_prefix: str = "from Wulihe"  # NEW: per D-01, D-03
```

### Pattern 2: Threading rule_prefix to Cloud Providers

**What:** Pass rule_prefix from config through Updater to cloud provider instances
**When to use:** Per D-04, cloud providers need access to rule_prefix for both add_rules and get_rules
**Recommendation:** Use constructor parameter on BaseCloudProvider (already accepts `**kwargs`).

Two viable approaches from Claude's discretion:

**Approach A: Via **kwargs (recommended -- minimal change)**
```python
# updater.py set_client():
def set_client(self, provider_name, access_key, secret_key, region, rule_prefix):
    if provider_name == 'huawei':
        self.client = HuaweiCloud(access_key, secret_key, region, rule_prefix=rule_prefix)
    elif provider_name == 'tencent':
        self.client = TencentCloud(access_key, secret_key, region, rule_prefix=rule_prefix)

# base_cloud_provider.py already has:
# for key, value in kwargs.items():
#     setattr(self, key, value)
# So self.rule_prefix is automatically set via **kwargs
```

**Approach B: Explicit constructor parameter**
Would require modifying BaseCloudProvider.__init__ signature and all subclass calls. More explicit but more changes.

Approach A is recommended because BaseCloudProvider already stores all kwargs as instance attributes (line 38-39), so adding `rule_prefix=rule_prefix` to the constructor call automatically sets `self.rule_prefix` on the provider instance with zero changes to BaseCloudProvider.

### Anti-Patterns to Avoid

- **Renaming directory without updating imports in same commit:** Breaks CI and all local development until fixed.
- **Forgetting to update mocker.patch paths:** Tests silently pass against wrong mock targets or fail with import errors.
- **Changing config.yaml key names (huawei/tencent/etc.):** Per D-10, these are cloud provider identifiers, not project identity -- they stay unchanged.
- **Removing git history of old filename:** Use `git mv` so git tracks the rename correctly.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Package rename | Custom import hooks or aliases | Direct `git mv` + find-and-replace imports | Simpler, no runtime overhead |
| Config field with default | Validation logic for rule_prefix | Pydantic field with `str` default | Already have the pattern |
| Dev/prod isolation | Environment detection code | Different config files (per D-02) | Simpler, already decided |

## Runtime State Inventory

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| **Stored data** | `ip_cache.txt` -- stores IP string only, no package name references | None -- code edit only (cache path from config) |
| **Stored data** | `update_whitelist.log*` -- log files on disk with old name | None -- new runs create `stay_in_whitelist.log`, old files are inert. Already-deployed systems use `paths.log_file` config override (per D-09) |
| **Stored data** | Cloud provider security group rules -- descriptions contain "from Wulihe" prefix | **Data migration NOT needed** -- existing rules with old prefix will NOT be matched by `startswith(new_prefix)` if prefix changes. However, D-01 keeps default as `"from Wulihe"`, so no migration needed unless user changes prefix. User must understand: changing prefix means old rules become orphaned. |
| **Live service config** | None verified -- no external service config stores the package name. Cloud provider API keys are in config.yaml (gitignored). | None |
| **OS-registered state** | No systemd service files found in repository. README describes manual setup instructions. | None -- deployed instances would need manual update of ExecStart path (README migration note) |
| **Secrets/env vars** | None -- project uses config.yaml for secrets (gitignored). No env var names reference the package. | None |
| **Build artifacts** | `update_whitelist.egg-info/` in project root -- stale after rename | **Code edit:** Delete and let setuptools regenerate via `pip install -e .` |
| **Build artifacts** | `.venv/lib/.../update_whitelist-0.6.8.dev15+...dist-info/` -- installed package in local venv | **Reinstall:** `pip install -e ".[dev]"` after rename |
| **Build artifacts** | `update_whitelist/_version.py` -- generated by setuptools_scm, gitignored but present on disk | **Auto-regenerated** by setuptools_scm on next build. Must update pyproject.toml `write_to` path (per D-13). Must also update .gitignore entry from `update_whitelist/_version.py` to `stay_in_whitelist/_version.py`. |
| **Build artifacts** | `update_whitelist/__pycache__/` and subdirectory caches | **Auto-cleaned** or irrelevant after rename |

**Nothing found in category for:**
- OS-registered state: No systemd service templates in repo, no Task Scheduler, no launchd/plist files.
- Secrets/env vars: No env var names reference the package name.

## Common Pitfalls

### Pitfall 1: Broken Imports During Rename
**What goes wrong:** Python files importing `update_whitelist.*` fail when directory is renamed to `stay_in_whitelist/`, or vice versa.
**Why it happens:** Import statements and directory name must match exactly.
**How to avoid:** Update ALL import references AND rename directory in the SAME commit. Use `git mv` then batch-update imports.
**Warning signs:** `ModuleNotFoundError: No module named 'update_whitelist'` or `ModuleNotFoundError: No module named 'stay_in_whitelist'`

### Pitfall 2: Stale mocker.patch Paths in Tests
**What goes wrong:** Tests pass locally (because old package still installed) but fail in CI (clean install uses new package name).
**Why it happens:** `mocker.patch('update_whitelist.updater.TencentCloud')` patches the old module path. After rename, the live object is at `stay_in_whitelist.updater.TencentCloud`.
**How to avoid:** Grep all test files for `mocker.patch` calls containing `update_whitelist` and update to `stay_in_whitelist`. Specifically found:
- `tests/test_ip_fetcher.py:93` -- `mocker.patch('update_whitelist.ip_fetcher.logger')`
- `tests/test_updater.py:142` -- `mocker.patch('update_whitelist.updater.TencentCloud', ...)`
- `tests/test_updater.py:148` -- `mocker.patch('update_whitelist.updater.HuaweiCloud', ...)`
- `tests/test_updater.py:160` -- `patch('update_whitelist.updater.logger')`
- `tests/test_huawei_cloud.py:92` -- `mocker.patch('update_whitelist.cloud_providers.huawei_cloud.BaseCloudProvider.log')`
**Warning signs:** Tests failing with `AttributeError` or mock assertions not matching.

### Pitfall 3: Orphaned Security Group Rules After Prefix Change
**What goes wrong:** User changes `rule_prefix` in config from `"from Wulihe"` to `"Stay-in-Whitelist"`. Old rules with "from Wulihe" prefix are no longer matched by `startswith("Stay-in-Whitelist")`, so they are never deleted and accumulate.
**Why it happens:** The filter `startswith(rule_prefix)` only matches rules with the CURRENT prefix.
**How to avoid:** Document this behavior clearly. Old rules must be manually cleaned up when changing prefix. Consider adding a log warning on first run with new prefix. This is acceptable per the project's self-use nature.
**Warning signs:** Security group accumulating orphaned rules after prefix change.

### Pitfall 4: setuptools_scm Version File Path Mismatch
**What goes wrong:** After renaming directory, setuptools_scm still writes to `update_whitelist/_version.py` (per pyproject.toml config), but `__init__.py` tries to import from `stay_in_whitelist._version`.
**Why it happens:** pyproject.toml `[tool.setuptools_scm] write_to` is not auto-updated by directory rename.
**How to avoid:** Update `write_to = "stay_in_whitelist/_version.py"` in pyproject.toml BEFORE or in the same commit as directory rename.
**Warning signs:** `ImportError: cannot import name 'version' from 'stay_in_whitelist._version'` or `_version.py` not found.

### Pitfall 5: .gitignore Still References Old Paths
**What goes wrong:** After rename, `stay_in_whitelist/_version.py` and `stay_in_whitelist.log` are no longer gitignored because .gitignore still lists `update_whitelist/_version.py` and `update_whitelist.log*`.
**Why it happens:** .gitignore is not automatically updated by directory rename.
**How to avoid:** Update .gitignore entries to match new package name in same commit.
**Warning signs:** Generated files appearing in `git status` after rename.

### Pitfall 6: Config Docstring References Old Package Name
**What goes wrong:** `config.py` docstring (line 9) says `from update_whitelist.config.config import load_config` -- confusing after rename.
**Why it happens:** Docstrings are not updated by find-and-replace on code logic.
**How to avoid:** Update docstrings in config.py (lines 8-13) and any other module-level docstrings.
**Warning signs:** New developers confused by docstring examples that don't work.

## Code Examples

### Config Model with rule_prefix (after change)
```python
# Source: D-01, D-03 from CONTEXT.md
class Config(BaseModel):
    huawei: Optional[CloudProvider] = None
    tencent: Optional[CloudProvider] = None
    aliyun: Optional[CloudProvider] = None
    ipinfo: Optional[IPInfo] = None
    timeouts: TimeoutSettings = TimeoutSettings()
    check_interval: int = 600
    paths: Paths = Paths()
    rule_prefix: str = "from Wulihe"  # per D-01, D-03
```

### Updater.set_client with rule_prefix
```python
# Source: D-04 from CONTEXT.md
def set_client(self, provider_name, access_key, secret_key, region, rule_prefix):
    if provider_name == 'huawei':
        self.client = HuaweiCloud(access_key, secret_key, region, rule_prefix=rule_prefix)
    elif provider_name == 'tencent':
        self.client = TencentCloud(access_key, secret_key, region, rule_prefix=rule_prefix)
    # ... (aliyun same pattern)

def update_cloud_providers(self, current_ip, config):
    for provider_name in CLOUD_PROVIDER_FIELDS:
        # ...
        self.set_client(provider_name, access_key, secret_key, region, config.rule_prefix)
```

### Huawei Cloud with configurable prefix
```python
# Source: D-04, D-05 from CONTEXT.md
# add_rules:
description=f"{self.rule_prefix}{' - ' + rule['desc'] if rule.get('desc') else ''}"

# get_rules filter:
if getattr(rule, 'description', None) and
   getattr(rule, 'description').startswith(self.rule_prefix) and
   getattr(rule, 'direction', None) and getattr(rule, 'direction') == "ingress"
```

### Tencent Cloud with configurable prefix
```python
# Source: D-04, D-05 from CONTEXT.md
# add_rules:
"PolicyDescription": f"{self.rule_prefix}{' - ' + rule['desc'] if rule.get('desc') else ''}"

# get_rules filter:
filtered_rules = [rule for rule in rules if rule['PolicyDescription'].startswith(self.rule_prefix)]
```

### config.example.yaml with rule_prefix
```yaml
# Optional: rule description prefix for security group rules (default: "from Wulihe")
# Change this for dev/prod isolation, e.g., "from Wulihe-dev" for development
# rule_prefix: "from Wulihe"
```

## Complete Rename Inventory

### Files requiring `update_whitelist` -> `stay_in_whitelist` import path changes:

**Source files (4 files):**
1. `main.py` -- 4 import lines (12-15)
2. `update_whitelist/cloud_providers/base_cloud_provider.py` -- 1 import (line 12)
3. `update_whitelist/cloud_providers/huawei_cloud.py` -- 1 import (line 15)
4. `update_whitelist/cloud_providers/tencent_cloud.py` -- 1 import (line 13)

**Test files (7 files):**
5. `tests/conftest.py` -- 1 import block (line 7)
6. `tests/test_ip_fetcher.py` -- 1 import (line 10) + 1 mocker.patch (line 93)
7. `tests/test_updater.py` -- 3 imports (lines 9-12) + 3 mocker.patch (lines 142, 148, 160)
8. `tests/test_huawei_cloud.py` -- 1 import (line 8) + 1 mocker.patch (line 92)
9. `tests/test_tencent_cloud.py` -- 1 import (line 10)
10. `tests/test_config.py` -- 1 import block (lines 11-20) + 2 docstring references (lines 2, 28) + 1 inline import (line 36)
11. `tests/test_base_cloud_provider.py` -- 2 imports (lines 6-7)

**Config/doc files:**
12. `pyproject.toml` -- line 2 (name), line 44 (write_to)
13. `.github/workflows/test.yml` -- line 43 (--cov=)
14. `.gitlab-ci.yml` -- line 29 (artifact path), line 40 (--cov=)
15. `.gitignore` -- lines 8, 14 (log file pattern, _version.py path)
16. `update_whitelist/config/config.py` -- docstring lines 9, 91
17. `update_whitelist/logger.py` -- line 26 (default log filename)

**Total: 17+ files with ~35 individual change points**

### Files requiring `"from Wulihe"` -> `self.rule_prefix` changes:

1. `update_whitelist/cloud_providers/huawei_cloud.py` -- line 44 (add_rules), line 84 (get_rules filter)
2. `update_whitelist/cloud_providers/tencent_cloud.py` -- line 34 (get_rules filter), line 53 (add_rules)
3. `tests/test_tencent_cloud.py` -- line 28 (mock data), line 41 (assertion) -- update to match configurable prefix

### Directory rename:
- `update_whitelist/` -> `stay_in_whitelist/` (use `git mv`)

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Hardcoded prefix `"from Wulihe"` | Configurable `rule_prefix` field | This phase | Dev/prod isolation possible |
| Package name `update_whitelist` | Package name `stay_in_whitelist` | This phase | Aligns with project directory name |
| Log file `update_whitelist.log` | Default `stay_in_whitelist.log` | This phase | Consistent naming (overridable via config) |

**No deprecated library patterns** in this phase -- all changes are project-internal.

## Open Questions

1. **GitHub repo name**
   - What we know: README badges reference `abrahamgreyson/update-whitelist`. The project is now "Stay in Whitelist".
   - What's unclear: Whether the GitHub repo itself will be renamed to `stay-in-whitelist` or keep `update-whitelist`.
   - Recommendation: Plan README badge URLs to use `abrahamgreyson/stay-in-whitelist` (matching new project name). If the repo name does not change, badge URLs need to point to the actual repo name. Add a note in the plan to confirm the GitHub repo name with the user before updating badges.

2. **Migration guide for deployed users**
   - What we know: This is a self-use tool. Already-deployed instances will break if they pull the rename without updating their config/installation.
   - What's unclear: Whether to include a migration note in README.
   - Recommendation: Include a brief migration section in README noting: (1) reinstall with `pip install -e .`, (2) update systemd ExecStart if using absolute path, (3) old log files are inert, new ones created automatically.

## Environment Availability

Step 2.6: SKIPPED (no external dependencies identified)

This phase modifies only project-internal code, configuration, and documentation. No new external tools, services, or runtimes are required beyond what is already installed (Python 3.12, git, pip, venv). The existing `.venv` will need package reinstallation after rename, which is a standard development workflow step.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.2.2 |
| Config file | pyproject.toml `[tool.pytest.ini_options]` |
| Quick run command | `pytest tests/ -x` |
| Full suite command | `pytest tests/ --cov=stay_in_whitelist --cov-report=term` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| IDENT-01 | Package importable as `stay_in_whitelist` | unit | `python -c "from stay_in_whitelist.config.config import load_config"` | Existing tests updated |
| IDENT-02 | Log filename defaults to `stay_in_whitelist.log` | unit | `pytest tests/test_logger.py -x` (needs new test) | Needs new test |
| IDENT-05 | Cloud providers use configurable rule_prefix | unit | `pytest tests/test_huawei_cloud.py tests/test_tencent_cloud.py -x` | Existing tests updated |
| IDENT-06 | rule_prefix defaults to "from Wulihe" | unit | `pytest tests/test_config.py::TestRulePrefix -x` | Needs new test |

### Sampling Rate
- **Per task commit:** `pytest tests/ -x`
- **Per wave merge:** `pytest tests/ --cov=stay_in_whitelist --cov-report=term`
- **Phase gate:** Full suite green + `python -c "from stay_in_whitelist.config.config import Config; c=Config(); assert c.rule_prefix == 'from Wulihe'"`

### Wave 0 Gaps
- [ ] Add `test_config.py::TestRulePrefix` -- tests rule_prefix default and custom value
- [ ] Update all existing test imports from `update_whitelist` to `stay_in_whitelist`
- [ ] Update all `mocker.patch` paths from `update_whitelist` to `stay_in_whitelist`
- [ ] Update test assertions referencing `"from Wulihe"` to use configurable prefix

## Sources

### Primary (HIGH confidence)
- Source code audit of all 17+ files containing `update_whitelist` references
- Direct reading of `config.py`, `base_cloud_provider.py`, `huawei_cloud.py`, `tencent_cloud.py`, `updater.py`, `logger.py`
- Direct reading of all 7 test files
- Direct reading of `pyproject.toml`, `.github/workflows/test.yml`, `.gitlab-ci.yml`, `.gitignore`
- CONTEXT.md decisions D-01 through D-16 (user-locked)

### Secondary (MEDIUM confidence)
- README.md analysis for badge URL patterns and content structure

### Tertiary (LOW confidence)
- None -- all findings verified by direct source code inspection

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new libraries, all changes are internal
- Architecture: HIGH -- rename is mechanical, rule_prefix threading is well-defined
- Pitfalls: HIGH -- verified by source code grep, all change points identified

**Research date:** 2026-04-06
**Valid until:** 30 days (stable project, no fast-moving dependencies)
