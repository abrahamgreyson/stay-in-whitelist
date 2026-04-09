---
phase: 2
slug: configuration-hardening
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-06
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.2.2 |
| **Config file** | pyproject.toml `[tool.pytest.ini_options]` |
| **Quick run command** | `python -m pytest tests/ -x -q` |
| **Full suite command** | `python -m pytest tests/ -v --cov=update_whitelist` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/ -x -q`
- **After every plan wave:** Run `python -m pytest tests/ -v --cov=update_whitelist`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 02-01-01 | 01 | 1 | CONF-03 | unit | `python -m pytest tests/test_config.py -x -q` | ❌ W0 | ⬜ pending |
| 02-01-02 | 01 | 1 | CONF-01 | unit | `python -m pytest tests/test_config.py -x -q` | ❌ W0 | ⬜ pending |
| 02-01-03 | 01 | 1 | CONF-02 | unit | `python -m pytest tests/test_config.py -x -q` | ❌ W0 | ⬜ pending |
| 02-02-01 | 02 | 1 | CONF-02 | unit | `python -m pytest tests/test_ip_fetcher.py -x -q` | ❌ W0 | ⬜ pending |
| 02-02-02 | 02 | 1 | CONF-03 | unit | `python -m pytest tests/test_ip_fetcher.py -x -q` | ❌ W0 | ⬜ pending |
| 02-02-03 | 02 | 1 | CONF-01 | unit | `python -m pytest tests/test_main.py -x -q` | ❌ W0 | ⬜ pending |
| 02-03-01 | 03 | 1 | QUAL-04 | unit | `python -m pytest tests/test_updater.py -x -q` | ❌ W0 | ⬜ pending |
| 02-03-02 | 03 | 1 | CONF-04 | unit | `python -m pytest tests/test_updater.py -x -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_config.py` — covers CONF-01 validation, CONF-02 path resolution, CONF-03 deferred loading
- [ ] `tests/conftest.py` — shared mock_config fixture (D-13)
- [ ] `tests/test_main.py` — update for config parameter injection (CONF-01 scheduler interval)
- [ ] `tests/test_updater.py` — update mock from `.dict()` to attribute iteration, add instance variable test
- [ ] `tests/test_ip_fetcher.py` — update for config parameter injection (CONF-02 ip_cache path)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| None | — | — | — |

All phase behaviors have automated verification.

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
