# Beacon Evidence Review: human-in-the-loop cleaner redesign

**Status:** Phase 1 proposal, not an implementation. Prepared November 7, 2026 (ET). App and existing outputs unchanged; do not push or deploy. Approval of the design is the next gate.

**Goal:** Help a food-access team decide which public-data signals it can trust, understand limitations, and approve an evidence-backed next step—not merely produce a larger count of “problems fixed.”

## 1. What the new materials change

Three approaches considered:
1. **Recommended: deterministic checks + a human review queue + a small action shortlist.** Verifiable transformations; uncertain interpretation stays with people. Best fit for Beacon's trust, collaboration, and coordinated-action brief.
2. Automatic AI cleaner: quick-looking but cannot establish source truth, and risks silently changing valid unusual neighborhoods. Reject.
3. Full forecasting/routing platform: potentially useful later, but public samples have no current inventories, surpluses, deliveries, or shortage outcomes. Out of scope for this event.

Critical corrections to the existing project framing:
- Appendix B specifies **low-income AND low-access (LILA), ½ mile urban / 10 miles rural**, not the earlier 1/10-mile measure. Select the supplied **driving** definition consistently, label it, and retain straight-line as a sensitivity comparison. Never substitute a distance-only flag for LILA.
- SNAP stores are an **address list for optional manual lookup**, not a supplied tract-level retailer-density column, pantry capacity, or surplus source. Remove systematic store matching and private/example-inventory routing from the challenge demo; retain old code only as archived reference.
- Central Florida's absent transportation measure is a known coverage limitation, not hundreds of broken cells. Do not manufacture it or substitute “no car” as though it were the same concept.
- The USDA archive's filename says 2025, but its internal README says **initial release July 2026**. Official USDA documentation says poverty and SNAP housing-unit counts use **ACS 2020–24**, not unspecified “older years.” The earlier description of every USDA fill as older is incorrect.
- Direct ACS and USDA poverty agree exactly in **all 2,992 paired numeric records** across the three supplied regions. They are not independent corroborating sources. Cross-source conflict checks remain useful tests, but do not invent an observed conflict.
- USDA `TractSNAP` is ACS-derived, while `OHU2020` is a 2020 housing denominator. Their ratio is not interchangeable with ACS's ready-made household SNAP percentage. An impossible derived ratio should be investigated, **not capped at 100 and called corrected**.
- A group-quarters share cannot identify a dorm, prison, military base, or care home on its own. Avoid naming any one without evidence. USDA's own high-group-quarters flag is **≥67%**; a proposed 25% review threshold is our heuristic, not USDA's rule.

## 2. Verified inventory: all 12 example-folder files

Read the full main brief, Appendix B/C and all five pages of brand-guideline text. Listed the complete example folder (12 files; no continuation token). Seven core files were already local and have byte sizes matching the fresh Drive listing; downloaded the remaining employment archive, mortgage workbook, and three PDFs to `data/beacon/`. Inspected CSV headers, column dictionaries, full regional counts, workbook README/data, and PDF text. No new app code was written.

### Files, fields, vintages and geography

