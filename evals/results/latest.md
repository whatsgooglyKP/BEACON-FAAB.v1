# Beacon redesign scorecard · 2026-11-07T20:05:36-05:00 ET

**8 PASS · 0 FAIL · 1 SKIP** (211.1 seconds)

| # | Suite | Result | Evidence |
|---|---|---|---|
| 1 | Rules / schema acceptance | PASS | 38 passed in 82.04s (0:01:22) |
| 2 | Real-data integrity / coverage | PASS | fl: 490 retained; nyc: 2327 retained; slc: 268 retained; source byte hashes unchanged; union preserved; no duplicate joins |
| 3 | Independent source checks | PASS | fl: 18 stratified tracts; nyc: 17 stratified tracts; slc: 18 stratified tracts; 2,992 paired poverty cells identical (same upstream ACS); seeded disagreement detected |
| 4 | Rank / confidence / sensitivity | PASS | 10 independent midrank checks; deterministic; FL missing transport never zero. Top-10 overlap in 10 trials: 1% noise 10–10, MOE-aware 4–7. Definition-change flags among comparable records: {'fl': 76, 'nyc': 24, 'slc': 40} |
| 5b | Optional live Gemini | SKIP | 0 attempts: --skip-gemini or key not present; offline template is tested separately |
| 5 | Offline report faithfulness | PASS | Instant default without client; nonblocking optional job and bounded hung-client fallback; template indicator/geography/unit/year checks pass; swapped units/years and invented stock rejected |
| 6 | Human review / audit | PASS | 5 passed in 5.10s; full append history, both vote orders, stale save, restart, undo, explicit resolution/reopen, and export replay verified |
| 7 | End-to-end / export replay | PASS | fl: 3 UI steps, 490 export rows; nyc: 3 UI steps, 2327 export rows; slc: 3 UI steps, 268 export rows; UI disagreement/resolution exercised; replayed views exactly match; no dispatch or inventory upload |
| 8 | Answer-first / sensitive quick checks | PASS | Pristine quick checks {'fl': 8, 'nyc': 5, 'slc': 8}; all have real ±90% poverty-MOE membership witnesses; capped at 8, not refilled; actual UI challenge replaces a candidate without changing source estimates; stale targets are rejected. 2 passed in 12.68s |
