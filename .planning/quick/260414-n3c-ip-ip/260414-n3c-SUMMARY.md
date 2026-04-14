---
phase: quick-260414-n3c
plan: 01
subsystem: ip-detection
tags: [tri-state, error-handling, certifi, OSError, fallback]

requires:
  - phase: phase-01
    provides: IP detection and cloud provider infrastructure
provides:
  - tri-state has_ip_changed return (True/False/None)
  - OSError per-provider catch in get_current_ip
  - certifi as explicit dependency
affects: [ip-detection, cli, error-handling]

tech-stack:
  added: [certifi>=2024.2.2]
  patterns: [tri-state return for failure vs unchanged distinction]

key-files:
  created: [tests/test_cli.py]
  modified: [stay_in_whitelist/cli.py, stay_in_whitelist/ip_fetcher.py, pyproject.toml, tests/test_ip_fetcher.py]

key-decisions:
  - "Tri-state return (None, None) for IP fetch failure, distinct from (False, ip) for unchanged"
  - "OSError caught per-provider to handle missing certifi CA bundle without killing entire fallback chain"
  - "certifi added as explicit dependency to prevent missing CA bundle on fresh installs"

patterns-established:
  - "Tri-state return pattern: (True, ip) / (False, ip) / (None, None) for changed/unchanged/failure"

requirements-completed: [BUG-ip-fetch-failure-vs-unchanged, BUG-certifi-ca-bundle-missing]

duration: 5min
completed: 2026-04-14
---

# Quick Task 260414-n3c: IP Detection Failure vs Unchanged Bug Fix Summary

**Tri-state has_ip_changed distinguishing fetch failure from IP unchanged, OSError per-provider fallback for certifi CA bundle, certifi as explicit dependency**

## Performance

- **Duration:** 5 min
- **Started:** 2026-04-14T08:46:53Z
- **Completed:** 2026-04-14T08:52:13Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- Fixed has_ip_changed to return tri-state: (True, ip) / (False, ip) / (None, None) instead of conflating failure with unchanged
- Added OSError to per-provider catch in get_current_ip, allowing fallback when certifi CA bundle is missing
- Added certifi>=2024.2.2 as explicit dependency in pyproject.toml
- check_and_update_ip now logs failure message on fetch failure, never calls updater or cache_ip on failure

## Task Commits

Each task was committed atomically:

1. **Task 1: Write tests for all fixes (TDD RED)** - `f4f7017` (test)
2. **Task 2: Implement all fixes (TDD GREEN)** - `7e92511` (fix)

_Note: TDD tasks have two commits (test then implementation)_

## Files Created/Modified
- `tests/test_cli.py` - New file: 9 tests for tri-state has_ip_changed and check_and_update_ip failure handling
- `tests/test_ip_fetcher.py` - Added 2 tests for OSError per-provider fallback
- `stay_in_whitelist/cli.py` - tri-state has_ip_changed return, failure path in check_and_update_ip
- `stay_in_whitelist/ip_fetcher.py` - OSError added to per-provider except block
- `pyproject.toml` - certifi>=2024.2.2 added to dependencies

## Decisions Made
- Used tri-state (None, None) for failure rather than raising exception, to keep scheduler loop stable
- OSError caught alongside requests.RequestException per-provider since certifi raises OSError (not RequestException) when cacert.pem is missing
- certifi added with minimum version >=2024.2.2 (no upper bound) to avoid conflicts with other dependencies

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- _version.py module missing in worktree (generated file, gitignored) - created a stub version to unblock test runs

## User Setup Required

None - no external service configuration required.

## Self-Check: PASSED

All 5 modified/created files verified present. Both commit hashes (f4f7017, 7e92511) verified in git log. Full test suite (102 tests) passes with zero regressions.

---
*Phase: quick-260414-n3c*
*Completed: 2026-04-14*
