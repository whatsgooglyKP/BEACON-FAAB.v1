"""Simple need-to-supply matching. Straight-line (haversine) miles, not road routes.
No surplus/inventory data is included; inventory only comes from a user's own upload."""
import json, numpy as np, pandas as pd

def haversine(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    a = np.sin((lat2 - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2
    return 3958.8 * 2 * np.arcsin(np.sqrt(a))

def centroids(geojson_path="data/tracts.geojson"):
    rows = []
    for f in json.load(open(geojson_path))["features"]:
        g = f["geometry"]; ring = g["coordinates"][0] if g["type"] == "Polygon" else max((p[0] for p in g["coordinates"]), key=len)
        a = np.array(ring); rows.append((f["id"], a[:, 1].mean(), a[:, 0].mean()))
    return pd.DataFrame(rows, columns=["GEOID", "lat", "lon"])

def nearest_stores(need, stores, k=2):
    """need: GEOID, lat, lon (+ label). stores: Store_Name, Latitude, Longitude. Returns k nearest per tract."""
    out = []
    for r in need.itertuples():
        d = haversine(r.lat, r.lon, stores.Latitude.values, stores.Longitude.values)
        for j in np.argsort(d)[:k]:
            s = stores.iloc[j]
            out.append(dict(GEOID=r.GEOID, label=r.label, store=s.Store_Name.title(), store_type=s.Store_Type, address=f"{s.Store_Street_Address}, {s.City}",
                            miles=round(float(d[j]), 1), lat=r.lat, lon=r.lon, s_lat=s.Latitude, s_lon=s.Longitude))
    return pd.DataFrame(out)

def match_inventory(need, inv, demand_col="demand"):
    """Greedy: highest-need tract first; take pounds from the nearest site with capacity left until its demand is met.
    need: GEOID, label, lat, lon, demand (relative units, e.g. low-income people far from a store). inv: name, lat, lon, pounds_available."""
    inv = inv.copy(); inv["left"] = pd.to_numeric(inv.pounds_available, errors="coerce").fillna(0).astype(float)
    total_need = need[demand_col].sum(); total_lbs = inv.left.sum()
    plan = []
    for r in need.itertuples():
        want = getattr(r, demand_col) / total_need * total_lbs if total_need else 0  # share supply in proportion to need
        d = haversine(r.lat, r.lon, inv.lat.astype(float).values, inv.lon.astype(float).values)
        for j in np.argsort(d):
            if want <= 0.5: break
            if inv.left.iat[j] <= 0: continue
            take = min(want, inv.left.iat[j]); inv.iat[j, inv.columns.get_loc("left")] -= take; want -= take
            plan.append(dict(GEOID=r.GEOID, to=r.label, from_site=inv.name.iat[j], pounds=round(take), miles=round(float(d[j]), 1),
                             lat=r.lat, lon=r.lon, s_lat=float(inv.lat.iat[j]), s_lon=float(inv.lon.iat[j])))
    return pd.DataFrame(plan), inv
