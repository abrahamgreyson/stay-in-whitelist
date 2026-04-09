---
phase: 4
slug: project-identity
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-06
---

# Phase 4 -- Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.2.2 |
| **Config file** | pyproject.toml [tool.pytest.ini_options] |
| **Quick run command** | `python -m pytest tests/ -x -q` |
| **Full suite command** | `python -m pytest tests/ -v --cov=stay_in_whitelist` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/ -x -q`
- **After every plan wave:** Run `python -m pytest tests/ -v --cov=stay_in_whitelist`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 04-01-01 | 01 | 1 | IDENT-05, IDENT-06 | unit | `python -m pytest tests/ -x -q` | Y | pending |
| 04-01-02 | 01 | 1 | IDENT-05, IDENT-06 | unit | `python -m pytest tests/ -x -q` | Y | pending |
| 04-02-01 | 02 | 1 | IDENT-01, IDENT-03 | manual | `grep -c "stay-in-whitelist" pyproject.toml` | Y | pending |
| 04-02-02 | 02 | 1 | IDENT-02, IDENT-03 | manual | `grep -c "update_whitelist" .gitignore .github/ .gitlab-ci.yml config.example.yaml` | Y | pending |
| 04-03-01 | 03 | 2 | IDENT-01, IDENT-02 | unit | `python -m pytest tests/ -x -q` | Y | pending |
| 04-03-02 | 03 | 2 | IDENT-02 | unit | `python -m pytest tests/ -x -q && grep -rn "update.whitelist" --include="*.py" stay_in_whitelist/ main.py tests/` | Y | pending |
| 04-04-01 | 04 | 3 | IDENT-04 | manual | File inspection + README review | Y | pending |
| 04-04-02 | 04 | 3 | IDENT-04 | manual | Human verification checkpoint | Y | pending |

*Status: pending / green / red / flaky*

---

## Wave 0 Requirements

*Existing infrastructure covers all phase requirements.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| README content accuracy | IDENT-04 | Human judgment on prose quality | Read README.md, verify project name, architecture, badges |
| Log filename default change | IDENT-02 | Requires checking default value, not runtime behavior | Verify `logger.py` default is `stay_in_whitelist.log` |
| Zero old branding in Python files | IDENT-02 | Grep-based verification, not unit test | `grep -rn "update.whitelist" --include="*.py" stay_in_whitelist/ main.py tests/` returns nothing |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
