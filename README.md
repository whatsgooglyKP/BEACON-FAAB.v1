# Beacon · Evidence Review

**Top 10 → Quick checks → Advanced review:** a public-data prototype built for Beacon, DevFest Florida 2026, DataKind Challenge 2. This is **not an official DataKind product**.

Food-access teams need more than a map: they need to know which evidence is usable, why a signal was flagged, and how teammates reached a decision. This application safely standardizes public files, starts with an explicitly unreviewed top ten, and offers a few consequential quick checks plus the complete reviewed-only dashboard. It does **not** predict shortages or route food.

## Run locally

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/streamlit run app.py --server.port 8510
```

Open http://localhost:8510. No Gemini key is needed for importing, checks, review, maps, templates, or exports. SQLite decisions are saved under `data/review/` (gitignored); set `BEACON_REVIEW_DB` to a different local file for a separate workspace.

### Public data setup

The supplied source files are **not redistributed in this repo**. Obtain them from the [Beacon example folder](https://drive.google.com/drive/folders/1zuwSZjkK3gcvEzNFPJ8THFRw9ulCgA-p) and place/extract them as follows (retain the CSV names inside each archive):

| Supplied file | Local destination |
|---|---|
| Population – Below Poverty Level.zip | `data/beacon/poverty/ACSST5Y2024.S1701-Data.csv` |
| Households and Households Receiving SNAP Census, S2201.zip | `data/beacon/snap/ACSST5Y2024.S2201-Data.csv` |
| Total Population.zip | `data/beacon/pop/ACSST5Y2024.S0101-Data.csv` |
| Household Income, Median.zip | `data/beacon/income/ACSST5Y2024.S1901-Data.csv` |
| Low Grocery Access – 1/2 or 10 miles_2025-sram-fara-data.zip | `data/beacon/fara2025/` with General Tract Characteristics, Driving Distance, and Straight Line Distance CSVs |
| Transportation_PLACES…2025 release.csv | `data/beacon/places.csv` |

No address-level retailer join, private upload, financial-challenge file, or inventory is needed. A missing required file or changed schema fails visibly instead of generating demonstration numbers. `data_manifest.json` records the source hashes and scope used for verification.

## The advanced workflow

The default landing view is the explained top ten and map. Open **Advanced / full review** to use the complete workflow below.

1. **Load:** Central Florida only (Lake, Orange, Osceola and Seminole counties); there is no region selector. See units, periods, coverage, raw hashes and the exact definition before proceeding.
2. **Review:** safe formatting and documented missing-code handling are automatic and logged. Everything uncertain stays visible with a reason, action confidence, original cell/year/universe, and Accept/Reject. Source-backed numeric Edit is available on actual value/exclusion proposals; interpretation edits belong in tract notes, not fabricated statistics. Every human decision needs a display name and reason.
3. **Use:** the dashboard remains: explained rank, evidence-quality label, simple point map, and resource-finder links. **Only fully reviewed tracts appear by default in this advanced dashboard** (not the explicitly unreviewed landing preview). A separate, explicitly unreviewed preview keeps uncertain neighborhoods visible. The score never claims an operational action is approved.

### Collaboration and recommendation controls

Reviewer names are **self-entered and unauthenticated**. This demonstrates sequential collaboration on one local database, not production multi-user access. Conflicting named votes create a dispute, contested patches are withheld, and an explicit named resolution is required; new conflicting votes reopen it. Undo and revisions append history rather than deleting it. A stale form cannot overwrite newer decisions.

Add tract notes; confirm/challenge an inferred need; approve/reject/replace a proposed action; or set a human operational position. Human priority is shown **beside** the model rank and never rewrites its inputs. Conflicting operational choices are surfaced too. Exports include the baseline, observations, raw values, source coordinates/hashes, null reasons, all decisions, unresolved issues, notes, field dictionary, coverage, shortlist and offline health report; `exports.replay_export` reconstructs the reviewed view.

## Evidence, not overclaiming

- **Appendix B LILA:** low-income **AND** low-access, **½ mile urban / 10 miles rural, driving**. Straight-line and 1-mile alternatives are separate sensitivity measures.
- Source flags: **157/490 Central Florida tracts**. These are not confirmed high-need totals.
- Among FL's 157 flagged tracts, **129 poverty/SNAP estimates** have CV >30% (76 poverty, 53 SNAP), across **97 distinct tracts**. These are estimates, not 129 neighborhoods. One additional zero SNAP estimate with positive MOE has undefined CV and is separately cautioned. See [verified counts](PROBLEM_STAT_COUNTS.json).
- ACS figures are **2020–24**. USDA poverty shares that upstream ACS source: agreement is not independent corroboration. Population allocation is **2020**, retailers **June 2025**, USDA initial release **July 2026**. PLACES is a **2025 release with unverified observation years**.
- Transportation and supplied food-insecurity estimates are unavailable for Central Florida; missing is not zero. No car/housing-unit count is substituted for modeled adult transportation.
- Direct ready-made ACS percentages are preferred. `TractSNAP / OHU2020` mixes universes/years and is never a corrected SNAP percentage. Impossible values are excluded from calculation, **not capped**. Income bounds remain bounds; group settings are not labeled as a specific institution.
- Score: `50 × (poverty midrank percentile + low-access-population-share midrank percentile)`, within the selected community; missing either input means unscored. All input values, weights and cohort size are shown. Quartile classifications are withheld for small/undifferentiated cohorts.
- Confidence concerns **evidence quality**, not the probability of hunger. The shared 2020 population-base caution caps current confidence at Medium. Acknowledgment does not make data newer. Unrelated income imprecision never erases valid poverty/access evidence.
- Resource finders come from Appendix B. No nearest pantry, eligibility, current stock, verified coverage, or dispatch is inferred. “High poverty but low SNAP participation” is a potential signal, not evidence that someone qualifies but is not enrolled.

## Evaluation and documentation

```bash
.venv/bin/python -m pytest -q tests
.venv/bin/python -m evals.run                 # nine mandatory suites; live Gemini separately
.venv/bin/python -m evals.run --skip-gemini   # explicitly offline
.venv/bin/python -m evals.run --only 5        # report/fallback and optional model
```

[Latest scorecard](evals/results/latest.md) · [How the evaluations work](EVALS.md) · [Architecture and file tour](docs/ARCHITECTURE.md) · [Approved redesign](REDESIGN_PLAN.md) · [Requirements completion notes](docs/IMPLEMENTATION_STATUS.md).

Optional `GEMINI_API_KEY` is read only from the environment. Reports and chat show the built-in write-up immediately, without making a model request. The explicit **Generate AI summary (optional, Gemini)** / **Generate AI answer (optional, Gemini)** buttons use `gemini-3.8-flash` in the background with a **20-second total wall-clock cap**, one SDK attempt (no retries), and exact paragraph semantic validation. The transport timeout is at most 19 seconds; a 19.5-second result deadline leaves a rendering margin below 20 seconds. Late results are discarded. It can explain a fixed public evidence packet and resource finders, **not** freely generate facts, clean values, compute ranks or resolve votes. On timeout, 503, invalid output or any error, the built-in text stays visible and a friendly note says the AI summary is unavailable. No spinner blocks the UI. Do not commit a key or `.env` file.

## Screenshots

[Landing top 10](screenshots/redesign/00_landing_top10.png) · [Landing map](screenshots/redesign/00a_landing_map.png) · [Quick checks](screenshots/redesign/00b_quick_checks.png) · [After a decision](screenshots/redesign/00c_after_decision.png) · [Advanced](screenshots/redesign/00d_advanced.png) · [Built-in summary](screenshots/redesign/04_builtin_summary.png) · [Built-in chat](screenshots/redesign/05_builtin_chat.png) · [Load](screenshots/redesign/01_load.png) · [Review a flag](screenshots/redesign/02_review.png) · [Disagreement](screenshots/redesign/02b_disagreement.png) · [Priority list](screenshots/redesign/03_use_list.png) · [Map](screenshots/redesign/03b_use_map.png) · [Explained tract](screenshots/redesign/03c_explained_tract.png). Screenshots use real public data and a separately labeled **simulated-reviewer demo workspace**, not practitioner validation.

## Branding and preserved versions

Beacon design tokens follow the supplied April 2026 guidelines: navy headings, blue controls, orange calls to action, semantic alert colors with labels/icons. Avenir is **not bundled**; CSS declares an Arial/sans-serif fallback and Menlo/monospace for IDs. No official logo artwork is reproduced or recolored. Sources: [brief](https://docs.google.com/document/d/1UFeoveMyn0UYYCc3oj4fVDRtXSA5nHvSzRTJfswc_Do/edit), [Appendix B](https://docs.google.com/document/d/1L25DTxI31BlrH3QvB7k8H0rt6eowMiYA3YqHEwfJer0/edit), [brand guidelines](https://drive.google.com/file/d/1KZY4wAevNOpc0kg6owQqYE42hqKYrB2J/view).

`app_v0_dashboard.py` remains the original seven-tab backup. `archive/` preserves the first cleaner, its tests and its historical evals; `build_data.py`, `routing.py`, `logic.py`, example inventory and older processed assets are **legacy reference only**, not used by the redesigned app or current evals. Their old assumptions are not the current analytical contract. No deployment is performed by this build.

### Plain-language display

Tables use friendly indicator names, readable review statuses, and one-decimal percentages. Internal IDs and hashes are hidden from normal tables; originals and full-precision values remain unchanged in evidence details and exports. Review opens with one short explanation, while counts and technical reasoning are expandable.

## Start with an answer, not a cleaning queue

Each community opens on ten automatically cleaned priority neighborhoods, a one-line reason and evidence-confidence label for each, and the map. The banner explicitly says the list is **automatically cleaned, not yet checked by your team**. This is a starting answer—not confirmed need or an approved service plan. Local source preparation is automatic; there is no manual cleaning step or model dependency.

**Quick checks** surface at most eight current top-ten neighborhoods whose membership actually changes when poverty alone is varied within its published 90% margin of error and the regional score is recomputed. Pristine counts: **Central Florida 8**. These are a small starting set, not all possible uncertainties; other contenders, joint changes and access uncertainty remain advanced. Checks are not continually replenished after a decision.

Accept keeps a candidate **with its uncertainty**, without imputing an endpoint or claiming a correction. Challenge sets it aside from the team's working top ten, brings in the next source-ranked candidate, and shows who left/entered. Both are audited team choices; original observations and analytical ranks stay unchanged. Team disagreements remain visible and lower confidence rather than silently removing records. A quick answer does not complete the full evidence review.

Open **Advanced / full review** for the original Load → Review → Use workspace: all 18 rules, source coverage, notes, disagreements, audit log, reviewed-only dashboard and replayable export. No functionality was removed. The landing preview and reviewed-only dashboard are deliberately different views.

## Approximate place names (Central Florida only)

Every retained tract has a committed offline label in [`data/clean/tract_place_names.csv`](data/clean/tract_place_names.csv): **490 total; 307 inside a Census incorporated place or CDP, 183 labeled “Unincorporated <County> County.”** The supplied map point is used for 489 tracts; the one missing point uses the matching TIGER tract internal point for naming only, without altering the supplied map coordinates.

Source: [Census TIGER/Line 2024 Florida places](https://www2.census.gov/geo/tiger/TIGER2024/PLACE/tl_2024_12_place.zip) and [2024 Florida tracts](https://www2.census.gov/geo/tiger/TIGER2024/TRACT/tl_2024_12_tract.zip), January 1, 2024 boundary vintage. The reproducible builder uses point containment, never nearest-city guessing or a majority-area claim. The two raw archives are gitignored; the small CSV and [source hashes](data/clean/tract_place_names.sources.json) are committed. [Five independent official Census query checks](data/clean/place_name_checks.json) verify Orlando, Alafaya, Poinciana, Pine Hills and an unincorporated point.

```bash
.venv/bin/pip install -r requirements-geography.txt  # builder only, not needed by the app
.venv/bin/python scripts/build_place_names.py
.venv/bin/python scripts/build_place_names.py --verify
```

**Place names are approximate labels from Census boundaries; a tract can span more than one area.** A city/CDP label means the selected point is inside that polygon—not that the whole tract, all residents or a service area belongs to it. Tract GEOIDs remain alongside names throughout the UI and exports. Names do not affect ranking, confidence or review decisions.
