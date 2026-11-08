# Beacon redesign — current approved Central Florida scope

This working specification incorporates Kevin's latest scope: **Central Florida only** (Lake, Orange, Osceola and Seminole). No region selector or other-region features are part of the app, tests or evaluations. Earlier scope remains in git history, not in the current product.

## Answer first

Open with ten automatically cleaned priority neighborhoods, one plain-English reason, evidence confidence and a simple map. Explicitly label the list “Automatically cleaned, not yet checked by your team.” This is a starting answer, not confirmed hunger, eligibility or an approved service plan. Show one short automatic-formatting summary; originals stay untouched.

Quick checks contain at most eight source-ranked top-ten tracts whose membership actually changes at the low/high endpoints of the published 90% poverty margin of error. Recompute the full Florida cohort in each single-tract scenario. Changes in ordering alone do not count. The pristine starting set has eight checks; do not refill it after each answer. Accept retains the measured value with its uncertainty. Challenge withholds that candidate from the team's working list and shows who enters/exits, without changing official measurements or analytical ranks. Reject a stale form rather than silently voting on a different tract.

All 18 rules, source review, notes, disagreements, operational actions, audit history and exports remain in **Advanced / full review**. Its default Use dashboard remains reviewed-only; an explicitly labeled unreviewed preview is separate from approval.

## Source and analytical contract

- Retain all **490** supplied Central Florida tracts. The four county FIPS are 12069, 12095, 12097 and 12117.
- Appendix B LILA means low income **AND** low grocery access, **½ mile urban / 10 miles rural, driving distance**. There are **157** source-flagged tracts, not 157 confirmed needs.
- Among those flagged tracts, **129 poverty/SNAP estimates** have CV >30% (76 poverty, 53 SNAP), across **97 distinct tracts**. Do not describe 129 neighborhoods or claim a proven small survey sample.
- ACS figures are **2020–24**. Access uses a **2020 population base** and **June 2025 retailer snapshot**; USDA initial release was July 2026. Conditions may have changed. PLACES observation years are unverified.
- Florida transportation and supplied food-insecurity estimates remain unavailable, not zero. No car/housing-unit proxy is substituted.
- Prefer direct ready-made ACS percentages. Never cap a mixed-year SNAP ratio and call it corrected. Say “homes” for housing units, “households” only for actual household measures, and “high poverty but low SNAP participation,” not an eligibility/non-enrollment claim.
- Score = `50 × (poverty midrank percentile + low-access-population-share midrank percentile)` within these 490 tracts, with valid complete cases defining the cohort. Equal values share percentiles; ties sort by exact tract GEOID. A missing required input is unscored, never zero or silently reweighted.
- Confidence concerns evidence quality, not a prediction probability. The 2020 population-base caution caps confidence at Medium. Acknowledging a limitation does not repair it or make it newer.

## Approximate place names

Use official **Census TIGER/Line 2024 Florida place boundaries**, including incorporated places and CDPs. Assign the supplied PLACES/map point by polygon containment. The one unavailable map point uses the matching official TIGER tract internal point for naming only. Outside all place polygons, use “Unincorporated <County> County.” No nearest-city or majority-area claim.

Commit only the reproducible small lookup, source hashes and independent sample-check records under `data/clean/`; keep boundary archives gitignored under `data/geography/raw/`. The lookup covers all **490** tracts: **307** incorporated-place/CDP point hits and **183** unincorporated labels. Five independently queried official Census samples verify Orlando, Alafaya, Poinciana, Pine Hills and an outside-place point.

Make “Place name” primary in tables, selectors, cards, map tooltips, inspectors, change summaries and exports. Keep exact tract GEOIDs alongside. Repeat: **Place names are approximate labels from Census boundaries; a tract can span more than one area.** Labels are display metadata and must not change scores or erase reviewer decisions.

## Cleaning and review rule catalogue

