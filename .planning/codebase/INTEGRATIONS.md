# External Integrations

**Analysis Date:** 2026-04-04

## APIs & External Services

**IP Detection:**
- ipinfo.io - Retrieves the current public IP address of the machine
  - SDK/Client: `requests` library (direct HTTP GET)
  - Endpoint: `https://ipinfo.io/ip?token={TOKEN}`
  - Auth: Bearer token passed as URL query parameter
  - Implementation: `update_whitelist/ip_fetcher.py` (`get_current_ip()`)
  - Supports multiple tokens for rotation (random selection from config list)
  - Config location: `config.yaml` -> `ipinfo.tokens` (list of strings)

**Huawei Cloud VPC:**
- Huawei Cloud SDK - Manages security group ingress rules
  - SDK/Client: `huaweicloudsdkcore` + `huaweicloudsdkvpc` (official Python SDK)
  - Auth: AK/SK (Access Key / Secret Key) via `BasicCredentials`
  - API: VPC v3 (`huaweicloudsdkvpc.v3`)
  - Operations:
    - `ListSecurityGroupRulesRequest` - Fetch rules for a security group
    - `DeleteSecurityGroupRuleRequest` - Delete a single rule (iterated)
    - `BatchCreateSecurityGroupRulesRequest` - Batch create ingress rules
  - Region: Configurable per rule set (e.g., `cn-east-3`)
  - Implementation: `update_whitelist/cloud_providers/huawei_cloud.py`
  - Config location: `config.yaml` -> `huawei` section
  - Rule matching: Filters rules by description prefix `"from Wulihe"` and direction `"ingress"`

**Tencent Cloud VPC:**
- Tencent Cloud SDK - Manages security group ingress policies
  - SDK/Client: `tencentcloud_sdk_python_common` + `tencentcloud_sdk_python_vpc` (official Python SDK)
  - Auth: AK/SK via `credential.Credential`
  - API: VPC `2017-03-12` version
  - Operations:
    - `DescribeSecurityGroupPoliciesRequest` - Fetch ingress policies for a security group
    - `DeleteSecurityGroupPoliciesRequest` - Delete policies by `PolicyIndex`
    - `CreateSecurityGroupPoliciesRequest` - Create ingress policies
  - Region: Configurable per rule set (e.g., `ap-guangzhou`)
  - Implementation: `update_whitelist/cloud_providers/tencent_cloud.py`
  - Config location: `config.yaml` -> `tencent` section
  - Rule matching: Filters policies by `PolicyDescription` prefix `"from Wulihe"`

## Data Storage

**Databases:**
- None (no database usage)

**File Storage:**
- Local filesystem only
  - `ip_cache.txt` - Stores the last known public IP address (single line, root directory)
    - Read: `update_whitelist/ip_fetcher.py` (`load_cached_ip()`)
    - Write: `update_whitelist/ip_fetcher.py` (`cache_ip()`)
  - `update_whitelist.log` - Rotating log file (24-hour rotation, 7 backups)
    - Written by `update_whitelist/logger.py` via `TimedRotatingFileHandler`
  - `config.yaml` - Runtime configuration including credentials (gitignored)

**Caching:**
- Local file-based IP cache (`ip_cache.txt`)
- No in-memory or distributed caching

## Authentication & Identity

**Auth Provider:**
- Cloud provider AK/SK pairs (no centralized auth)
  - Huawei Cloud: `access_key` + `secret_key` in `config.yaml` -> `huawei` section
  - Tencent Cloud: `access_key` + `secret_key` in `config.yaml` -> `tencent` section
  - ipinfo.io: Token list in `config.yaml` -> `ipinfo.tokens`

**Implementation:**
- Huawei Cloud: `BasicCredentials(access_key, secret_key)` in `update_whitelist/cloud_providers/huawei_cloud.py` (`initialize_client()`)
- Tencent Cloud: `credential.Credential(access_key, secret_key)` in `update_whitelist/cloud_providers/tencent_cloud.py` (`initialize_client()`)

## Monitoring & Observability

**Error Tracking:**
- None (no external error tracking service)

**Logs:**
- Python stdlib `logging` module
- Dual output: console (`StreamHandler`) + rotating file (`TimedRotatingFileHandler`)
- Log file: `update_whitelist.log`, rotates every 24 hours, keeps 7 backups
- Format: `%(asctime)s - %(levelname)s - %(message)s`
- Implementation: `update_whitelist/logger.py`

## CI/CD & Deployment

**Hosting:**
- Self-hosted or local execution (no PaaS detected)
- Docker-compatible (CI runs in containers)

**CI Pipeline:**
- GitLab CI (`.gitlab-ci.yml`) - Primary CI
  - Uses custom registry image `atomhub.openatom.cn/amd64/python:3.12-rc`
  - Stages: prepare (install deps + build), test (pytest with coverage)
  - Reports: Cobertura XML coverage + JUnit XML test results
- GitHub Actions (`.github/workflows/test.yml`) - Secondary CI
  - Multi-version matrix: Python 3.9, 3.10, 3.11, 3.12
  - Coverage upload to Codecov via `codecov/codecov-action@v3`

## Environment Configuration

**Required config entries in `config.yaml`:**
- `huawei.access_key` - Huawei Cloud access key
- `huawei.secret_key` - Huawei Cloud secret key
- `huawei.regions[]` - List of regions with security group rules
- `tencent.access_key` - Tencent Cloud access key
- `tencent.secret_key` - Tencent Cloud secret key
- `tencent.regions[]` - List of regions with security group rules
- `ipinfo.tokens[]` - List of ipinfo.io API tokens

**Secrets location:**
- All secrets stored in `config.yaml` (gitignored, not committed)
- Template with placeholder values in `config.example.yaml`
- CI uses `cp config.example.yaml config.yaml` (placeholder config for tests)

**Secret references in CI:**
- GitHub Actions: `secrets.CODECOV_TOKEN` for Codecov upload

## Webhooks & Callbacks

**Incoming:**
- None

**Outgoing:**
- None (all API calls are synchronous request/response)

## Security Group Rule Convention

All rules managed by this tool follow a naming convention:
- Description prefix: `"from Wulihe"` (hardcoded in `huawei_cloud.py` and `tencent_cloud.py`)
- Optional suffix: `" - {desc}"` from config (e.g., `"from Wulihe - http"`)
- Protocol: TCP only (hardcoded)
- Direction: Ingress only
- The tool identifies its own rules by matching the `"from Wulihe"` description prefix

---

*Integration audit: 2026-04-04*
