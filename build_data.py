"""Build tract-level dataset for the Food Access Action Board from real public files in data/.
Run: .venv/bin/python build_data.py  -> data/tracts.csv, data/tracts.geojson, data/sources.json"""
import json, zipfile, io, datetime, pandas as pd, numpy as np, shapefile
B = "data/beacon"
COUNTIES = {"095":"Orange","117":"Seminole","097":"Osceola","069":"Lake",
            "127":"Volusia","009":"Brevard","105":"Polk","119":"Sumter"}
BEACON_COUNTIES = {"Orange","Seminole","Osceola","Lake"}

def acs(path, cols):
    d = pd.read_csv(path, skiprows=[1], dtype=str)
    d = d[d.GEO_ID.str.startswith("1400000US12")]
    d["GEOID"] = d.GEO_ID.str[-11:]
    out = d[["GEOID"]].copy()
    for c, name in cols.items():
        out[name] = pd.to_numeric(d[c].str.replace(",", "").str.replace("+","").str.replace("-",""), errors="coerce") if c in d else np.nan
        out.loc[d[c].isin(["-","N","(X)","**","***"]).values, name] = np.nan
    return out

snap = acs(f"{B}/snap/ACSST5Y2024.S2201-Data.csv", {"S2201_C01_001E":"households","S2201_C03_001E":"snap_households","S2201_C04_001E":"snap_pct","S2201_C04_001M":"snap_pct_moe"})
pov  = acs(f"{B}/poverty/ACSST5Y2024.S1701-Data.csv", {"S1701_C03_001E":"poverty_pct","S1701_C03_001M":"poverty_pct_moe"})
inc  = acs(f"{B}/income/ACSST5Y2024.S1901-Data.csv", {"S1901_C01_012E":"median_income"})
pop  = acs(f"{B}/pop/ACSST5Y2024.S0101-Data.csv", {"S0101_C01_001E":"population"})
acsd = snap.merge(pov,on="GEOID",how="outer").merge(inc,on="GEOID",how="outer").merge(pop,on="GEOID",how="outer")

g = pd.read_csv(f"{B}/fara2025/SRAM General Tract Characteristics Data.csv", dtype={"CensusTract20":str}, encoding="latin-1")
dd = pd.read_csv(f"{B}/fara2025/SRAM Driving Distance Data.csv", dtype={"CensusTract20":str}, encoding="latin-1")
fara = g.merge(dd.drop(columns=["State","County20","County24"]), on="CensusTract20")
fara["GEOID"] = fara.CensusTract20.str.zfill(11)
fara = fara[fara.GEOID.str[:2].eq("12") & fara.GEOID.str[2:5].isin(COUNTIES)]
u = fara.Urban.eq(1)
f = pd.DataFrame({"GEOID":fara.GEOID, "urban":u,
  "usda_low_income_tract":fara.LowIncomeTracts,
  "usda_lila_flag":fara.DD_SRAM_LILATracts_1And10,
  "usda_lila_vehicle_flag":fara.DD_SRAM_LILATracts_Vehicle,
  "pop2020":fara.POP2020, "hu_no_vehicle":fara.TractHUNV,
  "lowinc_far_pct":np.where(u, fara.DD_SRAM_lalowi1share, fara.DD_SRAM_lalowi10share),
  "novehicle_far_pct":np.where(u, fara.DD_SRAM_lahunv1share, fara.DD_SRAM_lahunv10share),
  "novehicle_far_units":np.where(u, fara.DD_SRAM_lahunv1, fara.DD_SRAM_lahunv10),
  "fara_poverty_pct":fara.PovertyRate, "fara_snap_pct":fara.TractSNAP/fara.OHU2020*100})
# blanks in FARA share columns mean 0 people beyond distance only when flagged as not low access; keep NaN honest
pl = pd.read_csv(f"{B}/places.csv", dtype={"TractFIPS":str,"CountyFIPS":str},
     usecols=["StateAbbr","CountyFIPS","TractFIPS","TotalPopulation","FOODINSECU_CrudePrev","FOODINSECU_Crude95CI","FOODSTAMP_CrudePrev","LACKTRPT_CrudePrev","DIABETES_CrudePrev"])
pl = pl[pl.StateAbbr.eq("FL")]; pl["GEOID"]=pl.TractFIPS.str.zfill(11)
pl = pl.rename(columns={"FOODINSECU_CrudePrev":"food_insecure_pct","FOODINSECU_Crude95CI":"food_insecure_ci","FOODSTAMP_CrudePrev":"places_snap_pct","LACKTRPT_CrudePrev":"lack_transport_pct","DIABETES_CrudePrev":"diabetes_pct"})[["GEOID","food_insecure_pct","food_insecure_ci","places_snap_pct","lack_transport_pct","diabetes_pct"]]

