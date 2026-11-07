"""Beacon Data Pre-Cleaner for food banks — one page, three steps."""
import os, json, pandas as pd, plotly.express as px, streamlit as st
import clean as C, routing as R
import plotly.graph_objects as go

st.set_page_config(page_title="Beacon Data Pre-Cleaner", page_icon="🧹", layout="wide")
RAW_OK = os.path.exists(f"{C.B}/places.csv")
CACHE = "data/clean"

@st.cache_data(show_spinner=False)
def run_clean(user_bytes=None, id_col=None):
    up = pd.read_csv(pd.io.common.BytesIO(user_bytes), dtype=str) if user_bytes else None
    if RAW_OK: return C.run(user_df=up, user_id_col=id_col)
    t = pd.read_csv(f"{CACHE}/clean_tracts.csv", dtype={"GEOID": str, "tract": str}); i = pd.read_csv(f"{CACHE}/issues.csv", dtype={"GEOID": str, "tract": str})
    return t, i, json.load(open(f"{CACHE}/summary.json"))

@st.cache_data(show_spinner="Writing the report…")
def report_text(t, i, s):
    base = C.health_report(t, i, s)
    key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not key or os.getenv("USE_GEMINI", "1") != "1": return base, "template"
    try:
        from google import genai
        p = ("Rewrite this data health report for a food bank coordinator in plain English, under 250 words. "
             "Keep every number exactly as given; add no new numbers, places, or claims.\n\n" + base)
        client = genai.Client(api_key=key, http_options={"timeout": 150000})
        return client.models.generate_content(model=os.getenv("GEMINI_MODEL", "gemini-3.8-flash"), contents=p).text, "gemini"
    except Exception as e:
        return base, f"template (Gemini error: {type(e).__name__})"

st.title("🧹 Beacon Data Pre-Cleaner")
st.markdown("Public food-access data comes in separate files with blanks, shaky numbers and mixed years. **This tool combines and checks it for you, so you can trust what you act on.**")

# ---------- Step 1 ----------
st.header("Step 1 · Load the data")
st.caption("We start with DataKind Beacon's free public files for Central Florida. You can add your own spreadsheet too.")
c1, c2 = st.columns([1, 1])
with c1:
    st.markdown("**Included files**")
    for f in ["USDA Food Access Atlas (2 files, 2025 release)", "Census survey tables: SNAP, poverty, income, population (2020–24)", "CDC PLACES health estimates (2025)", "USDA SNAP retailer list"]:
        st.markdown(f"- {f}")
with c2:
    up = st.file_uploader("Optional: add your own CSV (needs a census tract ID column)", type="csv")
    id_col = None; ub = None
    if up:
        ub = up.getvalue(); cols = pd.read_csv(pd.io.common.BytesIO(ub), nrows=0).columns.tolist()
        guess = next((c for c in cols if any(k in c.lower() for k in ["geoid", "tract", "fips"])), cols[0])
        id_col = st.selectbox("Which column has the tract ID?", cols, index=cols.index(guess))
clicked = st.button("🧹 Clean the data", type="primary")
if clicked: st.session_state.cleaned = True
if not st.session_state.get("cleaned"):
    st.stop()

with st.spinner("Joining and checking files…"):
    t, issues, s = run_clean(ub, id_col)

# ---------- Step 2 ----------
st.header("Step 2 · Clean and check")
st.caption("We match every file on the same 11-digit neighborhood ID, rename columns in plain English, and flag anything that looks wrong.")
m = st.columns(4)
m[0].metric("Files in", s["files_in"]); m[1].metric("Neighborhoods in 1 clean table", s["tracts"])
m[2].metric("Problems found", f"{s['problems']:,}"); m[3].metric("Flagged for a person to check", s["flagged"])
st.markdown(f"✅ **{s['fixed']:,} fixed or filled automatically** · 🔁 {s['id_fixes']:,} neighborhood IDs reformatted · 🚫 {s['left_out']} left out of rankings")
if s.get("user_match"): st.info(f"Your file: {s['user_match'][0]} of {s['user_match'][1]} rows matched a Central Florida neighborhood.")
EXPL = {"missing": "Blank in the source file", "mixed years": "Filled from an older source (years differ)", "unreliable": "Shaky estimate (big margin of error)",
        "group quarters": "Mostly dorms, prisons or care homes", "tiny population": "Very few residents", "fixed": "Impossible or coded value fixed"}
bt = pd.DataFrame([{"Problem": EXPL.get(k, k), "Count": v} for k, v in sorted(s["by_type"].items(), key=lambda x: -x[1])])
st.dataframe(bt, hide_index=True, use_container_width=False)
st.caption("Most 'blank' problems are CDC food-insecurity and transportation numbers, which CDC doesn't publish for any Florida neighborhood.")

