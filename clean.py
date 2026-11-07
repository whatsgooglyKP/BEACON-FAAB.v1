"""Beacon Data Pre-Cleaner: joins Beacon's public food-access files on an 11-digit tract ID,
renames columns to plain English, converts types, and flags problems per tract.
Usage: from clean import run; table, issues, summary = run()"""
import re, numpy as np, pandas as pd

B = "data/beacon"
COUNTIES = {"095": "Orange", "117": "Seminole", "097": "Osceola", "069": "Lake",
            "127": "Volusia", "009": "Brevard", "105": "Polk", "119": "Sumter"}
SUPPRESSED = {"-", "N", "(X)", "**", "***", "*****", "null", ""}
GQ_LIMIT, TINY_POP, CV_LIMIT = 25.0, 500, 0.30

def fix_geoid(x):
    """11-digit tract GEOID from '1400000US12095016510', 12095016510.0, '1209501651' (lost leading zero), '12-095-016510'."""
    if x is None or (isinstance(x, float) and np.isnan(x)): return None
    s = str(x).strip()
    if "US" in s: s = s.split("US")[-1]
    s = re.sub(r"\.0$", "", s); s = re.sub(r"\D", "", s)
    if not s or len(s) > 11 or len(s) < 10: return None
    return s.zfill(11)

def to_number(v):
    """Census-style text -> (number or NaN, note). Handles commas, '250,000+', '2,500-', suppression codes."""
    if v is None or (isinstance(v, float) and np.isnan(v)): return np.nan, None
    s = str(v).strip()
    if s in SUPPRESSED: return np.nan, "suppressed"
    capped = s.endswith("+") or (s.endswith("-") and len(s) > 1)
    try: return float(s.rstrip("+-").replace(",", "")), ("top/bottom-coded" if capped else None)
    except ValueError: return np.nan, "not a number"

def tract_name(g):
    return f"{int(g[5:9])}.{g[9:]}" if g[9:] != "00" else str(int(g[5:9]))

class Log:
    def __init__(s): s.rows = []; s.fixes = {}
    def issue(s, geoid, field, problem, action, kind, before="", after=""):
        s.rows.append(dict(GEOID=geoid, field=field, problem=problem, what_we_did=action, type=kind, value_before=before, value_after=after))
    def fix(s, kind, n=1): s.fixes[kind] = s.fixes.get(kind, 0) + n

def _in_region(g): return bool(g) and g[:2] == "12" and g[2:5] in COUNTIES

def _acs(path, cols, log, name):
    raw = pd.read_csv(path, dtype=str, skiprows=[1])
    out = pd.DataFrame({"GEOID": raw.GEO_ID.map(fix_geoid)})
    log.fix("tract IDs reformatted to 11 digits", int(out.GEOID.map(_in_region).sum()))
    for c, label in cols.items():
        vals = raw[c].map(to_number); out[label] = [v for v, _ in vals]
        for gid, rawv, (v, note) in zip(out.GEOID, raw[c], vals):
            if note and _in_region(gid):
                log.issue(gid, label, f"value was {note} in the Census file", "set blank" if note != "top/bottom-coded" else "kept the cap value", "fixed",
                          before=rawv, after="(blank)" if pd.isna(v) else f"{v:g}")
    return out

