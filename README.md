# 🧹 BEACON FAAB v1: Beacon Data Pre-Cleaner for food banks
DevFest Florida Hackathon 2026 · Data for Good track · DataKind **Beacon** challenge (Food Access & Nutrition Gaps)

## Problem
Across 8 Central Florida counties (Orange, Seminole, Osceola, Lake, Volusia, Brevard, Polk, Sumter), **about 1.48 million of 4.69 million residents** live more than 1 mile (city) or 10 miles (rural) by car from a SNAP-accepting store, and **1.16 million of them are low income**. **20,245 homes with no car** are that far from a store (USDA Food Access Research Atlas, 2025 release, 2020 population).
The data that shows this is split across USDA, Census, CDC and SNAP-retailer files, and food banks have to piece those scattered datasets together by hand (as DataKind's Beacon brief notes). The files also contain blanks, shaky estimates, dorm-heavy tracts and mixed years that are easy to miss.

## What it does (one page, three steps)
1. **Load:** Beacon's example public files (or add your own CSV with a tract ID column).
2. **Clean:** joins everything on the 11-digit tract ID (fixes `1400000US…` prefixes, lost leading zeros, float IDs), renames columns in plain English, converts Census text values (`250,000+`, `-`, `(X)`), and flags per tract:
   blank source fields · shaky estimates (CV > 30% from the margin of error) · mostly group quarters (≥25%: dorms, prisons, care homes) · tiny populations (<500) · impossible shares (>100%, capped) · mixed years (USDA used where the Beacon Census sample has no data).
3. **Results:** a plain-English Data Health Report (written by Gemini when `GEMINI_API_KEY` is set, otherwise a template), downloads (clean CSV, problem list CSV, report), and one map/list of the top 10 reliable USDA low-income & low-access tracts with the **nearest SNAP grocery stores** (straight-line miles).
   **Optional routing:** upload your food bank inventory / pantry locations (`name, lat, lon, pounds_available`) to get a greedy need-to-supply plan (pounds shared in proportion to need, taken from the nearest site with food left). `examples/EXAMPLE_food_bank_inventory.csv` is **made-up example data** for testing only.

Current numbers: 8 files → 1 table of 968 tracts · 3,124 problems found · 488 fixed or filled · 426 tracts flagged for review · 32 left out of rankings.

## Example for the pitch: high poverty but low SNAP participation
Current Census data only, reliable estimates, <10% group quarters: **Orange tract 177.03**, poverty 43.7% (±11.4) vs SNAP 21.5% of households (±7.5), 2% group quarters, 4,414 residents (ACS 2020–24 S1701 / S2201). This shows a *possible* enrollment gap, not eligibility. More examples are in `data/clean/snap_gap_examples.csv`. (Orange 165.1 was dropped because 47% of its residents live in group quarters.)

## Data sources (public, from the Beacon example data folder, downloaded 2026-11-07)
USDA ERS Food Access Research Atlas (2025 release) · Census ACS 5-year 2020–24 S2201, S1701, S1901, S0101 (Orange, Seminole, Osceola, Lake only) · CDC PLACES 2025 · USDA SNAP Retailer Locations · Census 2023 cartographic tract boundaries.

## Limitations
- CDC food-insecurity and transportation numbers are blank for all Florida tracts.
- The Beacon Census sample covers 4 of the 8 counties. The other 4 use older USDA figures; a Census API key would fill them (that's our limitation, not a public data gap).
- **No surplus or inventory data is included.** Routing only appears when a user uploads their own inventory. Distances are straight-line from tract centers, not driving routes.
- There's no pantry coverage data, and the tool shows correlation, not cause.

## Next steps
- **Plug in food bank inventory** for true shortage-to-surplus routing, using road distances.
- Pull the missing counties from the Census API.
- Add team notes and approvals.

## Run
```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/streamlit run app.py        # uses data/clean/* if raw Beacon files aren't in data/beacon/
.venv/bin/python -m pytest -q tests   # cleaning + routing tests
```
Files: `clean.py` (reusable cleaner), `routing.py` (nearest store and inventory matching), `app.py` (UI), `app_v0_dashboard.py` + `logic.py` (old dashboard, kept for reference).

## DataKind: What we made / learned / next
- **Made:** a pre-cleaner that turns 8 Beacon files into one trustworthy table, with a plain-English health report.
- **Learned:** _TODO_
- **Next:** _TODO_
