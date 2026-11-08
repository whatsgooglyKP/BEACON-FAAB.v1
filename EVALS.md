# How to evaluate Beacon Evidence Review

Run from the repo root with the required public files installed:

```bash
.venv/bin/python -m pytest -q tests
.venv/bin/python -m evals.run
.venv/bin/python -m evals.run --skip-gemini
.venv/bin/python -m evals.run --only 2,3
.venv/bin/python -m evals.run --only 5 --gemini-n 1
```

The command exits nonzero if any mandatory suite or attempted semantic model check fails. `evals/results/latest.json` and `latest.md` record actual outcomes with America/New_York (ET) timestamps. A partial `--only` run replaces the latest scorecard, so run the full command before presenting final results.

| Suite | Evidence checked |
|---|---|
| 1. Rules/schema | Independent fixtures for all 18 rules, exact tract-ID rules, source codes/bounds, missingness reasons, domain/denominator safety, imprecision, ranking ties/cohorts, consensus and workflow tests. Legacy cleaner tests are archived, not counted as redesigned passes. |
| 2. Real-data integrity/coverage | Independently computed county-ID union; 490 Central Florida tracts; no many-to-many duplication; source hashes unchanged; Florida transportation stays missing. |
| 3. Independent source checks | At least ten Central Florida tracts plus stratified missing-code, unmatched, group-setting, rural and definition-sensitivity cases. Direct poverty/SNAP cells, population, group quarters, both LILA methods and access counts. All 488 paired numeric poverty cells must agree; seeded >5-point conflict must be detected. |
| 4. Rank/confidence/sensitivity | Independent empirical-midrank oracle; deterministic results; missing mandatory inputs unscored; Florida transport never zero/transport gap; Medium maximum confidence. Actual 1% noise and MOE-aware top-ten overlap is **reported**, not forced to satisfy an arbitrary stability threshold. Definition sensitivity is counted separately. |
| 5. Offline report faithfulness | Source-appropriate counts, units, universes and years; exact fallback under simulated timeout; same-number/wrong-unit, wrong-year and invented-stock attacks rejected. |
| 5b. Optional live Gemini | Separate PASS/FAIL/SKIP, with actual attempt count. No key, explicit skip, timeout or server/model unavailability is **not a pass**. A returned response that fails the semantic gate is a model FAIL even though a usable offline fallback is retained. |
| 6. Human review/audit | Accept/Reject/source-backed Edit/Undo; required names/reasons/citations; source/domain validation; both conflict save orders; no last-writer-wins; stale saves; persisted restart; explicit resolution/reopening; notes, human/model-order separation; exact export replay. |
| 7. End-to-end/exports | Actual answer-first and advanced Streamlit Load/Review/Use in Central Florida using a temporary review database; no app exceptions; all export rows retained and full audit replay matches reviewed data. No inventory upload or dispatch step. |
| 8. Answer-first/quick checks | Small regional queues with real top-ten membership-change witnesses, exact score parity, audited Accept/Challenge behavior, real list changes, no made-up uncertainty corrections, and rejection of stale quick forms. |
| 9. Florida place labels/scope | 490 non-empty sourced labels, 307 named-place/CDP vs 183 unincorporated point assignments, one official tract-point fallback, five independent Census query checks, display-only score invariance, and no region selector. |

## Interpreting the results

- “PASS” proves the stated implementation check on these files/fixtures, **not** that a flagged tract is hungry, a resource has capacity, or the intervention works.
- The 157/37/48 LILA values are source flags, not approved shortlist sizes. FL's 129 high-CV poverty/SNAP estimates are 76+53 **estimates** across 97 distinct flagged tracts, not 129 neighborhoods. Undefined zero-estimate CV is separate.
- A missing/imprecise estimate is not a corrected number. Acknowledgment does not fix coverage or freshness. Missing required score inputs remain visibly unscored.
- Simulated review identities are explicitly test/demo identities, not practitioner validation. SQLite tests use temporary databases; the app's real review decisions are not overwritten.
- Live Gemini uses `gemini-3.8-flash` only when a key is present in the environment; 20-second total cap including all work, with no retries. Built-in reports/chat render without a model request; optional UI jobs never block a rerun. The key is never printed, placed in fixtures, or exported. No model is needed for the deterministic pipeline. Responsiveness tests inject a client that ignores transport timeouts and verify elapsed time is ≤20 seconds, late results cannot replace the fallback, and default UI render makes no model call. SDK configuration and optional-button responsiveness are tested separately.
- Exact approved paragraph matching is intentionally stricter than numeric matching: it prevents swapping correct numbers between the wrong geographies/units/years. The chat is bounded, not an unrestricted research assistant.

## Qualitative usability check (not yet performed)

Ask Kevin to explain a flag, find its source/year, reject a proposal, recognize disagreement and explain one shortlisted tract, without coaching. Record completion/confusions. Do not claim validated user impact without this check. A separate human code review is also recommended before production use.

## Follow-up acceptance checks

`tests/test_responsive_ui.py` covers default-offline latency, nonblocking optional requests, a real 20-second hung-client bound, ignored late results, one-attempt SDK settings, friendly headers/statuses and view-only rounding, and report/chat buttons in the actual Streamlit UI. Suite 1 runs these tests; suite 5 additionally checks that the default never constructs a client and that a hung optional request returns the identical fallback within its deadline. Run `python -m evals.run --skip-gemini` to keep live-model availability explicitly SKIP rather than manufacture a pass.

## Answer-first / quick-check gate (suite 8)

The mandatory eighth suite verifies the pristine Central Florida count (8), an eight-item ceiling, exact parity with the full score engine, and a recorded low/high uncertainty scenario that truly changes top-ten membership for every surfaced card. Zero-MOE and unrelated SNAP uncertainty must not create quick work. Real UI tests challenge a candidate, observe a replacement and a one-line change explanation, and verify the queue shrinks rather than replenishes. Accept tests require unchanged source values/scores and an honest unchanged-membership message. A stale form must never vote against a newly selected tract after another reviewer handles the displayed one. All source rows remain available in advanced review and exports.

## Place labels and geographic scope

The application and all current evaluation suites are Central Florida only. `tests/test_place_names.py` verifies complete coverage, exact tract IDs, source metadata, primary UI labels, known assignments independently queried from official Census services, export inclusion and exact replay, unchanged analytical scores, and the single exposed Florida scope. No live geocoding is needed at runtime or in tests. Full polygon rebuild verification is reproducible with `python scripts/build_place_names.py --verify` after installing the optional GIS requirements. Labels are approximate point-based Census places, not definitive neighborhood boundaries.
