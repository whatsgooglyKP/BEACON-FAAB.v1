# Beacon redesign scorecard · 2026-11-07T19:35:35-05:00 ET

**7 PASS · 0 FAIL · 1 SKIP** (132.7 seconds)

| # | Suite | Result | Evidence |
|---|---|---|---|
| 1 | Rules / schema acceptance | PASS | 22 passed in 29.67s |
| 2 | Real-data integrity / coverage | PASS | fl: 490 retained; nyc: 2327 retained; slc: 268 retained; source byte hashes unchanged; union preserved; no duplicate joins |
| 3 | Independent source checks | PASS | fl: 18 stratified tracts; nyc: 17 stratified tracts; slc: 18 stratified tracts; 2,992 paired poverty cells identical (same upstream ACS); seeded disagreement detected |
| 4 | Rank / confidence / sensitivity | PASS | 10 independent midrank checks; deterministic; FL missing transport never zero. Top-10 overlap in 10 trials: 1% noise 10–10, MOE-aware 4–7. Definition-change flags among comparable records: {'fl': 76, 'nyc': 24, 'slc': 40} |
| 5b | Optional live Gemini | SKIP | 0 attempts: --skip-gemini or key not present; offline template is tested separately |
| 5 | Offline report faithfulness | PASS | Template indicator/geography/unit/year checks pass; simulated timeout uses identical fallback; swapped units/years and invented stock rejected |
| 6 | Human review / audit | PASS | 5 passed in 4.94s; full append history, both vote orders, stale save, restart, undo, explicit resolution/reopen, and export replay verified |
| 7 | End-to-end / export replay | PASS | fl: 3 UI steps, 490 export rows; nyc: 3 UI steps, 2327 export rows; slc: 3 UI steps, 268 export rows; UI disagreement/resolution exercised; replayed views exactly match; no dispatch or inventory upload |