Confidence below concerns detection/action safety, not the probability of hunger. Thresholds labeled heuristic are prototype policy, not official standards. Safe formatting is recorded automatically; uncertain/meaning-changing decisions require named Accept/Reject/source-backed Edit with plain-English reasons and retained originals.

| Rule | Detection logic | Suggested action | Confidence | Exact plain-language explanation |
|---|---|---|---|---|
| R01 Format/encoding | File-specific UTF-8 BOM or documented cp1252; whitespace-only header suffix; ACS label row identified by non-tract `GEO_ID` and metadata | Preview deterministic import recipe; normalize header/remove label row from analysis, keep raw bytes and import log; stop on unexpected schema | High | “This file has an extra label row or formatting mark. We can standardize its format without changing the measurements.” |
| R02 Tract ID | Exact prefix + 11 digits; integer-looking `.0` only if exact and validated against source universe; leading-zero padding only when unambiguous | Propose normalized string; ambiguous/truncated/scientific-loss IDs quarantined for review, no guessed tract | High for exact formatting; low for damaged ID | “These sources name the same neighborhood differently. Here are the original and standardized IDs.” |
| R03 Duplicate/join cardinality | Duplicate observation key or many-to-many merge; compare raw payload hashes | Exact duplicate: propose one analytical instance with all source references; conflicting duplicate: require choice, no arbitrary first row | High | “Two rows share an ID. Joining them as-is could count this neighborhood twice.” |
| R04 Source codes | Match ACS annotation/code dictionary, e.g. `-`, `N`, `(X)`; do not blanket-parse all codes alike | Nullable numeric + exact source-code reason; do not impute or convert to zero | High when documented | “The source does not provide a usable number here. A blank does not mean zero.” |
| R05 Top/bottom-coded income | Terminal `+`/`-` documented as bound; distinguish from missing `-` | Preserve bound and source text; exclude from exact arithmetic requiring a point value | High | “This means at least $250,000, not exactly $250,000.” |
| R06 Impossible domain | Percentage outside [0,100], count negative, flag outside {0,1}, invalid CI ordering | Propose excluding invalid derived value from scoring while retaining raw; inspect unit/denominator; edit only with source evidence. **No winsorization/capping** | High detection; low replacement | “This percentage is outside the possible range. We will not guess the correct number.” |
| R07 Denominator/universe | Numerator and denominator periods or universes differ; zero denominator; population vs household vs adult mismatch | Block ratio; prefer direct ready-made ACS rate; keep alternatives separate and flag the derivation | High | “These numbers describe different populations or years, so dividing them could give a misleading percentage.” |
| R08 ACS imprecision | Positive estimate: `CV = (MOE90/1.645)/abs(estimate)` >0.30; heuristic. Zero estimate + positive MOE: uncertainty undefined, not perfect confidence. Missing MOE: unknown | Keep estimate/MOE; review only conclusions that depend on that indicator; do not throw away an entire tract because an unrelated income estimate is imprecise | High calculation; medium policy | “This estimate is imprecise. Its margin of error is large compared with the estimate.” |
| R09 PLACES uncertainty | Parse modeled 95% CI separately; width >20 percentage points or CI crosses the regional transport threshold (heuristic) | Retain modeled estimate/CI; lower confidence of transport inference; do not apply ACS MOE formula | Medium | “This modeled estimate has a wide range of plausible values. The transportation conclusion needs review.” |
| R10 Group quarters | `PCTGQTRS ≥25` custom caution; official flag/≥67 highlighted separately; zero population handled | Keep valid values; require context before household-focused recommendation; no institution-type guess or automatic data deletion | Medium | “Many residents live in group settings. These household measures may not describe everyone here.” |
| R11 Small geography | `0 < population_2020 <500` heuristic or poverty-universe/household denominator <100; zero-population tract separately | Review rather than label erroneous; exclude zero-base derived rate; never infer survey sample size from population alone | Medium | “This is a small neighborhood or reporting group. Percentages can change substantially with relatively few people.” |
| R12 Missing by design | FL transport/food insecurity absent per brief and file; ACS outside selected sample footprint | One coverage card per source/region + affected-tract count; no cell-level “fix” queue; leave null | High | “This indicator is not available for this community in the supplied data. We have not treated it as zero.” |
| R13 Unexpected missing | Expected row/field absent, failed numeric parsing or changed header not explained by coverage/code dictionary | Review import/lookup; block affected measure, not fabricate fill; missing row alone does not prove error | High anomaly; medium diagnosis | “We expected this field or row but could not use it. Please check the source or import.” |
| R14 Mixed/stale/unknown vintage | Component periods differ; reference end >3 years before run date triggers age caution (heuristic); release date is separate; unknown years explicit | Keep year badges and exact provenance; request newer public source if available; never relabel ACS 2020–24 as older just because USDA supplies it | High metadata; medium fitness | “These measures describe different years. The population base is from 2020; conditions may have changed.” / “The reference year has not been verified.” |
| R15 Source disagreement | Comparable same-universe/period poverty values differ by **>5 percentage points**, configurable; compare precise definitions first | Side-by-side source cells; review mapping/revisions, choose source with reason; never average. Same upstream ACS means no independent confirmation bonus | High difference; medium meaning | “Two comparable sources disagree by more than 5 percentage points. We have kept both rather than choosing silently.” |
| R16 Distribution outlier | Within community, valid measure beyond Q1−3×IQR or Q3+3×IQR, n≥20 and IQR>0 (heuristic) | Flag unusual observation, retain it; no clipping or deleting high-need tracts | Low as error evidence | “This value is unusual for this community. It may be correct; please check before changing it.” |
| R17 Definition sensitivity | LILA half/10 vs one/10 or driving vs straight-line flags differ | Keep default definition and show comparison; request acknowledgment if recommendation changes | High | “This neighborhood’s flag changes when we change the distance definition. That is a methodology choice, not a corrected data error.” |
| R18 Geographic coverage | Union of IDs produces missing source records; wrong county set, geography vintage mismatch or unmatched boundary | Preserve tract + limitation; quarantine incompatible geometry; require verified crosswalk before reallocating counts | High | “This source covers a different area or set of neighborhood boundaries. We have not dropped unmatched neighborhoods.” |


