# Technology Stack

**Analysis Date:** 2026-04-04

## Languages

**Primary:**
- Python 3.9+ - All source code, supports 3.9, 3.10, 3.11, 3.12 (declared in `pyproject.toml`)

**Secondary:**
- YAML - Configuration files (`config.yaml`, `config.example.yaml`)
- Shell (CI) - GitLab CI and GitHub Actions pipeline definitions

## Runtime

**Environment:**
- Python >=3.9 (enforced via `requires-python` in `pyproject.toml`)
- GitLab CI uses `atomhub.openatom.cn/amd64/python:3.12-rc` Docker image
- GitHub Actions uses `actions/setup-python@v4` with matrix: 3.9, 3.10, 3.11, 3.12

**Package Manager:**
- pip with `venv` for virtual environments
- `pyproject.toml` as the single source of truth for dependencies (PEP 621)
- No lockfile present (no `requirements.lock` or `poetry.lock`)

## Frameworks

**Core:**
- Pydantic 2.7.4 - Configuration validation and serialization via `BaseModel` (used in `update_whitelist/config/config.py`)
- APScheduler 3.10.4 - Scheduling periodic IP checks (blocking scheduler in `main.py`)

**Testing:**
- pytest 8.2.2 - Test runner
- pytest-mock 3.14.0 - Mocking support
- pytest-cov 5.0.0 - Coverage reporting

**Build/Dev:**
- setuptools (>=45) - Build backend (`pyproject.toml` `[build-system]`)
- setuptools_scm (>=6.2) - Versioning from git tags (writes to `update_whitelist/_version.py`)
- wheel - Wheel distribution support

## Key Dependencies

**Critical:**
- `requests` 2.32.3 - HTTP client for fetching current public IP from ipinfo.io (`update_whitelist/ip_fetcher.py`)
- `huaweicloudsdkcore` 3.1.101 - Huawei Cloud SDK core (auth, exceptions, credentials)
- `huaweicloudsdkvpc` 3.1.101 - Huawei Cloud VPC SDK (security group rule CRUD)
- `tencentcloud_sdk_python_common` 3.0.1174 - Tencent Cloud SDK common (auth, exceptions)
- `tencentcloud_sdk_python_vpc` 3.0.1174 - Tencent Cloud VPC SDK (security group policy CRUD)
- `PyYAML` 6.0.1 - YAML config file parsing (`update_whitelist/config/config.py`, `update_whitelist/config/config_loader.py`)
- `pydantic` 2.7.4 - Typed config models with validation

**Infrastructure:**
- `setuptools_scm` - Auto-versioning from git tags, writes to `update_whitelist/_version.py`
- Python stdlib `logging` with `TimedRotatingFileHandler` - Application logging (`update_whitelist/logger.py`)

## Configuration

**Environment:**
- Configuration is loaded from `config.yaml` at the project root
- Template provided at `config.example.yaml`
- No `.env` file support; secrets are in `config.yaml` (gitignored)
- No environment variable overrides detected

**Build:**
- `pyproject.toml` - Project metadata, dependencies, build system, pytest config
- `.gitlab-ci.yml` - GitLab CI pipeline (test stage with coverage)
- `.github/workflows/test.yml` - GitHub Actions CI pipeline (multi-Python matrix, Codecov upload)

## Platform Requirements

**Development:**
- Python 3.9+
- git (required by `setuptools_scm` for versioning)
- Virtual environment recommended (project uses `venv/`)

**Production:**
- Long-running process (APScheduler blocking scheduler, 180-second intervals)
- Network access to ipinfo.io (IP detection) and cloud provider APIs (Huawei Cloud, Tencent Cloud)
- Write access to working directory for `ip_cache.txt` and `update_whitelist.log` files
- Can run as a standalone process or in a container

---

*Stack analysis: 2026-04-04*
