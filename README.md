# Beacon · Evidence Review

**Load → Review → Use:** a public-data prototype built for Beacon, DevFest Florida 2026, DataKind Challenge 2. This is **not an official DataKind product**.

Food-access teams need more than a map: they need to know which evidence is usable, why a signal was flagged, and how teammates reached a decision. This application safely standardizes public files, exposes uncertainty, and keeps a simple explained dashboard after human review. It does **not** predict shortages or route food.

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

## The workflow

1. **Load:** choose Central Florida (Lake, Orange, Osceola, Seminole), NYC (five boroughs), or Salt Lake + Tooele. See units, periods, coverage, raw hashes and the exact definition before proceeding.
2. **Review:** safe formatting and documented missing-code handling are automatic and logged. Everything uncertain stays visible with a reason, action confidence, original cell/year/universe, and Accept/Reject. Source-backed numeric Edit is available on actual value/exclusion proposals; interpretation edits belong in tract notes, not fabricated statistics. Every human decision needs a display name and reason.
3. **Use:** the dashboard remains: explained rank, evidence-quality label, simple point map, and resource-finder links. **Only fully reviewed tracts appear in the default shortlist.** A separate, explicitly unreviewed preview keeps uncertain neighborhoods visible. The score never claims an operational action is approved.

### Collaboration and recommendation controls

Reviewer names are **self-entered and unauthenticated**. This demonstrates sequential collaboration on one local database, not production multi-user access. Conflicting named votes create a dispute, contested patches are withheld, and an explicit named resolution is required; new conflicting votes reopen it. Undo and revisions append history rather than deleting it. A stale form cannot overwrite newer decisions.

Add tract notes; confirm/challenge an inferred need; approve/reject/replace a proposed action; or set a human operational position. Human priority is shown **beside** the model rank and never rewrites its inputs. Conflicting operational choices are surfaced too. Exports include the baseline, observations, raw values, source coordinates/hashes, null reasons, all decisions, unresolved issues, notes, field dictionary, coverage, shortlist and offline health report; `exports.replay_export` reconstructs the reviewed view.

## Evidence, not overclaiming

- **Appendix B LILA:** low-income **AND** low-access, **½ mile urban / 10 miles rural, driving**. Straight-line and 1-mile alternatives are separate sensitivity measures.
- Source flags: **157/490 FL**, **37/2,324 USDA NYC** (2,327 IDs retained in the union), **48/268 Salt Lake + Tooele**. These are not confirmed high-need totals.
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
.venv/bin/python -m evals.run                 # seven mandatory suites; live Gemini separately
.venv/bin/python -m evals.run --skip-gemini   # explicitly offline
.venv/bin/python -m evals.run --only 5        # report/fallback and optional model
```

[Latest scorecard](evals/results/latest.md) · [How the evaluations work](EVALS.md) · [Architecture and file tour](docs/ARCHITECTURE.md) · [Approved redesign](REDESIGN_PLAN.md) · [Requirements completion notes](docs/IMPLEMENTATION_STATUS.md).

Optional `GEMINI_API_KEY` is read only from the environment. The opt-in chat prototype uses `gemini-3.8-flash`, a 150-second timeout, and exact paragraph semantic validation. It can explain a fixed public evidence packet and resource finders, **not** freely generate facts, clean values, compute ranks or resolve votes. Every failure has an immediately usable deterministic fallback. Do not commit a key or `.env` file.

## Screenshots

[Load](screenshots/redesign/01_load.png) · [Review a flag](screenshots/redesign/02_review.png) · [Disagreement](screenshots/redesign/02b_disagreement.png) · [Priority list](screenshots/redesign/03_use_list.png) · [Map](screenshots/redesign/03b_use_map.png) · [Explained tract](screenshots/redesign/03c_explained_tract.png). Screenshots use real public data and a separately labeled **simulated-reviewer demo workspace**, not practitioner validation.

## Branding and preserved versions

Beacon design tokens follow the supplied April 2026 guidelines: navy headings, blue controls, orange calls to action, semantic alert colors with labels/icons. Avenir is **not bundled**; CSS declares an Arial/sans-serif fallback and Menlo/monospace for IDs. No official logo artwork is reproduced or recolored. Sources: [brief](https://docs.google.com/document/d/1UFeoveMyn0UYYCc3oj4fVDRtXSA5nHvSzRTJfswc_Do/edit), [Appendix B](https://docs.google.com/document/d/1L25DTxI31BlrH3QvB7k8H0rt6eowMiYA3YqHEwfJer0/edit), [brand guidelines](https://drive.google.com/file/d/1KZY4wAevNOpc0kg6owQqYE42hqKYrB2J/view).

`app_v0_dashboard.py` remains the original seven-tab backup. `archive/` preserves the first cleaner, its tests and its historical evals; `build_data.py`, `routing.py`, `logic.py`, example inventory and older processed assets are **legacy reference only**, not used by the redesigned app or current evals. Their old assumptions are not the current analytical contract. No deployment is performed by this build.
