import json, os, datetime, pandas as pd, numpy as np, plotly.express as px, streamlit as st
from logic import INDICATORS, load, score, flags, quality, why, template_brief, gemini_brief

st.set_page_config(page_title="Food Access Action Board · Central Florida", page_icon="🥫", layout="wide")
DEC = "data/decisions.csv"

@st.cache_data
def base(): return load()
@st.cache_data
def geo(): return json.load(open("data/tracts.geojson"))
SOURCES = json.load(open("data/sources.json"))

def decisions():
    return pd.read_csv(DEC, dtype={"GEOID": str}) if os.path.exists(DEC) else pd.DataFrame(columns=["GEOID","label","decision","action","note","reviewer","timestamp"])

# ---------- sidebar: weights & filters ----------
st.sidebar.header("⚖️ What matters most?")
st.sidebar.caption("Move a slider to change how much each measure counts. The map and lists update instantly.")
weights = {k: st.sidebar.slider(lab, 0, 50, w, 5, help=tip) for k, (lab, tip, w) in INDICATORS.items()}
if sum(weights.values()) == 0: weights["poverty"] = 1
counties = st.sidebar.multiselect("Counties", sorted(base().county.unique()), default=sorted(base().county.unique()))
reviewer = st.sidebar.text_input("Your name (for approvals)", "Coordinator")

df = flags(score(base(), weights)); view = df[df.county.isin(counties)]
ravg = {k: df[f"{k}_val"].mean() for k in INDICATORS}
def cavg(c): return {k: df[df.county == c][f"{k}_val"].mean() for k in INDICATORS}

st.title("🥫 Food Access Action Board — Central Florida")
st.markdown("**Need score (0–100):** how a neighborhood (census tract) ranks against the other 968 Central Florida tracts on poverty, SNAP use, distance to groceries and car access. **Higher = more need.**")

tabs = st.tabs(["🏠 What to do next", "🗺️ Map", "📋 Ranked list", "🔎 Neighborhood detail", "🕳️ Data gaps", "📊 County comparison", "✅ Action list"])

# ---------- home ----------
with tabs[0]:
    st.info("**Start here.** These three lists are the suggested actions for this month. Click *Neighborhood detail* to see the evidence and approve or reject each one.")
    big = view[view["pop"] >= 1000]
    mob = big[big.car_gap].sort_values("need_score", ascending=False).head(3)
    snapg = view[view.snap_gap].sort_values("poverty_val", ascending=False).head(5)
    ver = view[view.verify_first].sort_values("need_score", ascending=False).head(5)
    c1, c2, c3 = st.columns(3)
    with c1:
        st.subheader("🚚 Top 3 places to try a mobile pantry stop")
        st.caption("Why: many homes with no car are far from any SNAP-accepting grocery store.")
        for r in mob.itertuples():
            st.markdown(f"**{r.label}** — score {r.need_score:.0f}  \n{int(r.novehicle_far_units)} car-free homes far from a store · poverty {r.poverty_val:.1f}%")
    with c2:
        st.subheader("📝 SNAP enrollment outreach")
        st.caption("Why: poverty is high but SNAP use is noticeably lower than the poverty rate — eligible families may not be enrolled.")
        for r in snapg.itertuples():
            st.markdown(f"**{r.label}** — poverty {r.poverty_val:.1f}% vs SNAP {r.snap_val:.1f}%")
    with c3:
        st.subheader("🔍 Verify data before acting")
        st.caption("Why: high need score, but the numbers are shaky (small sample, blank or out-of-range values).")
        for r in ver.itertuples():
            st.markdown(f"**{r.label}** — score {r.need_score:.0f}  \n{[x for x in quality(df.loc[r.Index]) if 'sample' in x or 'above' in x or 'blank for this' in x or 'Small' in x][0]}")
    st.divider()
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Tracts shown", len(view))
    m2.metric("USDA low-income & low-access tracts", int((view.usda_lila_flag == 1).sum()))
    m3.metric("'Hidden need' tracts (not USDA-flagged)", int(view.hidden_need.sum()), help="High poverty or SNAP use and many low-income people far from stores, but NOT on USDA's official low-access list.")
    m4.metric("Car-free homes far from a store", f"{int(view.novehicle_far_units.sum()):,}")

