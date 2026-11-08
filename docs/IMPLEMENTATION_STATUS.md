# Approved redesign implementation status

This describes the local prototype, not production readiness. See the latest scorecard for executed checks and exact results.

## Implemented

- All three community adapters and the ID union (490 / 2,327 / 268), common fields, cell provenance, raw hashes/values, bounds and explicit missing reasons.
- All 18 review rules; safe format/code recipes separate from meaning-changing proposals and contextual cautions. Correct Appendix B half/10 driving LILA and ACS 2020–24 wording. No mixed-denominator SNAP fill or percentage cap.
- Load → Review → Use; retained dashboard with default reviewed-only list, explained model rank and evidence-quality labels, and a point map. Labeled unreviewed preview retains uncertain places.
- Accept/Reject/source-backed numeric Edit on actual value/exclusion proposals; interpretation edits via tract notes. Required reviewer/reason, domain checks, optimistic stale-save protection, Undo, persistence, append-only trace and exact export replay.
- Sequential two-reviewer disagreement, provisional/agreed states, explicit resolution and reopening for a new contrary vote. No last-writer-wins for data or operational recommendations.
- Tract notes, confirm/challenge inferred need, approve/reject/replace actions and independent human operational position.
- Beacon design tokens, readable typography/fallback, plain text brand treatment, no altered/reproduced logo, explicit unofficial-prototype attribution.
- Bounded offline chat and opt-in Gemini paragraph ordering, instant built-in text, explicit nonblocking AI buttons, a 20-second total cap with no retries and semantic gate. Gemini never edits or infers data. Live availability is a separate eval result, not silently counted as a pass.
- Architecture/README/major-code explanations, eight redesigned mandatory evaluation suites, separate optional-model result and screenshot automation using a disposable headless test browser.

## Deliberately not implemented / not claimed

- Deployment or submission to Devpost; slide deck/video are separate deliverables.
- Forecasting, private uploads, current inventory, surplus routing, service dispatch or systematic address-list retailer density. Legacy code is preserved only as a backup.
- Production authentication, concurrent multi-user permissions, calibrated probabilities, independently verified reviewer citations, verified live pantry capacity or authenticated external collaboration.
- Arbitrary upload/schema inference, eight-county Florida expansion and bulk statistical “fix all.” Repeated uncertainties require individual judgment; the safe import recipe already runs automatically.
- Licensed Avenir assets or official logo artwork. Fonts fall back to Arial/sans-serif; the supplied rules do not authorize recreating logo artwork.
- Practitioner usability validation, calibrated thresholds or causal user-impact evidence. Kevin's five-minute usability check is still needed.
- Public operational catalog matching, nearest-facility claims or live opening-hours verification. Appendix B public finders are manual-follow-up links.
- An unrestricted LLM research conversation. The optional model is deliberately constrained to faithful ordering of an already grounded packet.

## Screenshots and demo records

Current screenshots live under `screenshots/redesign/`. The screenshot server uses a separate `data/review/demo.sqlite3` and an explicit **Demonstration workspace** banner. Its named reviewers and choices are simulated; every measured input remains the real public source value. The normal application database is not populated with these demo choices.

## Lessons / next

**Made:** a reviewable evidence pipeline and a small explained action list, not another large unexplained dashboard. **Learned:** geography, definitions, missingness and shared upstream data matter more than a “problems fixed” counter; statistical sensitivity can substantially change a top-ten list. **Next:** practitioner threshold/usability calibration, fresher public evidence, verified resource catalogs, authenticated collaboration, and independent security/code review before production use.

- Answer-first default with ten explained candidates and map, explicitly not team-checked; bounded MOE-sensitive quick checks (FL 8 / NYC 5 / Salt Lake–Tooele 8), audited team choices and real entry/exit summaries. All former workflow views remain under Advanced / full review.

## Verified follow-up result

- `pytest`: **38 passed**, including a real hung-client wall-clock test at **19.50 seconds**, default offline rendering, optional-button responsiveness, and stale quick-form rejection. [Recorded pytest result](../evals/results/pytest_latest.json).
- Full offline scorecard: **8 PASS / 0 FAIL / 1 optional live Gemini SKIP**. [Actual suite results](../evals/results/latest.md); no live-model success is claimed.
- Thirteen refreshed screenshots cover landing top ten/map, quick checks, after-decision changes, advanced navigation, all three original steps, disagreement, built-in summary and built-in chat. Real source data and simulated reviewer choices are explicitly labeled.
- No deployment; original sources and `app_v0_dashboard.py` remain unchanged.
