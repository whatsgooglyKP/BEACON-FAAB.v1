# Architecture · Load → Review → Use

## 1. Load: immutable evidence, common fields

[`indicators.py`](../indicators.py) is the single source adapter for all three county sets. ACS label rows and exact `1400000US` prefixes are standardized; ambiguous IDs and conflicting duplicates are quarantined, not guessed. Each source is SHA-256 locked. A deterministic run ID includes source hashes, community, definition and configuration version.

`EvidenceBundle` contains an immutable wide baseline, long observations, coverage and manifest. Each observed cell retains its literal text, numeric view, missing reason/bound, source path/member/CSV row/column/hash, geography vintage, units, universe, reference years, release date and uncertainty. Poverty and household SNAP percentages come directly from ACS. USDA alternative poverty stays separate. Low-access share is a named derivation from the supplied low-access population and 2020 population, never an estimate of meals needed. PLACES adults and modeled 95% intervals never masquerade as household ACS rates/MOEs.

Outer concatenation preserves the tract-ID union. NYC's three ACS-only 9901 tracts remain with missing source reasons. Florida coverage limitations are declared once per region; nulls are not hundreds of “fixed errors.” The existing expanded eight-county dataset is not the default.

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

[`app.py`](../app.py) is a single three-step Streamlit workflow. Only immutable imports are cached; review state is read freshly from SQLite. Sidebar identity is a prototype display name. Every decision form passes the expected version. The current version keeps the original dashboard concept but removes the seven-tab maze, inventory upload and routing flow.

[`.streamlit/config.toml`](../.streamlit/config.toml) and [`assets/beacon.css`](../assets/beacon.css) apply the supplied palette and typography scale with declared unlicensed-font fallbacks. No official logo is recreated. Prototype attribution is explicit.

[`report.py`](../report.py) creates deterministic evidence packets. Optional Gemini may only reorder exact approved paragraphs, enforced by an exact paragraph-multiset gate: a number attached to the wrong indicator, unit, geography or year is rejected. Model exceptions/timeouts return the identical usable template. Bounded chat retrieves a packet for sources, missingness, the selected tract or public finders; it is not open-ended factual generation.

[`exports.py`](../exports.py) creates a local ZIP: readable CSVs plus a schema-bearing baseline JSON, manifest, observations, complete decisions, unresolved issues, notes, field dictionary, coverage and shortlist. Schema-bearing replay and the standard round-trip JSON float representation avoid CSV type inference, dropped leading zeros, and binary floating-point precision loss. The replay check requires exact numeric equality, not an approximate tolerance. `replay_export` reconstructs `reviewed.csv` from the baseline, proposals and append history without the database or raw source files. No export triggers external sharing.

## 6. Validation boundaries

[`tests/`](../tests/) supplies synthetic, independent acceptance fixtures and real-data scope/count checks. [`evals/run.py`](../evals/run.py) adds independently read raw source cells, byte hashes, rank oracles, sensitivity diagnostics, actual three-community Streamlit steps and complete export replay. Offline correctness and optional live-model availability are separate scorecard rows.

This prototype does not prove user impact, current service coverage, model calibration, production security or food shortages. A practitioner usability check, authenticated collaboration, verified resource catalogs and fresher data are next steps. Legacy files are preserved for reference but excluded from the live execution path.
