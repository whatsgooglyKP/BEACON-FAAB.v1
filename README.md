# 🥫 Food Access Action Board — Central Florida
DevFest Florida Hackathon 2026 · Data for Good track · DataKind **Beacon** challenge (Food Access & Nutrition Gaps)

## Problem
Central Florida food banks know their communities, but the public data on poverty, SNAP use and grocery access is scattered, partly stale, and sometimes contradictory. Coordinators need to know **where need may be going unmet and what to do next**, with the evidence and caveats visible.

## Persona
A food bank / pantry **outreach coordinator** (e.g., at a regional food bank like Second Harvest Food Bank of Central Florida — user type only, no partnership implied) planning this month's mobile pantry stops and SNAP outreach.

## What it does
- **What to do next** home view: top 3 mobile-pantry candidates, SNAP-enrollment outreach list, and "verify data before acting" list, each with the why and the numbers.
- **Map** of 968 census tracts in Orange, Seminole, Osceola, Lake, Volusia, Brevard, Polk, Sumter, colored by a transparent Need Score (red = highest).
- **Adjustable weights** (sliders) — what-if analysis.
- **Ranked list** with county filter and a plain-English "why flagged".
- **Neighborhood detail**: each measure vs county and region average, data-quality cautions, action brief (Gemini or grounded template), approve / reject / needs-discussion with notes, multi-reviewer **disagreement** surfacing.
- **Data gaps** tab: hidden need, coverage holes by county, small-sample estimates, indicators that disagree.
- **County comparison** and **Export Action List (CSV)**. Decisions persist to `data/decisions.csv`.

## Data sources (all public; downloaded 2026-11-07)
| Source | Vintage | Via |
|---|---|---|
| USDA ERS Food Access Research Atlas — SNAP-authorized Retailer Access Map, driving distance | Initial release July 2026; 2020 tracts & population | Beacon example data folder |
| ACS 5-year S2201 (SNAP), S1701 (poverty), S1901 (income), S0101 (population) | 2020–2024 | Beacon folder — **Orange, Seminole, Osceola, Lake only** |
| CDC PLACES tract data (food insecurity, SNAP, lack of transport, diabetes) | 2025 release | Beacon folder — food/transport fields **blank for all FL tracts** |
| USDA SNAP Retailer Locations | as provided | Beacon folder |
| Census cartographic boundaries cb_2023_12_tract_500k | 2023 (2020 tracts) | census.gov |

For Volusia, Brevard, Polk and Sumter, poverty and SNAP fall back to the USDA Atlas tract values (older ACS / 2020 households) and are labeled as such.

## Need Score
Each measure → percentile rank (0–100) across all 968 tracts → weighted average (default weights: poverty 25, low-income & far from grocery 25, no-car & far 20, SNAP 15, diabetes 10, few grocery stores 5). Missing measures are dropped and weights re-balanced. "Far" = >1 mile driving (urban) / >10 miles (rural) from a SNAP-authorized store.

## Gap rules
- **Hidden need**: not USDA low-income/low-access, but poverty or SNAP in top quartile and low-income-far share ≥ median.
- **SNAP gap**: poverty in top quartile and SNAP% < 0.8 × poverty%.
- **Car gap** (mobile pantry candidates): car-free homes far from a store in top 10%; population ≥ 1,000.
- **Verify first**: score in top 20% with a small-sample, blank or out-of-range value.

## GenAI use
`logic.gemini_brief` sends only the tract's numbers + warnings as JSON to Gemini (`gemini-2.5-flash`) with instructions not to invent numbers, pantries or causation. Enabled when `GEMINI_API_KEY` or `GOOGLE_API_KEY` is set (disable with `USE_GEMINI=0`); otherwise a deterministic template brief is used.

## Limitations
No pantry/coverage data (private data out of scope) → the tool cannot say an area is unserved. No Central Florida transportation data. Correlation, not causation. ACS small-sample margins; USDA distances use 2020 population; stores counted only inside tract boundaries.

## Run
```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
# put Beacon files in data/beacon/ and the tract shapefile zip at data/tr.zip, then:
.venv/bin/python build_data.py
.venv/bin/streamlit run app.py
```
(`data/tracts.csv`, `data/tracts.geojson`, `data/grocery_stores.csv` are committed, so `streamlit run app.py` works without rebuilding.)

## DataKind: What we made / learned / next
- **What we made:** _TODO_
- **What we learned:** _TODO (e.g., CDC PLACES food insecurity is blank for all of Florida; Beacon ACS sample covers 4 counties)_
- **What's next:** _TODO (add pantry locations from partners, transit data, shared team notes)_
