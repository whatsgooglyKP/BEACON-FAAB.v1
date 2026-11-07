"""Eval suite. Run all:  python -m evals.run
Options: --only 1,3   --skip-gemini   --gemini-n 3   --random (adds 10 unseeded tracts to the spot check)"""
import argparse, datetime, json, os, re, subprocess, sys, time, traceback, concurrent.futures as cf
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import clean as C, routing as R, report as RP

RES = []
def record(n, name, status, detail):
    RES.append(dict(id=n, name=name, status=status, detail=detail)); print(f"[{status:4}] {n}. {name}: {detail}", flush=True)

_cache = {}
def data():
    if "d" not in _cache: _cache["d"] = C.run()
    return _cache["d"]

def usda_raw():
    g = pd.read_csv(f"{C.B}/fara2025/SRAM General Tract Characteristics Data.csv", dtype=str, encoding="latin-1")
    d = pd.read_csv(f"{C.B}/fara2025/SRAM Driving Distance Data.csv", dtype=str, encoding="latin-1")
    u = g.merge(d.drop(columns=["State", "County20", "County24"]), on="CensusTract20"); u["GEOID"] = u.CensusTract20.map(C.fix_geoid)
    return u.set_index("GEOID")

def acs_raw(folder, table):
    a = pd.read_csv(f"{C.B}/{folder}/ACSST5Y2024.{table}-Data.csv", dtype=str, skiprows=[1]); a["GEOID"] = a.GEO_ID.map(C.fix_geoid)
    return a.set_index("GEOID")

def e1():
    r = subprocess.run([sys.executable, "-m", "pytest", "-q", "tests"], capture_output=True, text=True)
    last = (r.stdout.strip().splitlines() or ["no output"])[-1]
    return ("PASS" if r.returncode == 0 else "FAIL"), last

def e2():
    t, i, s = data(); probs = []
    u = usda_raw(); n_src = int(pd.Series(u.index).map(C._in_region).sum())
    if not (n_src == len(t) == 968): probs.append(f"rows src={n_src} out={len(t)}")
    if t.GEOID.duplicated().any(): probs.append("duplicate GEOIDs")
    pop = int(t.population_2020.sum())
    if pop != 4688329: probs.append(f"population {pop}")
    # raw columns identical to source
    ur = u.loc[t.GEOID]; urban = pd.to_numeric(ur.Urban).eq(1).values
    src_share = np.where(urban, pd.to_numeric(ur.DD_SRAM_lalowi1share), pd.to_numeric(ur.DD_SRAM_lalowi10share))
    if not np.allclose(t.low_income_far_from_store_pct_raw.values, src_share, equal_nan=True): probs.append("raw share column differs from USDA")
    if not np.allclose(t.usda_poverty_pct.values, pd.to_numeric(ur.PovertyRate).values, equal_nan=True): probs.append("usda_poverty_pct differs")
    # every changed value logged
    capped = t[t.low_income_far_from_store_pct != t.low_income_far_from_store_pct_raw].dropna(subset=["low_income_far_from_store_pct_raw"])
    capl = i[i.what_we_did == "capped at 100"]
    if set(capped.GEOID) != set(capl.GEOID) or (capl.value_before.isna() | capl.value_after.isna()).any(): probs.append("cap changes not all logged")
    filled = t[t.poverty_pct.isna() & t.poverty_pct_best.notna()]
    fl = i[i.type == "mixed years"].set_index("GEOID")
    if set(filled.GEOID) != set(fl.index): probs.append("fills not all logged")
    if (filled.poverty_snap_source != "USDA Atlas (older years)").any(): probs.append("fill without source label")
    bad = [g for g, v in zip(filled.GEOID, filled.poverty_pct_best) if f"poverty {v:.1f}%" not in str(fl.value_after.get(g, ""))]
    if bad: probs.append(f"{len(bad)} fills missing value_after")
    same = t[t.poverty_pct.notna() & (t.poverty_pct != t.poverty_pct_best)]
    if len(same): probs.append(f"{len(same)} Census values silently changed")
    if i[["value_before", "value_after"]].isna().any().any() or (i.value_before.astype(str) == "").any(): probs.append("empty before/after cells")
    return ("FAIL" if probs else "PASS"), "; ".join(probs) or f"968 in/968 out, 0 dupes, pop 4,688,329, {len(capl)} caps + {len(fl)} fills + {int(i.type.eq('fixed').sum())} recodes all logged with before/after"

