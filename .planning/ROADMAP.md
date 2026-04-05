# Roadmap: Stay in Whitelist

## Overview

This roadmap transforms Stay in Whitelist from a working-but-fragile daemon into a reliable, well-named, production-ready systemd service. The journey starts with critical reliability fixes that prevent hangs, lockouts, and data corruption, then hardens configuration and code quality, renames the project to align with its directory identity, and finishes with operational deployment tuning. Every phase delivers a daemon you can trust a little more than the last.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Critical Reliability** - Fix the five bugs that cause hangs, lockouts, and garbage in security groups
- [ ] **Phase 2: Configuration Hardening** - Fix config loading, file paths, Pydantic API, and shared-state bug
- [ ] **Phase 3: Code Quality** - Replace print with logger, remove dead code, fix build artifacts
- [ ] **Phase 4: Project Identity** - Rename package, update branding, add configurable rule prefix for dev/prod isolation
- [ ] **Phase 5: Operational Deployment** - APScheduler tuning, systemd unit, log retention

## Phase Details

### Phase 1: Critical Reliability
**Goal**: The daemon never hangs, never locks users out, and never writes garbage to security group rules
**Depends on**: Nothing (first phase)
**Requirements**: REL-01, REL-02, REL-03, REL-04, REL-05, REL-06, REL-07
**Success Criteria** (what must be TRUE):
  1. Every network request (IP detection + cloud API) completes or fails within a bounded timeout -- no indefinite hangs
  2. If the primary IP detection provider fails, the daemon automatically falls back to secondary providers and still detects the IP
  3. Invalid IP responses (HTML error pages, rate-limit messages) are rejected before reaching any cloud API call
  4. Cloud API transient failures are retried up to 3 times with exponential backoff without manual intervention
  5. If a rule update fails midway, the old rules remain in place -- the user is never locked out
**Plans**: 3 plans

Plans:
- [x] 01-01-PLAN.md -- IP detection: multi-provider fallback, timeout, IP validation (REL-01, REL-02, REL-03)
- [ ] 01-02-PLAN.md -- Cloud provider error handling: get_rules returns [], add_rules try/except (REL-06, REL-07)
- [ ] 01-03-PLAN.md -- Updater: add-before-delete order + tenacity retry (REL-04, REL-05)

### Phase 2: Configuration Hardening
**Goal**: The daemon loads config safely, uses correct file paths under systemd, and has no Pydantic deprecation warnings
**Depends on**: Phase 1
**Requirements**: CONF-01, CONF-02, CONF-03, CONF-04, QUAL-04
**Success Criteria** (what must be TRUE):
  1. The check interval is read from config.yaml (defaulting to 600 seconds) and can be changed without code changes
  2. The ip_cache file and log file are written to their configured absolute paths regardless of working directory -- systemd deployment works correctly
  3. Importing the config module does not trigger file I/O -- config loads only when explicitly initialized
  4. No Pydantic deprecation warnings appear during config usage (model_dump replaces dict)
  5. The Updater's cloud client is an instance variable, not shared across instances via class variable
**Plans**: TBD

Plans:
- [ ] 02-01: TBD
- [ ] 02-02: TBD
- [ ] 02-03: TBD

### Phase 3: Code Quality
**Goal**: All output goes through structured logging, dead code is removed, and the build toolchain works cleanly
**Depends on**: Phase 2
**Requirements**: QUAL-01, QUAL-02, QUAL-03, QUAL-05, QUAL-06
**Success Criteria** (what must be TRUE):
  1. All runtime output appears in the log file via logger calls -- no print() statements remain in production code
  2. API tokens never appear in log output -- credential leakage is prevented
  3. Commented-out dead code in updater.py is removed -- the file contains only active logic
  4. The unused config_loader.py module no longer exists in the codebase
  5. `pip install -r requirements.dev.txt` succeeds without errors (trailing quote character fixed)
**Plans**: TBD

Plans:
- [ ] 03-01: TBD
- [ ] 03-02: TBD

### Phase 4: Project Identity
**Goal**: The project is consistently named "Stay in Whitelist" everywhere, with a configurable rule prefix that isolates dev and prod environments
**Depends on**: Phase 3
**Requirements**: IDENT-01, IDENT-02, IDENT-03, IDENT-04, IDENT-05, IDENT-06
**Success Criteria** (what must be TRUE):
  1. The Python package is importable as `stay_in_whitelist` (not `update_whitelist`) -- all imports and entry points updated
  2. Log messages, comments, and user-facing strings reference "Stay in Whitelist" branding consistently
  3. The README accurately describes the project by its new name with current architecture details
  4. Security group rule descriptions use the "Stay-in-Whitelist" prefix (or a custom prefix from config)
  5. A developer can run a local instance with a custom rule prefix (e.g., "Stay-in-Whitelist-dev") that does not interfere with production rules on the same cloud account
**Plans**: TBD

Plans:
- [ ] 04-01: TBD
- [ ] 04-02: TBD
- [ ] 04-03: TBD

### Phase 5: Operational Deployment
**Goal**: The daemon runs reliably as a systemd service with proper scheduler configuration and sufficient log retention for audit
**Depends on**: Phase 4
**Requirements**: OPS-01, OPS-02, OPS-03
**Success Criteria** (what must be TRUE):
  1. APScheduler does not silently skip scheduled checks due to misfire handling -- misfire_grace_time is explicitly configured
  2. The systemd service unit template references the correct WorkingDirectory, StandardOutput, and StandardError paths for the renamed project
  3. Log files are retained for 30 days, providing a sufficient audit trail for a security tool
**Plans**: TBD

Plans:
- [ ] 05-01: TBD
- [ ] 05-02: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 4 -> 5

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Critical Reliability | 0/3 | Not started | - |
| 2. Configuration Hardening | 0/3 | Not started | - |
| 3. Code Quality | 0/2 | Not started | - |
| 4. Project Identity | 0/3 | Not started | - |
| 5. Operational Deployment | 0/2 | Not started | - |