def load_sources(base=B):
    log = Log(); files = []; acs = None
    for folder, table, cols in [
        ("snap", "S2201", {"S2201_C01_001E": "households", "S2201_C04_001E": "snap_households_pct", "S2201_C04_001M": "snap_households_pct_moe"}),
        ("poverty", "S1701", {"S1701_C03_001E": "poverty_pct", "S1701_C03_001M": "poverty_pct_moe"}),
        ("income", "S1901", {"S1901_C01_012E": "median_household_income"}),
        ("pop", "S0101", {"S0101_C01_001E": "population_2024"})]:
        d = _acs(f"{base}/{folder}/ACSST5Y2024.{table}-Data.csv", cols, log, table); files.append(f"Census ACS {table} (2020–24)")
        acs = d if acs is None else acs.merge(d, on="GEOID", how="outer")
    g = pd.read_csv(f"{base}/fara2025/SRAM General Tract Characteristics Data.csv", dtype=str, encoding="latin-1")
    dd = pd.read_csv(f"{base}/fara2025/SRAM Driving Distance Data.csv", dtype=str, encoding="latin-1")
    files += ["USDA Food Access Atlas: tract facts", "USDA Food Access Atlas: driving distance"]
    usda = g.merge(dd.drop(columns=["State", "County20", "County24"]), on="CensusTract20")
    usda["GEOID"] = usda.CensusTract20.map(fix_geoid)
    num = lambda c: pd.to_numeric(usda[c], errors="coerce")
    urban = num("Urban").eq(1)
    U = pd.DataFrame({"GEOID": usda.GEOID, "urban": urban,
        "population_2020": num("POP2020"), "homes_2020": num("OHU2020"), "group_quarters_pct": num("PCTGQTRS"),
        "usda_poverty_pct": num("PovertyRate"), "usda_snap_homes": num("TractSNAP"), "homes_without_car": num("TractHUNV"),
        "usda_low_income_low_access": num("DD_SRAM_LILATracts_1And10"),
        "people_far_from_store": np.where(urban, num("DD_SRAM_lapop1"), num("DD_SRAM_lapop10")),
        "low_income_people_far_from_store": np.where(urban, num("DD_SRAM_lalowi1"), num("DD_SRAM_lalowi10")),
        "low_income_far_from_store_pct": np.where(urban, num("DD_SRAM_lalowi1share"), num("DD_SRAM_lalowi10share")),
        "car_free_homes_far_from_store": np.where(urban, num("DD_SRAM_lahunv1"), num("DD_SRAM_lahunv10"))})
    pl = pd.read_csv(f"{base}/places.csv", dtype=str, usecols=["TractFIPS", "FOODINSECU_CrudePrev", "LACKTRPT_CrudePrev", "DIABETES_CrudePrev"])
    files.append("CDC PLACES health estimates (2025)")
    P = pd.DataFrame({"GEOID": pl.TractFIPS.map(fix_geoid), "food_insecurity_pct": pd.to_numeric(pl.FOODINSECU_CrudePrev, errors="coerce"),
        "lack_transportation_pct": pd.to_numeric(pl.LACKTRPT_CrudePrev, errors="coerce"), "diabetes_pct": pd.to_numeric(pl.DIABETES_CrudePrev, errors="coerce")})
    s = pd.read_csv(f"{base}/snap_retailers.csv", usecols=["State", "County"], dtype=str)
    files.append("USDA SNAP retailer list")
    sc = s[s.State.eq("FL")].assign(county=lambda x: x.County.str.title()).groupby("county").size().rename("snap_stores_in_county").reset_index()
    return dict(acs=acs, usda=U, places=P, stores=sc, files=files, log=log)

