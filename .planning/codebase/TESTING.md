# Testing Patterns

**Analysis Date:** 2026-04-04

## Test Framework

**Runner:**
- pytest ~8.2.2
- Config: `pyproject.toml` `[tool.pytest.ini_options]`

**Assertion Library:**
- pytest built-in assertions (`assert` statements)
- No separate assertion library

**Mocking:**
- pytest-mock ~3.14.0 (provides the `mocker` fixture, a thin wrapper around `unittest.mock`)

**Coverage:**
- pytest-cov ~5.0.0 (wraps coverage.py)

**pytest configuration** (in `pyproject.toml`):
```toml
[tool.pytest.ini_options]
addopts = "--import-mode=importlib"
pythonpath = ["."]
```

**Run Commands:**
```bash
pytest tests/                                    # Run all tests
pytest tests/test_ip_fetcher.py                  # Run specific test file
pytest tests/ -v                                 # Verbose output
pytest tests/ --cov=update_whitelist             # With coverage
pytest tests/ --cov=update_whitelist --cov-report=term   # Coverage with terminal report
pytest tests/ --cov=update_whitelist --cov-report=xml    # XML coverage report
pytest tests/ --junitxml=report.xml              # JUnit XML report
```

## Test File Organization

**Location:** Separate `tests/` directory at project root (not co-located with source).

**Naming:** Files use `test_` prefix matching the source module:
| Source File | Test File |
|------------|-----------|
| `main.py` | `tests/test_main.py` |
| `update_whitelist/updater.py` | `tests/test_updater.py` |
| `update_whitelist/ip_fetcher.py` | `tests/test_ip_fetcher.py` |
| `update_whitelist/cloud_providers/huawei_cloud.py` | `tests/test_huawei_cloud.py` |
| `update_whitelist/cloud_providers/tencent_cloud.py` | `tests/test_tencent_cloud.py` |
| `update_whitelist/cloud_providers/base_cloud_provider.py` | `tests/test_base_cloud_provider.py` |

**Structure:**
```
tests/
  __init__.py
  test_main.py
  test_updater.py
  test_ip_fetcher.py
  test_huawei_cloud.py
  test_tencent_cloud.py
  test_base_cloud_provider.py
```

## Test Structure

**Suite Organization:**
Tests are flat functions (no classes). Each test function uses the `mocker` pytest fixture for mocking. Test names are descriptive and follow the pattern `test_<function>_<scenario>`.

```python
"""
Author: abe<wechat:abrahamgreyson>
Date: 2024/6/25 16:27:03
"""

import pytest
from unittest.mock import patch
from update_whitelist.ip_fetcher import get_current_ip, load_cached_ip, cache_ip


def test_get_current_ip(mocker):
    mock_response = mocker.MagicMock()
    mock_response.status_code = 200
    mock_response.text = '127.0.0.1\n'
    mocker.patch('requests.get', return_value=mock_response)
    assert get_current_ip() == '127.0.0.1'
```

**Patterns:**
- **Setup:** Create mock objects inline at the start of each test function
- **Teardown:** Not needed; mocks are scoped to each test via the `mocker` fixture
- **Assertion:** Direct `assert` statements, no custom matchers

**When adding a new test file:**
1. Create `tests/test_<module>.py`
2. Add the author/date docstring header
3. Import `pytest` and `mocker` (via `pytest` import for the fixture)
4. Import functions/classes under test
5. Write `test_<function>_<scenario>(mocker)` functions

## Mocking

**Framework:** pytest-mock (`mocker` fixture wrapping `unittest.mock`)

**Primary patterns used:**

**Pattern 1 -- Patch a function and set return value:**
```python
def test_get_current_ip(mocker):
    mock_response = mocker.MagicMock()
    mock_response.status_code = 200
    mock_response.text = '127.0.0.1\n'
    mocker.patch('requests.get', return_value=mock_response)
    assert get_current_ip() == '127.0.0.1'
```

**Pattern 2 -- Patch object method on a class:**
```python
def test_update_cloud_providers(mocker):
    mocker.patch.object(Updater, 'set_client')
    mocker.patch.object(Updater, 'update_security_group_rules')
    updater = Updater()
    # ... test logic ...
    updater.set_client.assert_called_once_with('tencent', 'key1', 'secret1', 'region1')
```

