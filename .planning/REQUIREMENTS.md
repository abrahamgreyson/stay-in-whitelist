# Requirements

**Project:** Stay in Whitelist
**Created:** 2026-04-05

## v1 Requirements

### Core Reliability (CRITICAL)

- [x] **REL-01**: All network requests (IP detection + cloud API) have configurable timeouts — prevents scheduler hangs
- [x] **REL-02**: Multi-provider IP detection with automatic fallback chain (ipinfo → icanhazip → ipify → ifconfig.me) — prevents single-provider outage
- [x] **REL-03**: IP format validation using `ipaddress.ip_address()` before any cloud API call — prevents garbage in security group rules
- [x] **REL-04**: Cloud API calls have retry with exponential backoff (tenacity library) — handles rate limits and transient failures
- [x] **REL-05**: Security group rule update order changed to add-before-delete — prevents lockout during update failures
- [x] **REL-06**: `get_rules()` returns empty list `[]` on error instead of `None` — prevents rule accumulation bug
- [x] **REL-07**: `huawei_cloud.add_rules()` wrapped in try/except — prevents unhandled exception crashing scheduler

### Configuration (CONFIG)

- [x] **CONF-01**: Check interval is configurable via `config.yaml` with default of 600 seconds (10 minutes)
- [x] **CONF-02**: File paths (ip_cache, log file) use absolute paths resolved via `pathlib` — fixes systemd deployment
- [x] **CONF-03**: Config loading deferred to explicit initialization function (not module-level side effect) — improves testability
- [x] **CONF-04**: `config.dict()` migrated to `config.model_dump()` — Pydantic v2 API compatibility

### Code Quality (QUAL)

- [x] **QUAL-01**: All `print()` calls replaced with `logger` calls — ensures all output goes through log rotation
- [x] **QUAL-02**: Logger does not expose API tokens in log messages — prevents credential leakage
- [x] **QUAL-03**: Commented-out dead code in `updater.py` removed — reduces confusion
- [x] **QUAL-04**: `Updater.client` moved from class variable to instance variable — fixes latent shared state bug
- [x] **QUAL-05**: Unused `config_loader.py` module removed — eliminates dead code
- [x] **QUAL-06**: `requirements.dev.txt` trailing quote character fixed — fixes pip install failure

### Project Identity (IDENT)

- [x] **IDENT-01**: Python package renamed from `update_whitelist` to `stay_in_whitelist` — aligns with project directory name
- [x] **IDENT-02**: All user-facing strings, log messages, and comments updated to "Stay in Whitelist" branding
- [x] **IDENT-03**: Config YAML keys updated for new naming (where applicable)
- [ ] **IDENT-04**: `README.md` rewritten to reflect new project name and updated architecture
- [x] **IDENT-05**: Security group rule description prefix updated from "from Wulihe" to "Stay-in-Whitelist" — aligns with new project identity
- [x] **IDENT-06**: Rule description prefix is configurable via `config.yaml` — isolates dev/prod environments (e.g. "Stay-in-Whitelist-prod" vs "Stay-in-Whitelist-dev"), prevents home debugging from overwriting workplace IP rules

### Operational (OPS)

- [ ] **OPS-01**: APScheduler configured with explicit `misfire_grace_time` — prevents silent job skipping
- [ ] **OPS-02**: `systemd` service unit template updated with correct `WorkingDirectory` and `StandardOutput`/`StandardError` paths
- [ ] **OPS-03**: Log retention period increased from 7 to 30 days — improves audit trail for security tool

## v2 Requirements (Deferred)

- Health check / heartbeat mechanism
- Startup immediate IP check (run once on daemon start, before scheduler)
- Consecutive failure tracking and alerting
- Idempotent rule management (skip if rule already exists)
- IP change notification (webhook/email)
- systemd WatchdogSec integration via sd_notify
- Rollback mechanism for failed updates
- Aliyun cloud provider implementation

## Out of Scope

- Web UI or API interface — self-use CLI tool, no need
- Async/queue architecture — current scale doesn't justify the complexity
- Container/Docker deployment — systemd service is sufficient
- Multi-tenant support — single user tool
- HashiCorp Vault / secrets manager — local config.yaml + gitignore is sufficient for self-use
- Database storage for state — file-based cache is sufficient

## Traceability

| REQ-ID | Phase | Status |
|--------|-------|--------|
| REL-01 | Phase 1 | Complete |
| REL-02 | Phase 1 | Complete |
| REL-03 | Phase 1 | Complete |
| REL-04 | Phase 1 | Complete |
| REL-05 | Phase 1 | Complete |
| REL-06 | Phase 1 | Complete |
| REL-07 | Phase 1 | Complete |
| CONF-01 | Phase 2 | Complete |
| CONF-02 | Phase 2 | Complete |
| CONF-03 | Phase 2 | Complete |
| CONF-04 | Phase 2 | Complete |
| QUAL-04 | Phase 2 | Complete |
| QUAL-01 | Phase 3 | Complete |
| QUAL-02 | Phase 3 | Complete |
| QUAL-03 | Phase 3 | Complete |
| QUAL-05 | Phase 3 | Complete |
| QUAL-06 | Phase 3 | Complete |
| IDENT-01 | Phase 4 | Complete |
| IDENT-02 | Phase 4 | Complete |
| IDENT-03 | Phase 4 | Complete |
| IDENT-04 | Phase 4 | Pending |
| IDENT-05 | Phase 4 | Complete |
| IDENT-06 | Phase 4 | Complete |
| OPS-01 | Phase 5 | Pending |
| OPS-02 | Phase 5 | Pending |
| OPS-03 | Phase 5 | Pending |