| Drive filename → local path under `data/beacon/` | Indicators / actual contents | Observation period; geography; gap |
|---|---|---|
| Total Population.zip → `pop.zip` | ACS S0101 total population, age/sex counts/percentages, estimate/MOE pairs; data + metadata + notes | ACS five-year **2020–24**; 3,085 tract records plus one label row; regions below |
| Population - Below Poverty Level.zip → `poverty.zip` | ACS S1701 population with poverty status determined, below-poverty count, **ready-made poverty %**, MOEs; metadata/notes | ACS 2020–24; same 3,085 tract IDs; poverty universe is not total population |
| Households and Households Receiving SNAP Census, S2201.zip → `snap.zip` | ACS S2201 households, SNAP household counts, **ready-made SNAP %**, MOEs; metadata/notes | ACS 2020–24; same 3,085 tract IDs; household denominator |
| Household Income, Median.zip → `income.zip` | ACS S1901 household income estimates/MOEs, income distribution; metadata/notes | ACS 2020–24; same 3,085 tracts; median household ≠ median family income |
| Employed and Unemployed, 16+ Labor Force.zip → `employment.zip` | ACS B23025 employment/labor force counts and MOEs; three members | ACS 2020–24; 3,085 tracts; optional context, not a food-need score input |
| Low Grocery Access - 1/2 or 10 miles_2025-sram-fara-data.zip → `fara2025.zip` | Three national data tables: general characteristics (population, occupied housing, urban, poverty, group quarters, SNAP counts), driving-distance access, straight-line access; three lookup CSVs + README | **84,119 tracts**, 2020 tract IDs; initial release July 2026. Population/occupied housing/group quarters 2020; poverty/low-income/SNAP counts ACS 2020–24; access uses June 2025 retailer snapshot, 2020 population allocation and 2025 urban definitions. Mixed component vintages are metadata, not automatically errors |
| Transportation_PLACES__Census_Tract_Data_(GIS_Friendly_Format),_2025_release .csv → `places.csv` | **83,522 rows × 88 fields** nationally; `LACKTRPT_CrudePrev` and 95% CI; also food insecurity, adult food-stamp prevalence and other modeled adult health indicators; tract ID/geolocation | Release 2025, 2020 tract linkage. Underlying survey/model years are **not encoded in this CSV**: display “reference years unverified” until checked against release documentation. Do not equate release year to observation year; model CI ≠ ACS MOE |
| SNAP_Retailer_Location_data.csv → `snap_retailers.csv` | **248,872 address records × 17 fields**; name, address, type, lat/lon, city/state/county; **no tract ID** | National point/address geography; snapshot date not in file. Manual lookup only; cannot infer present stock, pantry access, store hours or retailer density by tract |
| mortgage_denials_originations_by_tract.xlsx → same name | README + Data; **3,260 rows**: originations, denials, totals, ready-made denial ratio | README: HMDA **2025 activity year**; 7-county Central FL (includes Marion, not Polk/Sumter), five NYC boroughs, Salt Lake County only. 538 ungeocoded applications excluded per README. Challenge 1 only |
| Small Business FL.pdf → `Small_Business_FL.pdf` | **2024 CRA MSA** loan-originations report; count/amount bands and borrower-revenue bands; tract rows plus subtotals | Orlando–Kissimmee–Sanford MSA 36740, Lake/Orange/Osceola/Seminole. Challenge 1 only; not a clean SBA tract CSV |
| Small Business NY.pdf → `Small_Business_NY.pdf` | Same 2024 CRA report format | New York–Jersey City–White Plains MSA division 35614; five borough counties **plus Putnam/Rockland/Westchester**. Must not silently treat all rows as NYC |
| SmallBusinessUtah.pdf → `SmallBusinessUtah.pdf` | Same 2024 CRA report format | Salt Lake City–Murray MSA 41620, Salt Lake **and Tooele** counties. Challenge 1 only |

The three PDF-derived `.txt` files are inspection artifacts, not new source datasets. Auxiliary financial data is inventoried but not fed into food-access logic.

### Per-community coverage measured from the actual files

All five ACS archives share the same regional coverage. Counts below exclude the descriptive label row. PLACES counts are existing rows, not automatically all census tracts.

| Region / explicit county FIPS | ACS tract rows | USDA rows | PLACES rows | Numeric poverty % / SNAP % | Numeric transportation / food insecurity |
|---|---:|---:|---:|---:|---:|
| **Central FL supplied:** Lake 12069, Orange 12095, Osceola 12097, Seminole 12117 | **490** | **490** | 489 | **488 / 488** | **0 / 0** |
| **NYC:** Bronx 36005, Kings 36047, New York 36061, Queens 36081, Richmond 36085 | **2,327** | **2,324** | **2,231** | **2,239 / 2,231** | **2,231 / 2,231** |
| **SLC supplied metro sample:** Salt Lake 49035 + Tooele 49045 | **268** (251 + 17) | **268** | **265** | **265 / 265** | **265 / 265** |
| Existing app's **expanded Central FL**, additionally Brevard/Polk/Sumter/Volusia | **490** | **968** | **962** | **488 / 488** | **0 / 0** |