# ---------- map ----------
with tabs[1]:
    st.caption("🟥 Red = highest need · 🟨 yellow = lowest. Hover a neighborhood for details.")
    fig = px.choropleth_map(view, geojson=geo(), locations="GEOID", color="need_score", color_continuous_scale="YlOrRd", range_color=(0, 100),
        hover_name="label", hover_data={"GEOID": False, "need_score": ":.0f", "poverty_val": ":.1f", "snap_val": ":.1f", "lowinc_far_val": ":.1f", "novehicle_far_units": True},
        labels={"need_score": "Need score", "poverty_val": "Poverty %", "snap_val": "SNAP %", "lowinc_far_val": "Low income & far from grocery %", "novehicle_far_units": "Car-free homes far from store"},
        map_style="carto-positron", center={"lat": 28.5, "lon": -81.5}, zoom=7.3, opacity=0.7, height=620)
    fig.update_layout(margin=dict(l=0, r=0, t=0, b=0))
    st.plotly_chart(fig, use_container_width=True)
    st.success("➡️ **Next step:** open the red areas in *Neighborhood detail* and approve the ones your team should act on.")

# ---------- ranked ----------
with tabs[2]:
    n = st.slider("How many to show", 10, 100, 25, 5)
    t = view.sort_values("need_score", ascending=False).head(n)
    show = pd.DataFrame({"Rank": t["rank"], "Neighborhood": t.label, "Need score": t.need_score.round(0), "Poverty %": t.poverty_val.round(1),
        "SNAP %": t.snap_val.round(1), "Low income & far from grocery %": t.lowinc_far_val.round(1), "Car-free homes far from store": t.novehicle_far_units,
        "USDA low-access list?": t.usda_lila_flag.map({1: "Yes", 0: "No"}), "Why flagged": t.apply(why, axis=1)})
    st.dataframe(show, hide_index=True, use_container_width=True)
    st.success(f"➡️ **Next step:** review the top {min(n,10)} in *Neighborhood detail* and approve or reject each.")

# ---------- detail ----------
with tabs[3]:
    opts = view.sort_values("need_score", ascending=False)
    sel = st.selectbox("Pick a neighborhood (sorted by need)", opts.GEOID, format_func=lambda g: f"#{df.set_index('GEOID').loc[g,'rank']} · {df.set_index('GEOID').loc[g,'label']} · score {df.set_index('GEOID').loc[g,'need_score']:.0f}")
    r = df[df.GEOID == sel].iloc[0]; ca = cavg(r.county)
    a, b = st.columns([1.1, 1])
    with a:
        st.subheader(f"{r.label}")
        st.markdown(f"**Need score {r.need_score:.0f}/100** (rank #{r['rank']} of {len(df)}). Why flagged: {why(r)}.")
        ev = pd.DataFrame([{"Measure": INDICATORS[k][0], "This neighborhood": r[f"{k}_val"], f"{r.county} County avg": ca[k], "Region avg": ravg[k]}
                           for k in ["poverty", "snap", "lowinc_far", "novehicle_far", "diabetes"]]).round(1)
        st.dataframe(ev, hide_index=True, use_container_width=True)
        st.caption(f"Population ≈ {int(r['pop']):,} · grocery-type SNAP stores inside tract: {int(r.grocery_type_retailers)} · all SNAP stores: {int(r.snap_retailers)} · median household income: {'$'+format(int(r.median_income),',') if pd.notna(r.median_income) else 'not in Beacon sample'}")
        st.markdown("**⚠️ Data cautions**")
        for w in quality(r): st.markdown(f"- {w}")
    with b:
        st.subheader("🧾 Action brief")
        if st.button("Generate brief"):
            st.session_state[f"brief_{sel}"] = gemini_brief(r, ca, ravg)
        txt, mode = st.session_state.get(f"brief_{sel}", (template_brief(r, ca, ravg), "template"))
        st.caption("Written by Gemini from this tract's numbers only" if mode == "gemini" else "Written from a fixed template using this tract's numbers (set GEMINI_API_KEY to use Gemini)")
        st.markdown(txt)
        st.divider()
        st.markdown("**Your decision**")
        action = st.selectbox("Proposed action", ["Mobile pantry stop", "SNAP enrollment outreach", "Verify data with local partners", "Home delivery pilot", "Other"])
        note = st.text_area("Note for your team (optional)")
        c1, c2, c3 = st.columns(3)
        for col, dec in [(c1, "Approve"), (c2, "Reject"), (c3, "Needs discussion")]:
            if col.button(dec, key=dec):
                d = decisions()
                d = pd.concat([d, pd.DataFrame([{"GEOID": sel, "label": r.label, "decision": dec, "action": action, "note": note, "reviewer": reviewer, "timestamp": datetime.datetime.now().isoformat(timespec="seconds")}])])
                d.to_csv(DEC, index=False); st.success(f"Saved: {dec}")
        hist = decisions(); hist = hist[hist.GEOID == sel]
        if len(hist):
            latest = hist.sort_values("timestamp").groupby("reviewer").tail(1)
            if latest.decision.nunique() > 1: st.warning("Team members disagree on this neighborhood: " + "; ".join(f"{x.reviewer}: {x.decision}" for x in latest.itertuples()))
            st.dataframe(hist[["reviewer", "decision", "action", "note", "timestamp"]], hide_index=True)