def clean(src, user_df=None, user_id_col=None):
    log = src["log"]
    t = src["usda"][src["usda"].GEOID.map(_in_region)].copy()
    t.insert(1, "county", t.GEOID.str[2:5].map(COUNTIES)); t.insert(2, "tract", t.GEOID.map(tract_name))
    t = t.merge(src["acs"], on="GEOID", how="left").merge(src["places"], on="GEOID", how="left").merge(src["stores"], on="county", how="left")
    t["poverty_pct_best"] = t.poverty_pct; t["snap_pct_best"] = t.snap_households_pct; t["poverty_snap_source"] = "Census 2020–24"
    t.insert(t.columns.get_loc("low_income_far_from_store_pct") + 1, "low_income_far_from_store_pct_raw", t.low_income_far_from_store_pct)
    t["needs_review"] = False; t["left_out_of_ranking"] = False; t["review_reasons"] = ""
    def flag(i, txt, out=False):
        t.at[i, "review_reasons"] = (t.at[i, "review_reasons"] + "; " if t.at[i, "review_reasons"] else "") + txt
        t.at[i, "needs_review"] = True
        if out: t.at[i, "left_out_of_ranking"] = True
    for i, r in t.iterrows():
        g = r.GEOID
        for f, lab in [("food_insecurity_pct", "food insecurity"), ("lack_transportation_pct", "lack of transportation")]:
            if pd.isna(r[f]): log.issue(g, lab, "blank at the source (CDC has no Florida values)", "left blank", "missing", "(blank)", "(blank)")
        if pd.isna(r.poverty_pct):
            if pd.notna(r.usda_poverty_pct):
                t.at[i, "poverty_pct_best"] = r.usda_poverty_pct
                t.at[i, "snap_pct_best"] = r.usda_snap_homes / r.homes_2020 * 100 if r.homes_2020 else np.nan
                t.at[i, "poverty_snap_source"] = "USDA Atlas (older years)"
                sn = t.at[i, "snap_pct_best"]
                log.issue(g, "poverty / SNAP", "no current Census numbers in the Beacon sample", "filled from USDA Atlas and labeled", "mixed years",
                          before="(blank)", after=f"poverty {r.usda_poverty_pct:.1f}%; SNAP {sn:.1f}% (USDA TractSNAP/OHU2020)" if pd.notna(sn) else f"poverty {r.usda_poverty_pct:.1f}%; SNAP blank")
            else:
                log.issue(g, "poverty / SNAP", "blank in every source", "left blank", "missing", "(blank)", "(blank)"); flag(i, "poverty blank everywhere")
        for est, moe, lab in [("snap_households_pct", "snap_households_pct_moe", "SNAP %"), ("poverty_pct", "poverty_pct_moe", "poverty %")]:
            if pd.notna(r[est]) and pd.notna(r[moe]) and r[est] > 0 and (r[moe] / 1.645) / r[est] > CV_LIMIT:
                log.issue(g, lab, f"shaky estimate: {r[est]:.1f}% ± {r[moe]:.1f}", "flagged for review", "unreliable", f"{r[est]:.1f}", f"{r[est]:.1f} (unchanged)"); flag(i, f"shaky {lab} ({r[est]:.1f}% ± {r[moe]:.1f})")
        if pd.notna(r.group_quarters_pct) and r.group_quarters_pct >= GQ_LIMIT:
            log.issue(g, "group quarters", f"{r.group_quarters_pct:.0f}% live in dorms, prisons or care homes", "left out of ranking", "group quarters", f"{r.group_quarters_pct:.2f}", "(unchanged)"); flag(i, f"{r.group_quarters_pct:.0f}% in dorms/prisons/care homes", True)
        pop = r.population_2024 if pd.notna(r.population_2024) else r.population_2020
        if pd.notna(pop) and pop < TINY_POP:
            log.issue(g, "population", f"only {int(pop)} residents", "left out of ranking", "tiny population", f"{int(pop)}", "(unchanged)"); flag(i, f"only {int(pop)} residents", True)
        if pd.notna(r.low_income_far_from_store_pct) and r.low_income_far_from_store_pct > 100:
            t.at[i, "low_income_far_from_store_pct"] = 100.0
            log.issue(g, "low income & far %", f"was {r.low_income_far_from_store_pct:.1f}% (impossible)", "capped at 100", "fixed", f"{r.low_income_far_from_store_pct:.2f}", "100")
        if pd.isna(r.low_income_people_far_from_store):
            log.issue(g, "low income & far", "blank in USDA file", "left blank", "missing", "(blank)", "(blank)"); flag(i, "USDA distance blank", True)
    t["poverty_minus_snap_points"] = t.poverty_pct_best - t.snap_pct_best
    user_match = None
    if user_df is not None and user_id_col:
        u = user_df.copy(); u["GEOID"] = u[user_id_col].map(fix_geoid)
        u = u.drop(columns=[user_id_col]).dropna(subset=["GEOID"]).drop_duplicates("GEOID")
        u.columns = ["GEOID" if c == "GEOID" else "your_" + re.sub(r"\W+", "_", str(c)).strip("_").lower() for c in u.columns]
        user_match = (int(u.GEOID.isin(t.GEOID).sum()), len(user_df))
        t = t.merge(u, on="GEOID", how="left")
    issues = pd.DataFrame(log.rows, columns=["GEOID", "field", "problem", "what_we_did", "type", "value_before", "value_after"])
    issues = issues[issues.GEOID.isin(t.GEOID)].merge(t[["GEOID", "county", "tract"]], on="GEOID", how="left")
    summary = dict(files_in=len(src["files"]) + (user_df is not None), file_names=src["files"], tracts=len(t), problems=len(issues),
        fixed=int(issues.type.isin(["fixed", "mixed years"]).sum()), id_fixes=src["log"].fixes.get("tract IDs reformatted to 11 digits", 0),
        flagged=int(t.needs_review.sum()), left_out=int(t.left_out_of_ranking.sum()),
        ranking_out=int(t.needs_review.sum()), out_size=int(t.left_out_of_ranking.sum()), out_shaky=int((t.needs_review & ~t.left_out_of_ranking).sum()),
        corrected=int(issues.type.eq("fixed").sum()), filled=int(issues.type.eq("mixed years").sum()),
        statewide_cdc=int(issues.field.isin(["food insecurity", "lack of transportation"]).sum()),
        tract_issues=int((~issues.field.isin(["food insecurity", "lack of transportation"])).sum()), user_match=user_match,
        by_type=issues.groupby("type").size().to_dict())
    return t, issues, summary

