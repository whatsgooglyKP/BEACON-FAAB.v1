# Eval scorecard — 2026-11-07T18:42:56-05:00

**7 pass · 0 fail · 0 skip** (163.6 s)

| # | Eval | Result | Detail |
|---|---|---|---|
| 1 | Cleaning correctness (unit tests) | PASS | 9 passed in 0.31s |
| 2 | Real-data integrity | PASS | 968 in/968 out, 0 dupes, pop 4,688,329, 4 caps + 472 fills + 16 recodes all logged with before/after |
| 3 | Source spot-check | PASS | 10 tracts × up to 6 fields match source cells exactly |
| 4 | Ranking sanity | PASS | 0 flagged in top 10, deterministic, 1% noise overlap min 10/10 (20 trials) |
| 5 | Gemini report faithfulness | PASS | 1/3 Gemini runs returned; 1 fully faithful; fallback ok |
| 6 | Routing | PASS | 13 legs, 9,499/9,500 lb used, all 10 tracts matched, 7.9–56.6 mi |
| 7 | End-to-end smoke | PASS | 3 steps rendered, routing example ran, 0 exceptions; downloads: clean CSV 968 rows, issues CSV 3,124 rows, report 1,907 chars |