**Pattern 3 -- Patch builtins:**
```python
def test_load_cached_ip(mocker):
    mocker.patch('builtins.open', mocker.mock_open(read_data='127.0.0.1\n'))
    mocker.patch('os.path.exists', return_value=True)
    assert load_cached_ip() == '127.0.0.1'
```

**Pattern 4 -- Patch class constructor (for cloud SDK clients):**
```python
def test_initialize_client(mocker):
    mock_vpc_client = mocker.MagicMock()
    mocker.patch('huaweicloudsdkvpc.v3.VpcClient.new_builder', return_value=mock_vpc_client)
    huawei_cloud = HuaweiCloud('access_key', 'secret_key', 'cn-north-1')
    huawei_cloud.client = mock_vpc_client
```

**Pattern 5 -- Manual Mock for client injection:**
```python
def test_fetch_security_group_rules(mocker):
    updater = Updater()
    updater.client = Mock()
    updater.client.get_rules.return_value = ['rule1']
    assert updater.fetch_security_group_rules('sg1') == ['rule1']
```

**Pattern 6 -- Using MagicMock with spec for isinstance checks:**
```python
def test_set_client(mocker):
    mock_tencent_cloud = mocker.MagicMock(spec=TencentCloud)
    mocker.patch('update_whitelist.updater.TencentCloud', return_value=mock_tencent_cloud)
    updater.set_client('tencent', 'key1', 'secret1', 'region1')
    assert isinstance(updater.client, TencentCloud)
```

**Pattern 7 -- Mock abstract base class with concrete stub:**
```python
class MockCloudProvider(BaseCloudProvider):
    def initialize_client(self): pass
    def delete_rules(self, group_id, rules): pass
    def add_rules(self, group_id, rules, ip): pass
    def get_rules(self, group_id): pass

def test_base_cloud_provider(mocker):
    mock_cloud_provider = MockCloudProvider('access_key', 'secret_key', 'region')
```

**What to Mock:**
- External HTTP calls (`requests.get`)
- Cloud SDK client constructors and methods
- File I/O (`builtins.open`, `os.path.exists`)
- Logger calls (when verifying error logging)
- Complex object methods being tested indirectly

**What NOT to Mock:**
- The module/class under test itself (import it directly)
- Simple data transformations and pure logic
- Pydantic model validation (use real models in tests)

## Fixtures and Factories

**Test Data:**
Inline mock data within each test function. No shared fixtures or factory patterns.

```python
config = {
    'tencent': {
        'access_key': 'key1',
        'secret_key': 'secret1',
        'regions': [
            {
                'region': 'region1',
                'rules': [{'sg': 'sg1', 'allow': ['allow1']}]
            }
        ]
    }
}
```

**No conftest.py:** There is no `tests/conftest.py` file. All mocks are created inline in each test.

**Location:** All test data is inline within test functions. No external fixture files.

## Coverage

**Requirements:** No minimum coverage threshold enforced. Coverage is generated but no `fail_under` option is set.

**CI coverage target:** The GitLab CI extracts total coverage from the regex `/TOTAL.*\s+(\d+%)$/` but does not enforce a minimum.

**View Coverage:**
```bash
pytest tests/ --cov=update_whitelist --cov-report=term
pytest tests/ --cov=update_whitelist --cov-report=html    # HTML report in htmlcov/
```

**Coverage scope:** `--cov=update_whitelist` measures coverage of the `update_whitelist` package only. `main.py` is outside the package and its coverage is measured separately via test imports.

**Codecov integration:** GitHub Actions uploads coverage to Codecov using `codecov/codecov-action@v3`.

## Test Types

**Unit Tests:**
- All current tests are unit tests
- Each test isolates a single function or method
- All external dependencies are mocked
- No real network calls, file I/O, or cloud SDK calls

**Integration Tests:**
- Not present. No test verifies the full flow from IP detection through cloud API calls.

**E2E Tests:**
- Not used.

## Common Patterns

**Testing a function with conditional return:**
```python
def test_has_ip_changed(mocker):
    mocker.patch('main.get_current_ip', return_value='1.1.1.1')
    mocker.patch('main.load_cached_ip', return_value='1.1.1.1')
    ip_changed, current_ip = has_ip_changed()
    assert not ip_changed
    assert current_ip == '1.1.1.1'

    mocker.patch('main.get_current_ip', return_value='2.2.2.2')
    ip_changed, current_ip = has_ip_changed()
    assert ip_changed
    assert current_ip == '2.2.2.2'
```