Summary details distinguish format records, analytical changes, cautions and coverage—not every flag is an error. Keep dense counts and methods expandable. Votes, resolution, undo, tract notes and operational actions append history; no last-writer-wins on disputed source changes.

## Optional AI and branding

Built-in reports and chat answers render immediately without any model request. Only explicit optional buttons call Gemini `gemini-3.8-flash`, in the background with a **20-second total cap**, no retries, bounded transport and ignored late results. Timeout/503/errors retain built-in text and a friendly unavailable note. Exact paragraph validation rejects invented facts and semantic swaps; the UI never awaits model work.

Follow supplied Beacon colors and permitted typography with declared fallbacks; do not reproduce/recolor unlicensed logo artwork. Label the app a prototype built for Beacon, **not an official DataKind product**. Public data only; no private inventory, routing, forecasting or deployment.

## Verification and delivery

Run `pytest` and `python -m evals.run --skip-gemini`. Nine mandatory suites cover rules/schema, Florida integrity, independent source cells, scoring/sensitivity, offline/AI responsiveness, human audit, full advanced workflow/export replay, quick checks and place labels. The live model row is explicitly SKIP when not attempted; do not count it as a pass. Verify the small lookup rebuild and source hashes with `python scripts/build_place_names.py --verify`.

Retake landing, map, quick-check and advanced workflow screenshots against port 8510 using real sources and clearly labeled simulated reviewer choices. Keep `app_v0_dashboard.py`. Before a normal approved push to origin main, scan tracked files and incoming history for secrets and raw source/boundary files. Never print a key; never deploy.
