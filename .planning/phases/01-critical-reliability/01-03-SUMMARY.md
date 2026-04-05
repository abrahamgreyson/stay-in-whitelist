---
phase: 01-critical-reliability
plan: 03
subsystem: updater
tags: [tenacity, retry, security-groups, add-before-delete, error-handling]

# Dependency graph
requires:
  - phase: 01-02
    provides: "Cloud providers return [] from get_rules() on error"
provides:
  - "Updater.add_rules called BEFORE delete_rules (no lockout window)"
  - "Updater._call_with_retry with tenacity: 3 attempts, exponential backoff on ConnectionError/Timeout"
  - "Updater.fetch_security_group_rules returns [] on error"
affects: [ip-detection, scheduler]

# Tech tracking
tech-stack:
  added: [tenacity]
  patterns:
    - "Add-before-delete rule update order: new rules added before old rules deleted"
    - "Retry wrapper for transient network errors with tenacity decorator"

key-files:
  created: []
  modified:
    - update_whitelist/updater.py
    - tests/test_updater.py

key-decisions:
  - "Retry applied at updater level via _call_with_retry helper, not inside cloud provider methods, because providers already catch SDK exceptions internally"
  - "Only requests.ConnectionError and requests.Timeout are retried -- SDK exceptions are caught by providers"
  - "fetch_security_group_rules returns [] on error (matching Plan 02 cloud provider contract)"

patterns-established:
  - "Add-before-delete: security group rules are added before old ones are removed to prevent lockout"
  - "Retry wrapper: _call_with_retry wraps cloud API calls with tenacity for transient failure resilience"

requirements-completed: [REL-04, REL-05]

# Metrics
duration: 3min
completed: 2026-04-05
---

# Phase 01 Plan 03: Updater Retry and Rule Order Summary

**Reversed security group rule update order to add-before-delete and added tenacity retry with exponential backoff on transient network errors**

## Performance

- **Duration:** 3 min
- **Started:** 2026-04-05T15:05:13Z
- **Completed:** 2026-04-05T15:08:37Z
- **Tasks:** 1 (TDD: RED + GREEN)
- **Files modified:** 2

## Accomplishments
- Reversed update_security_group_rules: add_rules called BEFORE delete_rules, eliminating lockout window
- Added tenacity retry via _call_with_retry helper: 3 attempts, exponential backoff (1-10s), only on ConnectionError/Timeout
- Fixed fetch_security_group_rules to return [] on error instead of None, matching cloud provider contract
- Removed dead print() call from fetch_security_group_rules
- All 12 updater tests pass, full suite 38 tests pass with no regressions

## Task Commits

Each task was committed atomically (TDD: RED then GREEN):

1. **Task 1 RED: Test updater improvements** - `d42397d` (test)
2. **Task 1 GREEN: Implement updater improvements** - `46ce145` (feat)

## Files Created/Modified
- `update_whitelist/updater.py` - Reversed rule order (add before delete), added tenacity import and _call_with_retry, fixed fetch return type, removed print()
- `tests/test_updater.py` - Added 7 new tests for call order, retry behavior, and fetch return type; updated 3 existing tests for new call order

## Decisions Made
- Retry applied at updater level via _call_with_retry helper, not inside cloud provider methods, because providers already catch SDK exceptions internally and retry is only needed for unhandled network errors
- Only requests.ConnectionError and requests.Timeout are retried -- SDK-specific exceptions are already caught by providers and logged
- fetch_security_group_rules returns [] on error to match the Plan 02 cloud provider contract ([] from providers, [] from updater)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Phase 01 (Critical Reliability) is now complete -- all 3 plans executed
- Cloud providers return [] on error, updater adds before deletes, retry handles transient failures
- The system is now resilient against: lockout during updates, transient network errors, and error return type confusion

## Self-Check: PASSED

All 3 files verified present. Both commits verified in git history.

---
*Phase: 01-critical-reliability*
*Completed: 2026-04-05*