**Testing error handling with exception side_effect:**
```python
def test_fetch_security_group_rules(mocker):
    updater = Updater()
    updater.client = Mock()
    updater.client.get_rules.side_effect = Exception('error')
    with patch('update_whitelist.updater.logger') as mock_logger:
        assert updater.fetch_security_group_rules('sg1') is None
        mock_logger.error.assert_called_once_with('获取 sg1 安全组规则时出错: error')
```

**Testing NotImplementedError:**
```python
def test_set_client(mocker):
    updater = Updater()
    with pytest.raises(ValueError):
        updater.set_client('unsupported', 'key', 'secret', 'region')
```

**Testing a method that calls delete then add (verification order):**
```python
def test_update_security_group_rules_with_existed_rules(mocker):
    updater = Updater()
    updater.client = Mock()
    mocker.patch.object(updater, 'fetch_security_group_rules', return_value=['rule1'])
    updater.update_security_group_rules('sg1', ['allow1'], '127.0.0.1')
    updater.client.delete_rules.assert_called_once_with('sg1', ['rule1'])
    updater.client.add_rules.assert_called_once_with('sg1', ['allow1'], '127.0.0.1')
```

**Testing the "no rules to delete" path:**
```python
def test_update_security_group_rules_without_existed_rules(mocker):
    updater = Updater()
    updater.client = Mock()
    mocker.patch.object(updater, 'fetch_security_group_rules', return_value=[])
    updater.update_security_group_rules('sg1', ['allow1'], '127.0.0.1')
    updater.client.delete_rules.assert_not_called()
    updater.client.add_rules.assert_called_once_with('sg1', ['allow1'], '127.0.0.1')
```

## CI/CD Test Pipeline

### GitHub Actions

**File:** `.github/workflows/test.yml`

**Trigger:** Push and PR to `main` branch.

**Matrix:** Python 3.9, 3.10, 3.11, 3.12 (fail-fast disabled).

**Steps:**
1. Checkout code
2. Set up Python (from matrix)
3. Create virtual environment
4. Install dependencies: `pip install -e ".[dev]"`
5. Prepare config: `cp config.example.yaml config.yaml`
6. Run tests: `pytest tests/ --cov=update_whitelist --junitxml=report.xml --cov-report=xml --cov-report=term`
7. Upload coverage to Codecov
8. Upload test results as artifacts

### GitLab CI

**File:** `.gitlab-ci.yml`

**Image:** `atomhub.openatom.cn/amd64/python:3.12-rc`

**Stages:** `prepare` (install deps) then `test` (run tests).

**Steps:**
1. Install dependencies with venv caching
2. Build package: `python -m build`
3. Install editable: `pip install -e ".[dev]"`
4. Prepare config: `cp config.example.yaml config.yaml`
5. Run tests: `pytest tests/ --cov=update_whitelist --junitxml=report.xml --cov-report=xml --cov-report=term`
6. Extract coverage from Cobertura XML report

**Artifacts:** JUnit XML report and coverage XML report are collected.

## Test Count Summary

| Test File | Tests | What It Tests |
|-----------|-------|---------------|
| `tests/test_main.py` | 2 | `has_ip_changed()`, `check_and_update_ip()` |
| `tests/test_updater.py` | 5 | `Updater.update_cloud_providers()`, `update_security_group_rules()`, `set_client()`, `fetch_security_group_rules()` |
| `tests/test_ip_fetcher.py` | 4 | `get_current_ip()`, `load_cached_ip()`, `cache_ip()` |
| `tests/test_huawei_cloud.py` | 4 | `HuaweiCloud.initialize_client()`, `get_rules()`, `delete_rules()`, `add_rules()` |
| `tests/test_tencent_cloud.py` | 4 | `TencentCloud.initialize_client()`, `get_rules()`, `add_rules()`, `delete_rules()` |
| `tests/test_base_cloud_provider.py` | 1 | `BaseCloudProvider` initialization and `log()` method |
| **Total** | **20** | |

## Areas Without Test Coverage

- `update_whitelist/config/config.py` -- Pydantic config models are not directly tested (loaded as side effect of other tests)
- `update_whitelist/config/config_loader.py` -- `load_config()` function is not tested
- `update_whitelist/logger.py` -- `get_logger()` is not directly tested
- Integration between IP fetcher and updater -- no end-to-end test
- Error paths in cloud providers (e.g., `get_rules()` returning `None` on SDK error)
- `check_and_update_ip()` when IP has NOT changed (only the changed path is tested)

---

*Testing analysis: 2026-04-04*