- Recommended default is **the supplied 490-tract Central FL footprint**, not silently changing it to eight counties. Offer the existing 968-tract expansion only later, explicitly labeled “ACS coverage incomplete: 478 tracts outside supplied sample.” This is a scope mismatch, not a statewide missing-data problem.
- Preserve the **union** of valid tract IDs, not an inner join. NYC has three ACS-only 9901 tracts: `36047990100`, `36081990100`, `36085990100`; poverty is `-` in each. Retain them visibly as insufficient data; do not guess that they are join failures or delete them.
- Raw `-` values account for missing direct poverty/SNAP percentages: FL 2/2; NYC 88/96; SLC 3/3. Preserve their source-coded meaning rather than filling zero.
- USDA driving LILA ½/10 flags: **157/490 FL**, **37/2,324 NYC**, **48/268 SLC**. Straight-line flags: **118**, **7**, **29**. These are raw flags, not approved high-need totals.
- Switching driving LILA from 1/10 to ½/10 changes **76 FL, 24 NYC, 40 SLC** tract flags. This is a substantive definition decision, not cosmetic cleaning.

## 3. Common indicator schema (identical adapters for every community)

Use a source-observation layer plus a reviewed wide export. One observation key is `(community_id, tract_id, geography_vintage, indicator_id, source_id, reference_period, definition_id)`. Maintain alternative observations, not one overwritten “best” value.

Each observation carries `value_raw`, `value_numeric`, `unit`, `universe`, `denominator_field`, `source_file`, `source_member`, `source_column`, `source_row`, `source_sha256`, `release_date`, `reference_start/end`, `missing_reason`, `estimate_kind`, `moe90`, `ci95_low/high`, `quality_flags`. Geography vintage is explicit, even if all current inputs align. Suggested actions are separate from observations; `reviewed_value`/`selected_source` only reflect the decision overlay.

| Canonical field | Same source mapping for FL, NYC, SLC | Unit / restriction |
|---|---|---|
| `tract_id`, `tract_name`, `county_fips` | ACS `GEO_ID`/`NAME`; USDA `CensusTract20`; PLACES `TractFIPS` | 11-digit **string**, county first five; strip exact `1400000US` prefix only; never fuzzy-join by tract name |
| `population_acs`, `population_2020` | S0101 `S0101_C01_001E/M`; USDA `POP2020` | Persons; separate measures, never overwrite one with the other |
| `poverty_pct`, `poverty_moe90` | S1701 `S1701_C03_001E/M` | % persons with poverty status determined; source preference direct ACS; USDA `PovertyRate` retained as alternate, same ACS period but no supplied MOE |
| `households_acs`, `snap_households_acs`, `snap_pct`, `snap_moe90` | S2201 `S2201_C01_001E`, `S2201_C03_001E`, **`S2201_C04_001E/M`** | Household count/%; ready-made percentage preferred. Never divide by 2020 occupied housing to recreate it |
| `lila_half10_driving` | `DD_SRAM_LILATracts_halfAnd10` | Nullable bool; low-income **and** low-access flag |
| `low_access_half10_driving` | `DD_SRAM_LAhalfand10` | Separate distance-only flag, not LILA |
| `low_access_population_half10`, `low_income_low_access_population_half10` | `DD_SRAM_LAPOP05_10`, `DD_SRAM_LALOWI05_10` | Persons, model/spatial estimates; population base 2020; not measured hunger or meals needed |
| `low_access_population_pct_half10` | `100 * DD_SRAM_LAPOP05_10 / POP2020` when denominator >0 | Derived population share, explicitly labeled; invalid range → review, no cap |
| `lila_half10_straight`, `lila_one10_driving` | `SD_SRAM_LILATracts_halfAnd10`, `DD_SRAM_LILATracts_1And10` | Comparison definitions, never spliced into default column |
| `transport_lack_pct`, `transport_ci95` | PLACES `LACKTRPT_CrudePrev/Crude95CI` | Modeled **adults**; FL null + `not_available_for_region`; NYC/SLC populated where present |
| `food_insecurity_adult_pct` | `FOODINSECU_CrudePrev/Crude95CI` | Optional context; not required common ranking input; same FL gap |
| `group_quarters_pct`, `group_quarters_usda_flag`, `urban` | `PCTGQTRS`, `GroupQuartersFlag`, `Urban` | Percent 0–100; official group-quarters flag ≥67%; custom ≥25% caution separately named |
| `median_household_income`, `income_moe90`, `income_bound` | S1901 `S1901_C01_012E/M` | Dollars; `250,000+` stays a lower bound, not exact $250,000; USDA median **family** income separate |
| `retailer_lookup` | Separate address table; no per-tract field | Optional manual reference only; all cities same restriction |