# geometry (Census cartographic boundary 2023, 2020-vintage tracts)
z = zipfile.ZipFile("data/tr.zip"); n="cb_2023_12_tract_500k"
r = shapefile.Reader(shp=io.BytesIO(z.read(n+".shp")), dbf=io.BytesIO(z.read(n+".dbf")), shx=io.BytesIO(z.read(n+".shx")))
feats, polys, names = [], {}, {}
for sr in r.iterShapeRecords():
    rec = sr.record.as_dict()
    if rec["COUNTYFP"] not in COUNTIES: continue
    geo = sr.shape.__geo_interface__
    def rnd(c): return [[round(x,4),round(y,4)] for x,y in c]
    if geo["type"]=="Polygon": geo["coordinates"]=[rnd(ring) for ring in geo["coordinates"]]
    else: geo["coordinates"]=[[rnd(ring) for ring in p] for p in geo["coordinates"]]
    feats.append({"type":"Feature","id":rec["GEOID"],"properties":{},"geometry":geo})
    rings = [geo["coordinates"][0]] if geo["type"]=="Polygon" else [p[0] for p in geo["coordinates"]]
    polys[rec["GEOID"]] = rings; names[rec["GEOID"]] = (rec["NAME"], COUNTIES[rec["COUNTYFP"]], rec["ALAND"])
json.dump({"type":"FeatureCollection","features":feats}, open("data/tracts.geojson","w"))

# SNAP retailers per tract (point in polygon)
s = pd.read_csv(f"{B}/snap_retailers.csv", usecols=["Store_Name","Store_Type","Latitude","Longitude","State","County","City","Store_Street_Address"])
s = s[s.State.eq("FL") & s.County.str.upper().isin([c.upper() for c in COUNTIES.values()])]
def inside(x,y,ring):
    c=False; j=len(ring)-1
    for i in range(len(ring)):
        xi,yi=ring[i]; xj,yj=ring[j]
        if (yi>y)!=(yj>y) and x < (xj-xi)*(y-yi)/(yj-yi+1e-12)+xi: c=not c
        j=i
    return c
bbox={k:[(min(p[0] for p in r_),min(p[1] for p in r_),max(p[0] for p in r_),max(p[1] for p in r_),r_) for r_ in v] for k,v in polys.items()}
cnt={k:0 for k in polys}; groc={k:0 for k in polys}
GROCERY={"Supermarket","Super Store","Grocery Store","Farmers and Markets"}
stores=[]
for row in s.itertuples():
    x,y=row.Longitude,row.Latitude
    for k,bs in bbox.items():
        if any(b[0]<=x<=b[2] and b[1]<=y<=b[3] and inside(x,y,b[4]) for b in bs):
            cnt[k]+=1; groc[k]+= row.Store_Type in GROCERY; break
stores = s[s.Store_Type.isin(GROCERY)][["Store_Name","Store_Type","Latitude","Longitude","County","City","Store_Street_Address"]]
stores.to_csv("data/grocery_stores.csv", index=False)

base = pd.DataFrame([{"GEOID":k,"tract_name":v[0],"county":v[1],"land_sqmi":v[2]/2.59e6,
        "snap_retailers":cnt[k],"grocery_type_retailers":groc[k]} for k,v in names.items()])
df = base.merge(f,on="GEOID",how="left").merge(pl,on="GEOID",how="left").merge(acsd,on="GEOID",how="left")
df["in_beacon_sample"]=df.county.isin(BEACON_COUNTIES)
df.to_csv("data/tracts.csv", index=False)
today=datetime.date.today().isoformat()
json.dump([
 {"name":"USDA ERS Food Access Research Atlas – SNAP-authorized Retailer Access Map (driving distance)","vintage":"Initial release July 2026; 2020 census tracts/pop","via":"Beacon example data folder","downloaded":today},
 {"name":"ACS 5-year 2020–2024 Subject Tables S2201 (SNAP), S1701 (poverty), S1901 (income), S0101 (population)","vintage":"2024 5-year","via":"Beacon example data folder (Orange, Seminole, Osceola, Lake only)","downloaded":today},
 {"name":"CDC PLACES census tract data (GIS friendly), 2025 release – food insecurity, SNAP, lack of transportation","vintage":"2025 release (model-based estimates from BRFSS ~2022-2023)","via":"Beacon example data folder","downloaded":today},
 {"name":"USDA SNAP Retailer Location data","vintage":"as provided in Beacon folder","via":"Beacon example data folder","downloaded":today},
 {"name":"Census cartographic boundary tracts cb_2023_12_tract_500k","vintage":"2023 (2020 tract definitions)","via":"www2.census.gov","downloaded":today}],
 open("data/sources.json","w"), indent=1)
print(df.groupby("county").agg(n=("GEOID","size"),acs=("snap_pct","count"),places=("food_insecure_pct","count"),fara=("usda_lila_flag","count"),stores=("snap_retailers","sum")))
