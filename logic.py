"""Scoring, data-quality checks, gap detection and action briefs. All numbers come from data/tracts.csv."""
import os, json, numpy as np, pandas as pd

# plain-English indicator definitions: key -> (label, tooltip, default weight)
INDICATORS = {
 "poverty":   ("People living in poverty (%)", "Share of residents below the federal poverty line (ACS 2020-24; USDA Atlas value used where ACS is missing).", 25),
 "lowinc_far":("Low income and far from a grocery store (%)", "Share of residents who are low income AND live more than 1 mile (city) or 10 miles (rural) driving distance from a SNAP-accepting food store (USDA Food Access Research Atlas).", 25),
 "novehicle_far":("Homes with no car, far from a grocery store (%)", "Share of homes with no vehicle that are also beyond that driving distance from a SNAP-accepting store (USDA).", 20),
 "snap":      ("Households using SNAP (%)", "Share of households receiving SNAP/food stamps (ACS 2020-24; USDA Atlas value where ACS is missing).", 15),
 "diabetes":  ("Adults with diabetes (%)", "CDC PLACES model estimate. Diet-related health signal, not a direct food measure.", 10),
 "few_stores":("Few grocery stores nearby", "Fewer grocery-type SNAP stores (supermarket, grocery, farmers market) located inside the tract per 1,000 residents.", 5),
}

def load():
    df = pd.read_csv("data/tracts.csv", dtype={"GEOID": str})
    df["label"] = "Tract " + df.tract_name.astype(str) + ", " + df.county + " County"
    df["poverty_val"] = df.poverty_pct.fillna(df.fara_poverty_pct)
    df["poverty_src"] = np.where(df.poverty_pct.notna(), "ACS 2020-24", np.where(df.fara_poverty_pct.notna(), "USDA Atlas (older ACS)", "missing"))
    df["snap_val"] = df.snap_pct.fillna(df.fara_snap_pct)
    df["snap_src"] = np.where(df.snap_pct.notna(), "ACS 2020-24", np.where(df.fara_snap_pct.notna(), "USDA Atlas (2020 homes)", "missing"))
    df["pop"] = df.population.fillna(df.pop2020)
    df["lowinc_far_val"] = df.lowinc_far_pct.clip(upper=100)
    df["novehicle_far_val"] = df.novehicle_far_pct.clip(upper=100)
    df["diabetes_val"] = df.diabetes_pct
    df["stores_per_1k"] = df.grocery_type_retailers / (df["pop"].replace(0, np.nan) / 1000)
    df["few_stores_val"] = -df.stores_per_1k   # higher = fewer stores
    return df

def score(df, weights):
    d = df.copy(); tot = 0; acc = 0
    wsum = pd.Series(0.0, index=d.index)
    for k, w in weights.items():
        p = d[f"{k}_val"].rank(pct=True) * 100
        d[f"{k}_pctile"] = p
        acc = acc + p.fillna(0) * w; wsum = wsum + d[f"{k}_val"].notna() * w
    d["need_score"] = (acc / wsum.replace(0, np.nan)).round(1)
    d["rank"] = d.need_score.rank(ascending=False, method="min").astype("Int64")
    return d

def quality(r):
    w = []
    if r.poverty_src != "ACS 2020-24": w.append(f"Poverty: current Census survey data not in the Beacon sample for {r.county} County; using {r.poverty_src}.")
    if r.snap_src != "ACS 2020-24": w.append(f"SNAP: using {r.snap_src} instead of current survey data.")
    if pd.notna(r.snap_pct_moe) and pd.notna(r.snap_pct) and r.snap_pct > 0 and r.snap_pct_moe / r.snap_pct > 0.5:
        w.append(f"SNAP estimate is based on a small sample: {r.snap_pct:.1f}% ± {r.snap_pct_moe:.1f} points.")
    if pd.notna(r.poverty_pct_moe) and pd.notna(r.poverty_pct) and r.poverty_pct > 0 and r.poverty_pct_moe / r.poverty_pct > 0.5:
        w.append(f"Poverty estimate is based on a small sample: {r.poverty_pct:.1f}% ± {r.poverty_pct_moe:.1f} points.")
    if pd.notna(r.lowinc_far_pct) and r.lowinc_far_pct > 100: w.append(f"USDA access share is above 100% ({r.lowinc_far_pct:.1f}%), likely population-base mismatch; capped at 100.")
    if pd.isna(r.lowinc_far_pct) or pd.isna(r.novehicle_far_pct): w.append("USDA grocery-distance value is blank for this tract.")
    if pd.notna(r["pop"]) and r["pop"] < 1000: w.append(f"Small population ({int(r['pop'])} people): percentages swing a lot.")
    w.append("Food insecurity and lack-of-transportation (CDC PLACES) are blank for every Florida tract, so they can't be used here.")
    w.append("USDA grocery distances use 2020 population; stores may have opened or closed since.")
    return w