`missing_reason` enumeration: `not_available_for_region`, `outside_supplied_sample`, `suppressed_or_unavailable_source_code`, `not_applicable`, `source_row_absent`, `parse_error`, `invalid_value`, `unverified_definition`. An unclassified blank stays `source_reason_unknown`, never silently “not applicable.”

## 4. Cleaning and review rule catalogue

**Confidence below concerns detection/action safety, not a probability that a neighborhood needs food.** Keep severity, confidence and review state separate. Thresholds labeled “prototype heuristic” are adjustable policy, not official USDA/ACS standards. Every suggested action has Accept/Reject/Edit and a reversible decision; flags need acknowledgment/context, not invented replacement numbers.

| Rule | Detection logic | Suggested action | Confidence | Exact plain-language explanation |
|---|---|---|---|---|
| R01 Format/encoding | File-specific UTF-8 BOM or documented cp1252; whitespace-only header suffix; ACS label row identified by non-tract `GEO_ID` and metadata | Preview deterministic import recipe; normalize header/remove label row from analysis, keep raw bytes and import log; stop on unexpected schema | High | “This file has an extra label row or formatting mark. We can standardize its format without changing the measurements.” |
| R02 Tract ID | Exact prefix + 11 digits; integer-looking `.0` only if exact and validated against source universe; leading-zero padding only when unambiguous | Propose normalized string; ambiguous/truncated/scientific-loss IDs quarantined for review, no guessed tract | High for exact formatting; low for damaged ID | “These sources name the same neighborhood differently. Here are the original and standardized IDs.” |
| R03 Duplicate/join cardinality | Duplicate observation key or many-to-many merge; compare raw payload hashes | Exact duplicate: propose one analytical instance with all source references; conflicting duplicate: require choice, no arbitrary first row | High | “Two rows share an ID. Joining them as-is could count this neighborhood twice.” |
| R04 Source codes | Match ACS annotation/code dictionary, e.g. `-`, `N`, `(X)`; do not blanket-parse all codes alike | Nullable numeric + exact source-code reason; do not impute or convert to zero | High when documented | “The source does not provide a usable number here. A blank does not mean zero.” |
| R05 Top/bottom-coded income | Terminal `+`/`-` documented as bound; distinguish from missing `-` | Preserve bound and source text; exclude from exact arithmetic requiring a point value | High | “This means at least $250,000, not exactly $250,000.” |
| R06 Impossible domain | Percentage outside [0,100], count negative, flag outside {0,1}, invalid CI ordering | Propose excluding invalid derived value from scoring while retaining raw; inspect unit/denominator; edit only with source evidence. **No winsorization/capping** | High detection; low replacement | “This percentage is outside the possible range. We will not guess the correct number.” |
| R07 Denominator/universe | Numerator and denominator periods or universes differ; zero denominator; population vs household vs adult mismatch | Block ratio; prefer direct ready-made ACS rate; keep alternatives separate and flag the derivation | High | “These numbers describe different populations or years, so dividing them could give a misleading percentage.” |
| R08 ACS imprecision | Positive estimate: `CV = (MOE90/1.645)/abs(estimate)` >0.30; heuristic. Zero estimate + positive MOE: uncertainty undefined, not perfect confidence. Missing MOE: unknown | Keep estimate/MOE; review only conclusions that depend on that indicator; do not throw away an entire tract because an unrelated income estimate is imprecise | High calculation; medium policy | “This estimate is imprecise, which can happen with a small sample. Its margin of error is large compared with the estimate.” |
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

Summary counters must distinguish **format standardizations**, **proposed value changes**, **accepted value changes**, **review cautions**, **coverage limitations**, and **unique tracts affected**. One tract can have several cautions; do not imply every caution was a data error or was fixed. Acceptance of a limitation is not resolution of missing information.

## 5. One-page workflow: Load → Review → Use

### Load: choose community, inspect coverage
- Community selector defaults to supplied Central Florida; NYC and SLC use the same adapters/rules. Show county names, source periods, usable rows and missing-by-design measures before any cleaning.
- Lock raw files by SHA-256; create run ID, manifest and rule/configuration version. No networking or Gemini needed to import, run checks, review or export.

