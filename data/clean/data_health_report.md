# Data Health Report: Central Florida food access

We combined **8 public files** into **one clean table of 968 neighborhoods** (census tracts) in Orange, Seminole, Osceola, Lake, Volusia, Brevard, Polk and Sumter counties.
We found **3,124 problems**. 488 were fixed or filled automatically; **426 neighborhoods** are flagged for a person to check, and 32 are left out of rankings.

## The biggest problems
- **Missing at the source:** CDC food-insecurity and transportation numbers are blank for all 968 tracts. CDC's 2025 release has no Florida values for them.
- **Mixed years:** 472 tracts (Volusia, Brevard, Polk, Sumter) have no current Census numbers in the Beacon sample, so we filled them from older USDA figures and labeled them.
- **Shaky estimates:** 659 Census numbers have a margin of error too large to trust alone.
- **Dorms, prisons, care homes:** 25 tracts where 25%+ of people live in group quarters, which can make poverty look higher than it is for families.
- **Tiny populations:** 8 tracts with under 500 residents.

## What the clean data shows
- 1,481,494 of 4,688,329 residents live more than 1 mile (city) or 10 miles (rural) by car from a SNAP-accepting store; 1,158,183 of them are low income.
- 20,245 homes with no car are that far from a store.
- USDA low-income & low-access neighborhoods with the most low-income people far from a store (reliable data only): Polk tract 145.01 (5,877); Osceola tract 411.01 (4,927); Polk tract 144.01 (4,553).

_Public data only (USDA, Census, CDC). Distances use 2020 population. Shows where to look, not why; no pantry coverage data._