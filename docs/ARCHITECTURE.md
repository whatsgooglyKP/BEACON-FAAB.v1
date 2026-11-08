# Architecture · Load → Review → Use

## 1. Load: immutable evidence, common fields

[`indicators.py`](../indicators.py) is the single source adapter for the four Central Florida counties. ACS label rows and exact `1400000US` prefixes are standardized; ambiguous IDs and conflicting duplicates are quarantined, not guessed. Each source is SHA-256 locked. A deterministic run ID includes source hashes, community, definition and configuration version.

`EvidenceBundle` contains an immutable wide baseline, long observations, coverage and manifest. Each observed cell retains its literal text, numeric view, missing reason/bound, source path/member/CSV row/column/hash, geography vintage, units, universe, reference years, release date and uncertainty. Poverty and household SNAP percentages come directly from ACS. USDA alternative poverty stays separate. Low-access share is a named derivation from the supplied low-access population and 2020 population, never an estimate of meals needed. PLACES adults and modeled 95% intervals never masquerade as household ACS rates/MOEs.

Outer concatenation preserves the tract-ID union. Florida coverage limitations are declared once per region; nulls are not hundreds of “fixed errors.” The existing expanded eight-county dataset is not the default.

## 2. Check: suggestions are not changes

[`quality_rules.py`](../quality_rules.py) implements R01–R18 from the [design catalogue](../REDESIGN_PLAN.md#4-cleaning-and-review-rule-catalogue). Format/code rules can be automatically acknowledged; domain errors, bounds, denominator problems, imprecision, modeled uncertainty, group settings, small geographies, missingness, vintages, source disagreement, distribution outliers and definition sensitivity get explicit reasons and confidence in the check.

[`clean.py`](../clean.py) orchestrates import and detection, then attaches exact observation coordinates to tract-specific proposals. It does not fill missing percentages or cap ratios. Pending proposals cannot change the analytical baseline. Relevant and context-only flags are distinct: for example, imprecise income must not erase a usable poverty/access score.

## 3. Review: append-only consensus overlay

[`review_store.py`](../review_store.py) owns local SQLite tables:

- `runs`, `snapshots`, `proposals`: manifest, immutable observations/baseline, and versioned rule proposals.
- `events`: full proposal snapshot, reviewer, action, reason, evidence link, before/after, rule version, previous event/version and ET timestamp.
- `notes`: append-only tract context, not statistic edits.
- `recommendation_events`: separate operational need/action/order choices.

`decide` requires a name/reason; numeric Edit additionally requires a cited public HTTPS source or exact existing-source selection and domain validation. **A citation is reviewer-supplied evidence, not independently verified by the prototype.** Actual invalid baselines are always gated out of arithmetic, even if exclusion is rejected.

`fold` keeps the latest vote per reviewer while retaining all historical events. One vote is provisional; concordant votes are agreed; conflict is disputed. Resolution is explicit and new conflicting votes reopen it. `BEGIN IMMEDIATE` plus an expected proposal version refuses stale saves. Review status is reduced deterministically, with disputed/pending states stronger than an earlier acknowledgment. Names are unauthenticated; this is a sequential local demonstration, not an authorization system.

`apply` recomputes a reviewed view from the immutable baseline and consensus. Disputed or pending patches are withheld. Original observations and raw columns never change. Cautions remain visible after acknowledgment.

## 4. Use: an honest dashboard and separate human priorities

[`need.py`](../need.py) uses complete, valid poverty/access pairs as the selected community cohort. Each empirical percentile is `(average rank − 0.5) / n`, so ties have the same value. The score is `50 × (poverty percentile + continuous access percentile)`. Stable ordering is descending score then ascending tract ID. Missing required inputs stay unscored.

Appendix B classification adaptations are explicit: classic gaps require top-quartile poverty and driving LILA half/10; transport-compounded gaps require available top-quartile adult transport and LILA. A blind spot uses at least two continuous mid-high signals, none in the top quartile, and never auto-recommends a service. Small or collapsed cohorts do not get confident quartile labels. Overall evidence confidence is capped at Medium for the shared 2020 base; relevant imprecision/conflicts reduce it further.

Default dashboard rows require completed relevant review. Unreviewed scores are available only as labeled previews. Low-confidence places remain visible with Review required rather than disappearing. `operational_view` adds need challenges, action approvals/replacements, disagreement labels and human positions **without altering model score/rank**.

The map uses supplied PLACES neighborhood point coordinates, not retailer locations, pantry coverage or routes. Unmapped tracts remain in the table. Resource links come from the appendix and require manual follow-up.

## 5. Interface, reports and replay

[`app.py`](../app.py) opens an answer-first view with a preserved three-step advanced Streamlit workflow. Only immutable imports are cached; review state is read freshly from SQLite. Sidebar identity is a prototype display name. Every decision form passes the expected version. The current version keeps the original dashboard concept but removes the seven-tab maze, inventory upload and routing flow.

[`.streamlit/config.toml`](../.streamlit/config.toml) and [`assets/beacon.css`](../assets/beacon.css) apply the supplied palette and typography scale with declared unlicensed-font fallbacks. No official logo is recreated. Prototype attribution is explicit.

[`report.py`](../report.py) creates deterministic evidence packets. Optional Gemini may only reorder exact approved paragraphs, enforced by an exact paragraph-multiset gate: a number attached to the wrong indicator, unit, geography or year is rejected. The built-in report/answer renders first on every path; no client is constructed by default. Only explicit optional AI buttons start a daemon-backed `GenerationJob`, polled by a Streamlit fragment without awaiting it. Jobs have a 20-second total ceiling (19.5-second result deadline, at most 19-second transport, one SDK attempt, no retries); late results are ignored even if a transport ignores its timeout. Model exceptions/503/timeouts keep the identical visible template plus a friendly unavailable note. The bounded synchronous adapter is for CLI/evals only, never the UI. Bounded chat retrieves a packet for sources, missingness, the selected tract or public finders; it is not open-ended factual generation.

[`exports.py`](../exports.py) creates a local ZIP: readable CSVs plus a schema-bearing baseline JSON, manifest, observations, complete decisions, unresolved issues, notes, field dictionary, coverage and shortlist. Schema-bearing replay and the standard round-trip JSON float representation avoid CSV type inference, dropped leading zeros, and binary floating-point precision loss. The replay check requires exact numeric equality, not an approximate tolerance. `replay_export` reconstructs `reviewed.csv` from the baseline, proposals and append history without the database or raw source files. No export triggers external sharing.

## 6. Validation boundaries

[`tests/`](../tests/) supplies synthetic, independent acceptance fixtures and real-data scope/count checks. [`evals/run.py`](../evals/run.py) adds independently read raw source cells, byte hashes, rank oracles, sensitivity diagnostics, actual three-community Streamlit steps and complete export replay. Offline correctness and optional live-model availability are separate scorecard rows.

This prototype does not prove user impact, current service coverage, model calibration, production security or food shortages. A practitioner usability check, authenticated collaboration, verified resource catalogs and fresher data are next steps. Legacy files are preserved for reference but excluded from the live execution path.

## Readable views without changing evidence

[`presentation.py`](../presentation.py) is the display boundary: a copied, allowlisted table receives friendly headers/statuses, one-decimal display rounding, and ET timestamps. Internal columns are excluded. [`app.py`](../app.py) shows short Review reasons and keeps methods/counters in expanders. Canonical source columns, original literals, source hashes, full-precision scores and the export/replay schema are untouched; UI labels never feed back into analytical calculations.

## Answer-first entry point (before the advanced workflow)

[`shortlist.py`](../shortlist.py) adds an honest starting answer over the same automatically cleaned data. `priority_ids` mirrors the core midrank score exactly (tested against `need.rank`). `quick_checks` tests the ten point-estimate leaders one at a time at the low/high poverty bounds from their published 90% margin of error, recomputing the entire regional cohort. It selects only actual **membership** changes and caps the snapshot set at eight. No uncertainty endpoint becomes a measured value. The pristine Central Florida quick-check count is 8; other contenders and joint uncertainty are explicitly outside this bounded starting set.

[`app.py`](../app.py) opens the top-ten preview with a map, one-line explanations and a not-team-checked label. It caches only the candidate-selection snapshot; decisions are still loaded from SQLite on every rerun. Accept maps to the existing audited `Confirm need` action. Challenge maps to `Challenge need`; `working_shortlist` excludes only uncontested challenges and fills from the next source-ranked candidate. `shortlist_change` reports real entries/exits, or honestly says membership is unchanged. Repeated checks are not replenished into an endless queue. A disputed team choice stays visible with Low confidence. The quick form remembers the tract actually rendered; if another reviewer handles it before submission, the stale action is rejected rather than accidentally applied to the next option.

The **Advanced / full review** secondary views preserve the complete Load → Review → Use architecture, all 18 checks, append-only audit, source-backed numeric edits, notes, resolution, and exact exports. Working-list decisions are already part of the exported recommendation log. Quick answers never set `review_complete`, approve an analytical patch or remove a source record.

## Central Florida place-label boundary

The product now exposes **Central Florida only**, with no region selector. [`scripts/build_place_names.py`](../scripts/build_place_names.py) downloads official 2024 Census Florida places (incorporated places plus CDPs) and tract internal points into gitignored `data/geography/raw/`. It assigns each of the 490 retained tracts by its supplied map point; one unavailable map point uses its matching official tract internal point for naming only. No nearest-place or majority-area inference is made. Outside all place polygons, the label is “Unincorporated <County> County.” There are 307 place/CDP hits and 183 outside-place labels. Polygon-boundary ties, if present, use the lowest place GEOID and are explicitly recorded in the method.

[`place_names.py`](../place_names.py) validates and attaches the small committed [`tract_place_names.csv`](../data/clean/tract_place_names.csv) snapshot to copies of the analytical table and observations. The lookup and raw-source SHA-256 hashes are pinned in [`tract_place_names.sources.json`](../data/clean/tract_place_names.sources.json). The naming hash is a UI cache key and export provenance, not an analytical score input or a reason to erase earlier reviewer decisions. The builder can verify identical regenerated bytes; the runtime requires no GIS libraries or network.

Names are primary in tables, card selectors, notes, tooltips, inspectors, change messages and exports; tract GEOIDs stay alongside. The export contains the full label snapshot and annotations without replacing original proposal/source payloads. [`place_name_checks.json`](../data/clean/place_name_checks.json) records five independent official Census TIGERweb ACS2024 point queries, including an unincorporated point with no incorporated-place/CDP hit. The app repeats: **Place names are approximate labels from Census boundaries; a tract can span more than one area.** Mapping and score inputs are unchanged.