def top_need(t, n=10):
    """USDA low-income & low-access tracts only, reliable data, ranked by low-income people far from a store."""
    ok = t[~t.left_out_of_ranking & ~t.needs_review & t.usda_low_income_low_access.eq(1)]
    return ok.sort_values("low_income_people_far_from_store", ascending=False).head(n)

def snap_gap(t, n=10):
    """High poverty, lower SNAP participation; current Census data only, reliable estimates, <10% group quarters."""
    ok = t[(t.poverty_snap_source == "Census 2020–24") & ~t.needs_review & (t.group_quarters_pct < 10) & (t.poverty_pct >= 25)]
    return ok.sort_values("poverty_minus_snap_points", ascending=False).head(n)

def run(base=B, user_df=None, user_id_col=None):
    return clean(load_sources(base), user_df, user_id_col)

def health_report(t, issues, s):
    bt = s["by_type"]; top = top_need(t, 3)
    L = ["# Data Health Report: Central Florida food access", "",
      f"We combined **{s['files_in']} public files** into **one clean table of {s['tracts']} neighborhoods** (census tracts) in Orange, Seminole, Osceola, Lake, Volusia, Brevard, Polk and Sumter counties.",
      f"We found **{s['tract_issues']:,} tract-level issues plus one statewide CDC gap**. {s['corrected']} values were corrected, {s['filled']} gaps were filled from USDA (labeled), and everything else was flagged; no original value was invented.",
      f"**{s['ranking_out']} neighborhoods are left out of the ranking** ({s['out_size']} for dorms or tiny size, {s['out_shaky']} for shaky estimates).",
      "Data integrity: raw values are kept next to cleaned ones, every change is logged with before/after values, and filled values are labeled by source.", "",
      "## The biggest problems",
      f"- **Statewide CDC gap:** CDC food-insecurity and transportation numbers are blank for all {s['tracts']} Florida tracts in the 2025 release (counted once, not as {s['statewide_cdc']:,} problems).",
      f"- **Mixed years:** {int((t.poverty_snap_source != 'Census 2020–24').sum())} tracts (Volusia, Brevard, Polk, Sumter) have no current Census numbers in the Beacon sample, so we filled them from older USDA figures and labeled them.",
      f"- **Shaky estimates:** {bt.get('unreliable', 0)} Census numbers have a margin of error too large to trust alone.",
      f"- **Dorms, prisons, care homes:** {int((t.group_quarters_pct >= GQ_LIMIT).sum())} tracts where {GQ_LIMIT:.0f}%+ of people live in group quarters, which can make poverty look higher than it is for families.",
      f"- **Tiny populations:** {int((t.population_2024.fillna(t.population_2020) < TINY_POP).sum())} tracts with under {TINY_POP} residents.", "",
      "## What the clean data shows",
      f"- {t.people_far_from_store.sum():,.0f} of {t.population_2020.sum():,.0f} residents live more than 1 mile (city) or 10 miles (rural) by car from a SNAP-accepting store; {t.low_income_people_far_from_store.sum():,.0f} of them are low income.",
      f"- {t.car_free_homes_far_from_store.sum():,.0f} homes with no car are that far from a store.",
      "- USDA low-income & low-access neighborhoods with the most low-income people far from a store (reliable data only): " + "; ".join(f"{r.county} tract {r.tract} ({r.low_income_people_far_from_store:,.0f})" for r in top.itertuples()) + ".", "",
      "_Public data only (USDA, Census, CDC). Distances use 2020 population. Shows where to look, not why; no pantry coverage data._"]
    return "\n".join(L)