def e3(random_extra=False):
    t, _, _ = data(); u = usda_raw(); acs = {"S1701": acs_raw("poverty", "S1701"), "S2201": acs_raw("snap", "S2201")}
    picks = list(t.sample(10, random_state=42).GEOID)
    if random_extra: picks += list(t.sample(10).GEOID)
    mism = []
    for g in picks:
        r = t.set_index("GEOID").loc[g]; src = u.loc[g]; urb = src.Urban == "1"
        checks = [("population_2020", float(src.POP2020)), ("group_quarters_pct", float(src.PCTGQTRS)),
                  ("low_income_people_far_from_store", float(src.DD_SRAM_lalowi1 if urb else src.DD_SRAM_lalowi10)),
                  ("car_free_homes_far_from_store", float(src.DD_SRAM_lahunv1 if urb else src.DD_SRAM_lahunv10))]
        if g in acs["S1701"].index:
            checks += [("poverty_pct", C.to_number(acs["S1701"].loc[g, "S1701_C03_001E"])[0]), ("snap_households_pct", C.to_number(acs["S2201"].loc[g, "S2201_C04_001E"])[0])]
        for col, want in checks:
            got = r[col]
            if not ((pd.isna(got) and pd.isna(want)) or abs(float(got) - float(want)) < 1e-9): mism.append(f"{g} {col} {got}!={want}")
    return ("FAIL" if mism else "PASS"), "; ".join(mism[:5]) or f"{len(picks)} tracts × up to 6 fields match source cells exactly"

def e4():
    t, _, _ = data(); top = C.top_need(t, 10); probs = []
    bad = top[(top.group_quarters_pct >= C.GQ_LIMIT) | (top.population_2020 < C.TINY_POP) | top.needs_review]
    if len(bad): probs.append(f"{len(bad)} flagged tracts in top 10")
    t2, _, _ = C.run()
    if list(C.top_need(t2, 10).GEOID) != list(top.GEOID): probs.append("not deterministic")
    rng = np.random.default_rng(7); overlaps = []
    for _ in range(20):
        p = t.copy(); p["low_income_people_far_from_store"] = p.low_income_people_far_from_store * (1 + rng.normal(0, 0.01, len(p)))
        overlaps.append(len(set(C.top_need(p, 10).GEOID) & set(top.GEOID)))
    if min(overlaps) < 8: probs.append(f"min overlap {min(overlaps)}/10 under 1% noise")
    return ("FAIL" if probs else "PASS"), "; ".join(probs) or f"0 flagged in top 10, deterministic, 1% noise overlap min {min(overlaps)}/10 (20 trials)"

NUM = re.compile(r"(?<![\w.])\d[\d,]*(?:\.\d+)?")
def numbers(txt): return [float(x.replace(",", "")) for x in NUM.findall(txt)]
def e5(skip, n):
    t, i, s = data(); base = C.health_report(t, i, s); allowed = set(numbers(base))
    # stats-backed check: headline numbers in the template equal the summary
    head = [s["files_in"], s["tracts"], s["tract_issues"], s["corrected"], s["filled"], s["ranking_out"], s["out_size"], s["out_shaky"]]
    miss = [h for h in head if float(h) not in allowed]
    class Boom:
        class models:
            @staticmethod
            def generate_content(**k): raise RuntimeError("simulated outage")
    txt, mode = RP.make_report(t, i, s, client_factory=Boom)
    fb_ok = mode.startswith("template") and txt == base
    key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if miss or not fb_ok: return "FAIL", f"template missing {miss}; fallback ok={fb_ok}"
    if skip or not key: return "SKIP", "Gemini runs skipped (no key or --skip-gemini); template numbers match stats and fallback triggers on failure"
    def one(_):
        txt, mode = RP.make_report(t, i, s)
        if mode != "gemini": return mode, []
        bad = [x for x in numbers(txt) if not any(abs(x - a) <= max(0.051, a * 0.005) for a in allowed) and x not in (1, 2, 3, 10, 2020, 2024, 2025)]
        return mode, bad
    with cf.ThreadPoolExecutor(n) as ex: outs = list(ex.map(one, range(n)))
    ok = [o for o in outs if o[0] == "gemini"]; unfaithful = [o for o in ok if o[1]]
    detail = f"{len(ok)}/{n} Gemini runs returned; {len(ok) - len(unfaithful)} fully faithful; fallback ok"
    if unfaithful: detail += f"; unsupported numbers: {unfaithful[0][1][:5]}"
    if not ok: return "SKIP", detail + f" (Gemini unavailable: {outs[0][0]})"
    return ("FAIL" if unfaithful else "PASS"), detail