def flags(d):
    """Gap / disagreement detection across indicators."""
    q = lambda c, p: d[c].quantile(p)
    d = d.copy()
    d["hidden_need"] = (d.usda_lila_flag != 1) & ((d.poverty_val >= q("poverty_val", .75)) | (d.snap_val >= q("snap_val", .75))) & (d.lowinc_far_val >= q("lowinc_far_val", .5))
    d["snap_gap"] = (d.poverty_val >= q("poverty_val", .75)) & (d.snap_val < d.poverty_val * 0.8)
    d["car_gap"] = (d.novehicle_far_units >= q("novehicle_far_units", .9))
    d["verify_first"] = d.apply(lambda r: len([x for x in quality(r) if "small sample" in x or "above 100" in x or "blank for this" in x or "Small population" in x]) > 0, axis=1) & (d.need_score >= q("need_score", .8))
    return d

def why(r):
    parts = []
    for k, (lab, _, _) in INDICATORS.items():
        p = r.get(f"{k}_pctile")
        if pd.notna(p) and p >= 80 and k != "few_stores":
            parts.append(f"{lab.split(' (')[0].lower()} is {r[f'{k}_val']:.1f}% (higher than {p:.0f}% of tracts)")
    return "; ".join(parts[:3]) or "moderately high on several measures"

def template_brief(r, cavg, ravg):
    L = [f"**{r.label}** — Need score {r.need_score:.0f}/100 (rank #{r['rank']} of region).", "",
         "**What the public data shows**"]
    for k in ["poverty", "snap", "lowinc_far", "novehicle_far", "diabetes"]:
        v = r[f"{k}_val"]
        if pd.notna(v): L.append(f"- {INDICATORS[k][0]}: {v:.1f} (county avg {cavg[k]:.1f}, region avg {ravg[k]:.1f})")
    L.append(f"- Homes with no car beyond a grocery store: {int(r.novehicle_far_units) if pd.notna(r.novehicle_far_units) else 'n/a'}")
    L.append(f"- Grocery-type SNAP stores located inside the tract: {int(r.grocery_type_retailers)}")
    L += ["", "**Suggested next steps (for a coordinator to approve or reject)**"]
    if r.get("car_gap"): L.append(f"- Consider a mobile pantry stop or delivery pilot: {int(r.novehicle_far_units)} homes have no car and are far from a store.")
    if r.get("snap_gap"): L.append(f"- SNAP enrollment outreach: poverty is {r.poverty_val:.1f}% but only {r.snap_val:.1f}% of households use SNAP.")
    if r.get("hidden_need"): L.append("- Not flagged by USDA as a low-income/low-access tract, yet poverty or SNAP use is in the top quarter — check with local partners.")
    L.append("- Confirm with local partners which pantries already serve this area before adding a new site (this tool has no pantry coverage data).")
    L += ["", "_These are correlations in public data, not proof of cause. No pantry coverage data is included._"]
    return "\n".join(L)

def gemini_brief(r, cavg, ravg):
    """Gemini path (USE_GEMINI=1 and GEMINI_API_KEY/GOOGLE_API_KEY set). Falls back to template on any error."""
    key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if os.getenv("USE_GEMINI", "1") != "1" or not key: return template_brief(r, cavg, ravg), "template"
    try:
        from google import genai
        facts = {k: (round(float(r[f'{k}_val']), 1) if pd.notna(r[f'{k}_val']) else None) for k in INDICATORS if k != "few_stores"}
        facts.update(label=r.label, need_score=float(r.need_score), no_car_far_homes=None if pd.isna(r.novehicle_far_units) else int(r.novehicle_far_units),
                     grocery_stores_in_tract=int(r.grocery_type_retailers), county_avg=cavg, region_avg=ravg, data_warnings=quality(r),
                     flags={x: bool(r.get(x)) for x in ["hidden_need", "snap_gap", "car_gap"]})
        prompt = ("You write short action briefs for a food bank outreach coordinator. Use ONLY the numbers in this JSON; do not invent any number, "
                  "pantry, partner or program. Do not claim causation or that an area lacks pantry coverage. Plain English, under 180 words, "
                  "sections: What the data shows, Suggested next steps (2-3 bullets), Data cautions.\n" + json.dumps(facts, default=str))
        c = genai.Client(api_key=key)
        out = c.models.generate_content(model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"), contents=prompt)
        return out.text, "gemini"
    except Exception as e:
        return template_brief(r, cavg, ravg) + f"\n\n_(Gemini unavailable: {type(e).__name__}; showing template.)_", "template"