# ---------- Step 3 ----------
st.header("Step 3 · Results")
st.caption("Your clean files, a plain-English health report, and what the clean data shows.")
txt, mode = report_text(t, issues, s)
a, b = st.columns([1.2, 1])
with a:
    st.markdown(txt.replace("# Data Health", "### Data Health").replace("\n## ", "\n#### "))
    st.caption("Report written by Gemini from the numbers above" if mode == "gemini" else f"Report from a fixed template ({mode}). Set GEMINI_API_KEY to have Gemini write it.")
with b:
    st.markdown("**Download**")
    st.download_button("⬇️ Clean table (CSV)", t.to_csv(index=False), "clean_tracts.csv", "text/csv", use_container_width=True)
    st.download_button("⬇️ Problem list (CSV)", issues.to_csv(index=False), "data_issues.csv", "text/csv", use_container_width=True)
    st.download_button("⬇️ Health report (Markdown)", txt, "data_health_report.md", use_container_width=True)

st.subheader("What the clean data shows")
st.caption("Neighborhoods USDA lists as low income and far from groceries, ranked by how many low-income residents live far from a store. Dorm-heavy, tiny and shaky neighborhoods are left out.")
top = C.top_need(t, 10).merge(R.centroids()[["GEOID", "lat", "lon"]], on="GEOID")
top["label"] = top.county + " tract " + top.tract
stores = pd.read_csv("data/grocery_stores.csv")
near = R.nearest_stores(top, stores, k=2)
inv_file = st.file_uploader("Optional: your food bank inventory / pantry locations (CSV: name, lat, lon, pounds_available)", type="csv", key="inv")
use_example = st.checkbox("Try it with the made-up EXAMPLE inventory file", value=False)
plan = None
if inv_file is not None or use_example:
    inv = pd.read_csv(inv_file) if inv_file is not None else pd.read_csv("examples/EXAMPLE_food_bank_inventory.csv")
    plan, left = R.match_inventory(top.assign(demand=top.low_income_people_far_from_store), inv)
l, r = st.columns([1, 1.2])
with l:
    first = near.groupby("GEOID").first().reset_index().set_index("GEOID").reindex(top.GEOID)
    st.dataframe(pd.DataFrame({"Neighborhood": top.label.values, "Low-income people far from a store": top.low_income_people_far_from_store.astype(int).values,
        "Homes with no car, far": top.car_free_homes_far_from_store.fillna(0).astype(int).values,
        "Nearest grocery (SNAP)": first.store.values, "Miles (straight line)": first.miles.values}), hide_index=True, use_container_width=True)
    if plan is not None:
        st.markdown("**Suggested routing from your inventory**" + (" — ⚠️ EXAMPLE data, not real" if inv_file is None else ""))
        st.dataframe(plan[["from_site", "to", "pounds", "miles"]].rename(columns={"from_site": "From", "to": "To", "pounds": "Pounds", "miles": "Miles"}), hide_index=True, use_container_width=True)
        st.caption("Each neighborhood gets a share of total pounds in proportion to its low-income residents far from a store, taken from the nearest site with food left.")
with r:
    gj = json.load(open("data/tracts.geojson"))
    t["Status"] = "Other"; t.loc[t.left_out_of_ranking | t.needs_review, "Status"] = "Check data first"; t.loc[t.GEOID.isin(top.GEOID), "Status"] = "Top 10 need"
    fig = px.choropleth_map(t, geojson=gj, locations="GEOID", color="Status", hover_name=t.county + " tract " + t.tract,
        color_discrete_map={"Top 10 need": "#d7301f", "Check data first": "#bdbdbd", "Other": "#fdd49e"},
        map_style="carto-positron", center={"lat": 28.4, "lon": -81.5}, zoom=7, opacity=0.7, height=480)
    links = plan if plan is not None else near
    color, name = ("#2c7fb8", "Suggested delivery") if plan is not None else ("#238b45", "Nearest grocery")
    for k, x in enumerate(links.itertuples()):
        fig.add_trace(go.Scattermap(lat=[x.lat, x.s_lat], lon=[x.lon, x.s_lon], mode="lines+markers", line=dict(width=2, color=color),
            marker=dict(size=[4, 8]), name=name, showlegend=k == 0, hoverinfo="text", text=f"{x.miles} mi"))
    fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), legend=dict(title=""))
    st.plotly_chart(fig, use_container_width=True)
st.caption("Public data only. Distances are straight-line miles, not driving routes. This tool has no surplus or inventory data of its own; routing appears only when you upload yours (or the labeled example).")