### Review: a prioritized queue, not seven tabs
- Three summary cards: **Needs a decision**, **Cautions to understand**, **Ready to use**. Default queue: blocking ID/domain/duplicate issues, then recommendation-affecting uncertainty/conflicts. Group repeated source limitations once; allow drilldown to affected tracts.
- Each review card shows neighborhood, indicator, original source cell, proposed analytical value/action, source link/period/universe, High/Medium/Low action-confidence badge, plain-language reason, and impact preview (“this would change its rank/gap classification”).
- **Accept / Reject / Edit**, reviewer display name, note and evidence link. Require a name and note for every decision; Edit needs a cited public source or chooses an existing source observation. Validate edited unit/domain; never let an unsupported numeric guess masquerade as source-backed. Local knowledge may challenge an inference or add a caution, but does not rewrite an official number.
- Bulk Accept only a selected, fully previewed homogeneous set of high-confidence format/code rules; retain one audit event per proposal. No “fix all” for statistical or contextual cautions.
- Reject keeps the original observation, not an invalid score: validation gates still prevent impossible values entering calculations. Pending value changes remain unapplied. Rejected proposals and unresolved limitations stay visible.
- Add a tract note/flag independently of fixing a number. Recommendation card separately supports **Confirm need / Challenge need**, and **Approve / Reject / Replace action / Move up/down** with a reason. Changing operational priority never rewrites measured need or the algorithmic order.

### Disagreements, storage and audit
- Local SQLite prototype: observations/manifest, proposals, append-only decisions, tract notes, recommendation decisions, resolutions. Reviewer names are **self-entered prototype identities**, not authenticated accounts; local persistence supports a sequential two-reviewer demonstration, not a claim of production multi-user collaboration.
- A proposal starts `pending`; one decision is `accepted_provisional` or `rejected_provisional`. A different named reviewer's conflicting action/value yields `disputed`, regardless of who saved last. Repeated reviewer changes append a new version rather than deleting history.
- Disagreement view shows both reviewers, notes, values and ranking effects side-by-side. Explicit resolver name + reason can select an existing alternative or create a source-backed edit; old votes remain. New conflicting votes reopen dispute. Do not silently majority-vote or overwrite.
- A disputed value patch is not applied in the consensus export; return to validated baseline and mark dependent recommendations “Review required.” If baseline itself is invalid, analytical value stays null. Single-reviewer output is labeled provisional; agreed two-reviewer output is labeled agreed, not universally true.
- Every event records proposal/rule/config versions, source hash/row/column, before/after, reviewer, note, decision, previous event/version, timestamp with zone and any resolution. Optimistic-version checks prevent stale saves. Display timestamps in ET.
- Export bundle: original-source manifest (no secrets), cleaned observation/wide CSV, decisions and unresolved/disputed issues CSV, tract notes, field dictionary/coverage, action shortlist and deterministic health report. Include raw columns and selected-source IDs; original files remain unmodified locally. The bundle must replay to exactly the exported dataset. No automatic external sharing.

## 6. Small downstream need view with explicit confidence

Use a **ranked list first**, optional map second. Wording: “places to review for food-access support,” not predicted shortages, confirmed hunger, eligible nonparticipants or surplus opportunities.

