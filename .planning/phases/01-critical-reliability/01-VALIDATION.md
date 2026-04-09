---
phase: 01
slug: critical-reliability
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-05
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.2.2 |
| **Config file** | pyproject.toml [tool.pytest.ini_options] |
| **Quick run command** | `pytest tests/ -x -q` |
| **Full suite command** | `pytest tests/ -v --tb=short` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/ -x -q`
- **After every plan wave:** Run `pytest tests/ -v --tb=short`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 01-01-01 | 01 | 1 | REL-01, REL-02, REL-03 | unit | `pytest tests/test_ip_fetcher.py -x -q` | ✅ | ⬜ pending |
| 01-01-02 | 01 | 1 | REL-01 | unit | `pytest tests/test_ip_fetcher.py -x -q` | ✅ | ⬜ pending |
| 01-02-01 | 02 | 1 | REL-04 | unit | `pytest tests/test_updater.py -x -q` | ✅ | ⬜ pending |
| 01-02-02 | 02 | 1 | REL-05 | unit | `pytest tests/test_updater.py::test_add_before_delete -x -q` | ✅ | ⬜ pending |
| 01-02-03 | 02 | 1 | REL-06 | unit | `pytest tests/test_huawei_cloud.py tests/test_tencent_cloud.py -x -q` | ✅ | ⬜ pending |
| 01-03-01 | 03 | 1 | REL-07 | unit | `pytest tests/test_huawei_cloud.py -x -q` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_ip_fetcher.py` — tests for multi-provider fallback, all-providers-fail, IP validation, timeout behavior
- [ ] `tests/test_updater.py` — modify existing test for add-before-delete order
- [ ] `tests/test_huawei_cloud.py` — tests for add_rules() error handling, get_rules() returning [] on error
- [ ] `tests/test_tencent_cloud.py` — test for get_rules() returning [] on error

*If none: "Existing infrastructure covers all phase requirements."*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| None | - | - | - |

All phase behaviors have automated verification.

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
