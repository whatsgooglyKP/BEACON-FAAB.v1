# Evals: how we know the cleaner can be trusted

## Run
```bash
.venv/bin/python -m evals.run                 # all 7 evals (or: make eval)
.venv/bin/python -m evals.run --only 2,3      # just some evals
.venv/bin/python -m evals.run --skip-gemini   # no Gemini calls (or: make eval-fast)
.venv/bin/python -m evals.run --gemini-n 5    # more Gemini runs
.venv/bin/python -m evals.run --random        # adds 10 unseeded tracts to the spot check
```
Results print as a scorecard and are saved to `evals/results/latest.md` and `latest.json`, with a timestamp. The exit code is 1 if anything fails.
The raw Beacon files must be present in `data/beacon/` (they are gitignored).

## What each eval checks
| # | Eval | What it checks | Why it matters |
|---|---|---|---|
| 1 | Cleaning correctness | Unit tests on tiny hand-made data with known answers: tract IDs normalized, suppressed codes → blank, top-coded values kept, >100% capped *and* logged, fills labeled by source, uploads joined, routing math | Proves each cleaning rule does exactly what we say |
| 2 | Real-data integrity | 968 tracts in = 968 out; no duplicate IDs; population totals 4,688,329; raw columns identical to USDA; every cap, fill and recode has a log row with before/after; no Census value changed silently | Shows cleaning didn't lose, duplicate or quietly alter data |
| 3 | Source spot-check | 10 tracts (fixed seed 42, optionally 10 random) compared field-by-field to the original USDA and Census cells | An independent check against the original files |
| 4 | Ranking sanity | No dorm-heavy, tiny or flagged tracts in the top 10; same top 10 on a re-run; top 10 overlaps ≥ 8/10 after adding 1% random noise (20 trials) | Rankings aren't driven by bad data or tiny wobbles |
| 5 | Gemini faithfulness | Car-free figure must be called homes/housing units, never households; required framings present; every number in Gemini's report must appear in the stats-based template (rounding tolerance); headline numbers must match the summary; a simulated Gemini failure must fall back to the template. SKIP if no key or Gemini is down | The AI can't invent numbers, and the app still works without it |
| 6 | Routing | Uses the **made-up EXAMPLE** inventory. No site ships more than it has; every top tract is matched when supply suffices; distances are between 0 and 60 miles | Routing suggestions are physically possible |
| 7 | End-to-end smoke | Runs the real app headlessly through steps 1→3 plus the routing example; no exceptions; clean CSV, problem CSV and report are non-empty and parseable | The demo won't crash |

## Reading the scorecard
- **PASS:** the check held.
- **FAIL:** something is wrong; the detail says what.
- **SKIP:** the check couldn't run (usually no Gemini key or Gemini overloaded). Its non-Gemini parts (template numbers, fallback) still ran.

## If one fails
1. Unit tests failing means a cleaning rule changed: `make test` shows which.
2. Integrity or spot-check failing means the source files changed or a cleaning step altered data. Compare against `data/clean/issues.csv`.
3. Ranking failing means a flagged tract got in, or the ranking is unstable. Check `top_need()` in `clean.py`.
4. Gemini failing means the report used a number not in the stats. Tighten the prompt in `report.py`, or present the template report.
5. Routing failing: check `routing.match_inventory`.
6. Smoke failing: run `streamlit run app.py` and read the error.