# ---------- gaps ----------
with tabs[4]:
    st.markdown("Where the public data is **missing, stale, or disagrees with itself** — and what that means for your decisions.")
    g1, g2 = st.columns(2)
    with g1:
        st.subheader("1. Hidden need")
        st.caption("High poverty or SNAP use and many low-income people far from stores — but NOT on USDA's official low-access list. Easy to miss if you only use the USDA map.")
        h = view[view.hidden_need].sort_values("need_score", ascending=False)
        st.dataframe(pd.DataFrame({"Neighborhood": h.label, "Need score": h.need_score.round(0), "Poverty %": h.poverty_val.round(1), "SNAP %": h.snap_val.round(1), "Low income & far %": h.lowinc_far_val.round(1)}), hide_index=True, height=300)
        st.subheader("3. Small-sample estimates")
        sm = view[(view.snap_pct_moe / view.snap_pct > .5) & view.snap_pct.gt(0)]
        st.caption(f"{len(sm)} tracts have a SNAP estimate where the margin of error is more than half the value.")
    with g2:
        st.subheader("2. Coverage holes by county")
        cov = view.groupby("county").agg(Tracts=("GEOID", "size"), **{"Current Census survey (ACS 2020-24)": ("snap_pct", "count"), "USDA grocery distance": ("lowinc_far_pct", "count"), "CDC food insecurity": ("food_insecure_pct", "count"), "CDC lack of transportation": ("lack_transport_pct", "count")}).reset_index()
        st.dataframe(cov, hide_index=True)
        st.caption("The Beacon sample has current Census data only for Orange, Seminole, Osceola and Lake. CDC food-insecurity and transportation estimates are blank for all Florida tracts.")
        st.subheader("4. Indicators that disagree")
        dis = view[(view.usda_lila_flag == 1) & (view.poverty_val < view.poverty_val.median())]
        st.caption(f"{len(dis)} USDA low-income/low-access tracts have below-median poverty — the USDA flag uses older income data, so check before acting.")
        st.dataframe(pd.DataFrame({"Neighborhood": dis.label, "Poverty %": dis.poverty_val.round(1), "Source": dis.poverty_src}), hide_index=True, height=200)
    st.success("➡️ **Next step:** treat 'hidden need' tracts as candidates to ask local partners about, and verify small-sample tracts before committing resources.")

# ---------- county ----------
with tabs[5]:
    cc = df.groupby("county").agg(**{"Tracts": ("GEOID", "size"), "Avg need score": ("need_score", "mean"), "Poverty % (avg)": ("poverty_val", "mean"), "SNAP % (avg)": ("snap_val", "mean"),
        "Car-free homes far from store": ("novehicle_far_units", "sum"), "USDA low-access tracts": ("usda_lila_flag", "sum"), "Hidden-need tracts": ("hidden_need", "sum"), "Tracts in region top 50": ("rank", lambda s: int((s <= 50).sum()))}).round(1).reset_index().sort_values("Avg need score", ascending=False)
    st.dataframe(cc, hide_index=True, use_container_width=True)
    st.plotly_chart(px.bar(cc, x="county", y="Car-free homes far from store", color="Avg need score", color_continuous_scale="YlOrRd", title="Homes with no car, far from a grocery store"), use_container_width=True)
    top = cc.iloc[0]
    st.success(f"➡️ **Next step:** {top.county} County has the highest average need score ({top['Avg need score']}); start review there.")

# ---------- action list ----------
with tabs[6]:
    d = decisions()
    if len(d):
        latest = d.sort_values("timestamp").groupby("GEOID").tail(1)
        appr = latest[latest.decision == "Approve"].merge(df[["GEOID", "need_score", "poverty_val", "snap_val", "lowinc_far_val", "novehicle_far_units"]], on="GEOID")
        st.subheader(f"Approved actions ({len(appr)})"); st.dataframe(appr, hide_index=True, use_container_width=True)
        st.download_button("⬇️ Export Action List (CSV)", appr.to_csv(index=False), "action_list.csv", "text/csv")
        st.caption("All decisions (full history):"); st.dataframe(d, hide_index=True)
    else:
        st.info("No decisions yet. Approve neighborhoods in *Neighborhood detail* and they'll appear here for export.")

with st.expander("ℹ️ Data sources & how the score works"):
    st.markdown("Each measure is turned into a percentile (0–100) across all 968 tracts, then combined using the slider weights. Missing measures are skipped and the remaining weights re-balanced.")
    st.table(pd.DataFrame(SOURCES))