- Common cross-community ranking: poverty percentage + low-access population share (both available conceptually in all three regions). On valid base data, compute within-community midrank percentiles; `priority = 50 * (poverty_percentile + access_percentile)` where percentiles are 0–1. Equal values share percentile; stable sort by score then tract ID. Publish two input values, weights, cohort size and method. Missing either required measure → **unscored / needs information**, never zero or silently reweighted.
- Scores compare tracts **within the selected community**, not FL vs NYC as an absolute national need scale. Optional NYC/SLC transport is a separate context badge/classification; it does not change the common two-input score. Avoid rewarding or penalizing Florida for missing transport.
- “Classic food access gap” (Appendix B's Classic Food Desert): poverty ≥ selected community's 75th percentile **and** driving LILA half/10=true. “Transport-compounded” only where transport exists, driving LILA=true and transport ≥ its 75th percentile; using LILA here is a conservative explicit adaptation of the appendix's low-access wording. Show both types when both apply.
- “Possible blind spot”: no available core measure reaches its 75th percentile, and at least two lie in [50th,75th) percentiles; FL core is poverty + continuous low-access population share, NYC/SLC may also use transport. **This is an explicit adaptation:** a binary LILA flag cannot meaningfully supply a second-highest quartile, so use a clearly labeled continuous access share. Always Review required; never auto-recommend a service.
- Small cohort (<20 complete observations), collapsed quartile thresholds, zero IQR or unresolved comparable-source conflict → no confident quartile classification; show insufficient differentiation/information instead of forcing a group.
- Confidence is a **rule-based evidence-quality label**, not a calibrated prediction probability: High = needed inputs validated, no relevant uncertainty/context blocker; Medium = usable inputs but relevant vintage/sensitivity/unknown uncertainty caution; Low = uncertain required input or unresolved conflict. Missing/invalid required inputs → insufficient evidence. Shared 2020-base caution remains visible and caps overall confidence at Medium until fit-for-purpose reviewed; acknowledgment never makes data newer.
- Do not discard a tract because any unrelated field has high CV. Relevant low-confidence tracts remain visible in a review-required section so weak data does not erase potentially underserved places.
- Actions are categories plus verified **public resource finder links** from Appendix B: pantry/mobile pantry for classic gaps; mobile/delivery/transit-accessible options for transport gaps. No “nearest” facility unless an actual public catalog/location has been verified; no capacity/coverage claim from a retailer address.
- Display model recommendation and human operational priority side-by-side, with review tier, approvals/challenges and reasons. No automated dispatch.

Gemini may summarize a fixed, validated evidence packet after checks; cannot clean, fill, choose sources, resolve disagreements or compute scores. Deterministic template is the default fast path; optional Gemini timeout/failure uses it. Numeric, unit, geography, period and caveat checks must gate generated text. No key is printed or included in exports.

## 7. Evaluation changes (retain one-command scorecard)

Keep `.venv/bin/python -m evals.run`; redesign the seven suites without claiming legacy passes validate this design. Tests use independent fixtures/reference computations, not the production function as its own oracle.

| Suite | New acceptance checks |
|---|---|
| 1. Rules/schema | Fixtures for every rule; exact BOM/label handling and tract preservation; domain-invalid shares **not capped**; top-coded income bound intact; suppressed code reason preserved; zero estimate/MOE behavior; adults vs households vs persons; direct ACS percentages selected; no mixed-denominator SNAP fill; imprecision on irrelevant income must not erase valid poverty/access |
| 2. Real-data integrity/coverage | Hash raw files before/after; same key union before/after; no many-to-many multiplication; source values untouched; every applied change explained by accepted decision; correct 490/2,327/268 scope, 3 NYC ACS-only rows retained, regional missingness explicit. Expanded 968 fixture remains separately labeled with USDA population 4,688,329, not a universal invariant |
| 3. Independent source checks | Stratified source-cell comparison: at least 10 tracts **per community**, including missing codes, unmatched NYC IDs, high group quarters, direct SNAP %, LILA urban/rural and both distance methods. Verify same-vintage poverty equality on 2,992 numeric pairs; seeded perturbation >5 points must trigger disagreement |
| 4. Gap/rank confidence | Four Appendix B scenarios plus threshold ties/zero-IQR/small cohort; CF transport absent never becomes zero or Transportation Gap; missing mandatory fields stay unscored; geography/definition swaps change version and warnings; run noise and MOE-aware sensitivity, report actual changes rather than demanding unrealistic invariant top ten. Equal inputs/decisions reproduce exact rank; human reordering does not alter model score |
| 5. Report faithfulness | Offline template always required; Gemini separately PASS/FAIL/SKIP with attempt counts. Tests match each number to the **right indicator, geography, units, definition and year**; reject invented eligibility, institution type, pantry stock and “all fixed” wording. Simulated 503/timeout gives identical usable fallback; a skipped live model is not a pass |
| 6. Human review/audit (replaces demo routing) | Accept/Reject/Edit/undo; mandatory reviewer/note/evidence; unsupported edit rejected; no unapproved patches; same-reviewer revision retained; two-reviewer disagreement in both save orders; no last-writer-wins; disputed patch withheld, resolution and reopening preserved; stale update conflict; persisted restart; full audit replay matches export |
| 7. End-to-end/exports | Load→review→use for all three regions; sequential reviewers disagree/resolve; export CSV round-trip keeps leading-zero IDs and null reasons; rejected/contested items visible; no private-data upload or stock-routing demo; report/template works offline and without Gemini; counts in UI, queue, audit and exports reconcile |

Add a 5-minute usability check with Kevin: can he explain one flag, find its source/year, reject a proposed change, recognize a disagreement, and explain why a shortlist item appears without help? Record completion/confusions as qualitative findings, not validated user impact.

## 8. Build order, effort and deadline guardrails

Estimate **8–11 focused hours** for a credible prototype plus **1–2 hours** for demo materials/regression buffer. Not a production multi-user product. Target finish **Sunday November 8, 2026, 2:30 PM ET**, hard submission **3:30 PM ET**. No push/deploy without Kevin's explicit approval.

| Stage | Files / responsibility | Estimated time; gate |
|---|---|---|
| 1 | `data_manifest.json`, `indicators.py` source adapters/schema; immutable inputs; scope and definition corrections | 1.5–2 h; all three communities reconcile and source mappings verified |
| 2 | `quality_rules.py`, rule fixtures; `clean.py` becomes orchestration, not hidden alteration | 1.5–2 h; rule and integrity checks pass |
| 3 | `review_store.py`, `review.py`, review-state tests; append-only SQLite overlay and disputes | 1.5–2 h; decisions survive restart, replay and conflict tests pass |
| 4 | `app.py` single-page Review-first UI; `need.py` transparent ranking/gap types; existing `routing.py` not used in demo | 1.5–2 h; one honest end-to-end reviewer story works |
| 5 | `report.py`, `evals/`, `EVALS.md`, README; three-community smoke/export/semantic checks and brand styling | 2–3 h; real result scorecard, no blanket “all passed” if skipped |

**Cut first if short:** Gemini live generation, map, bulk decisions, arbitrary upload schema inference, extended eight-county coverage, optional health/income/employment displays, rich resource catalogs. Keep all-community adapters/evals but showcase Florida first. Keep source traceability, correct LILA, no unsafe fills, Accept/Reject/Edit, audit and a minimal sequential two-reviewer disagreement demonstration. If the disagreement demo cannot be tested reliably, explicitly call collaboration a prototype/next step rather than silently suggesting production support.

**Brand:** Beacon Primary 900 `#1E343F` headings; Primary 700 `#385981` controls; Orange `#F79122` CTA; error `#C44A4A`, success `#388D58`, info `#4A7CD0`. Avenir Medium/Roman if licensed/available, otherwise declared sans-serif fallback; Menlo/monospace for IDs. 16px/1.5 body, 14px secondary; icons/text accompany colors. Use official logo only if available, without distortion/recoloring, with icon-height clear space; otherwise plain Beacon text. Don't imply DataKind approval.

**Demo success story:** Made: a reviewable evidence pipeline and a small approved action list. Learned: missingness, geography and definitions matter more than an impressive “fixed” counter; same-vintage USDA poverty isn't older independent data; community expertise should challenge inference, not overwrite statistics. Next: practitioner threshold calibration, verified resource catalogs, authenticated collaboration and newer public data. Forecasting and real inventory routing require separate validated data and authorization outside this public-data event.

## Sources and verification boundary

- Main brief: https://docs.google.com/document/d/1UFeoveMyn0UYYCc3oj4fVDRtXSA5nHvSzRTJfswc_Do/edit
- Appendix B/C: https://docs.google.com/document/d/1L25DTxI31BlrH3QvB7k8H0rt6eowMiYA3YqHEwfJer0/edit
- Brand PDF: https://drive.google.com/file/d/1KZY4wAevNOpc0kg6owQqYE42hqKYrB2J/view
- Full 12-file inventory: https://drive.google.com/drive/folders/1zuwSZjkK3gcvEzNFPJ8THFRw9ulCgA-p
- USDA period/definition validation (opened this turn): https://www.ers.usda.gov/data-products/food-access-research-atlas/documentation/snap-authorized-retailer-access-map-reference-guide
- Exact local source headers/metadata/README and pandas counts support the inventory above. Existing README/EVALS.md read for current behavior claims; no deep code investigation or app modification performed. PLACES underlying survey years and retailer-list snapshot date remain unverified and explicitly labeled, not guessed. No new eval suite was run because this phase is design/data inventory only.