def e6():
    t, _, _ = data(); top = C.top_need(t, 10).merge(R.centroids()[["GEOID", "lat", "lon"]], on="GEOID"); top["label"] = top.GEOID
    inv = pd.read_csv("examples/EXAMPLE_food_bank_inventory.csv"); probs = []
    plan, left = R.match_inventory(top.assign(demand=top.low_income_people_far_from_store), inv)
    used = plan.groupby("from_site").pounds.sum()
    for r in inv.itertuples():
        if used.get(r.name, 0) > r.pounds_available + 1: probs.append(f"{r.name} over capacity")
    if set(plan.GEOID) != set(top.GEOID): probs.append(f"{len(set(top.GEOID) - set(plan.GEOID))} tracts unmatched")
    if not plan.miles.between(0.0001, 60).all(): probs.append(f"distance out of range: {plan.miles.min()}–{plan.miles.max()}")
    near = R.nearest_stores(top, pd.read_csv("data/grocery_stores.csv"), 2)
    if not near.miles.between(0, 60).all(): probs.append("store distance out of range")
    return ("FAIL" if probs else "PASS"), "; ".join(probs) or f"{len(plan)} legs, {int(plan.pounds.sum()):,}/{int(inv.pounds_available.sum()):,} lb used, all 10 tracts matched, {plan.miles.min()}–{plan.miles.max()} mi"

def e7():
    from streamlit.testing.v1 import AppTest
    os.environ["USE_GEMINI"] = "0"
    at = AppTest.from_file(os.path.abspath("app.py"), default_timeout=180); at.run()
    if at.exception: return "FAIL", f"step 1 exception: {at.exception[0].message[:200]}"
    at.button[0].click().run()
    if at.exception: return "FAIL", f"after clean: {at.exception[0].message[:200]}"
    heads = [h.value for h in at.header]
    if not all(any(f"Step {k}" in h for h in heads) for k in (1, 2, 3)): return "FAIL", f"missing steps: {heads}"
    at.checkbox[0].check().run()
    if at.exception: return "FAIL", f"routing example: {at.exception[0].message[:200]}"
    # downloads: same objects the buttons serve
    t, i, s = data(); txt, _ = RP.make_report(t, i, s)
    import io
    a = pd.read_csv(io.StringIO(t.to_csv(index=False))); b = pd.read_csv(io.StringIO(i.to_csv(index=False)))
    if len(a) != 968 or len(b) == 0 or len(txt) < 200: return "FAIL", "a download is empty"
    return "PASS", f"3 steps rendered, routing example ran, 0 exceptions; downloads: clean CSV {len(a)} rows, issues CSV {len(b):,} rows, report {len(txt):,} chars"

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--only", default=""); ap.add_argument("--skip-gemini", action="store_true")
    ap.add_argument("--gemini-n", type=int, default=3); ap.add_argument("--random", action="store_true"); a = ap.parse_args()
    only = {int(x) for x in a.only.split(",") if x}
    evals = [(1, "Cleaning correctness (unit tests)", e1), (2, "Real-data integrity", e2), (3, "Source spot-check", lambda: e3(a.random)),
             (4, "Ranking sanity", e4), (5, "Gemini report faithfulness", lambda: e5(a.skip_gemini, a.gemini_n)), (6, "Routing", e6), (7, "End-to-end smoke", e7)]
    t0 = time.time()
    for n, name, fn in evals:
        if only and n not in only: continue
        try: st, d = fn()
        except Exception as ex: st, d = "FAIL", f"crashed: {type(ex).__name__}: {ex}"; traceback.print_exc()
        record(n, name, st, d)
    ts = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
    cnt = {k: sum(r["status"] == k for r in RES) for k in ("PASS", "FAIL", "SKIP")}
    out = dict(timestamp=ts, seconds=round(time.time() - t0, 1), summary=cnt, results=RES)
    json.dump(out, open("evals/results/latest.json", "w"), indent=1)
    md = [f"# Eval scorecard — {ts}", "", f"**{cnt['PASS']} pass · {cnt['FAIL']} fail · {cnt['SKIP']} skip** ({out['seconds']} s)", "", "| # | Eval | Result | Detail |", "|---|---|---|---|"]
    md += [f"| {r['id']} | {r['name']} | {r['status']} | {r['detail'].replace('|', '/')} |" for r in RES]
    open("evals/results/latest.md", "w").write("\n".join(md) + "\n")
    print("\n" + "\n".join(md)); sys.exit(1 if cnt["FAIL"] else 0)

if __name__ == "__main__": main()
