import os, sys, numpy as np, pandas as pd, pytest
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from clean import fix_geoid, to_number, tract_name, clean, Log

def test_fix_geoid():
    assert fix_geoid("1400000US12095016510") == "12095016510"
    assert fix_geoid(12095016510.0) == "12095016510"
    assert fix_geoid("1209501651") == "01209501651"
    assert fix_geoid("12-095-016510") == "12095016510"
    assert fix_geoid("abc") is None and fix_geoid(None) is None

def test_to_number():
    assert to_number("1,234") == (1234.0, None)
    assert to_number("250,000+") == (250000.0, "top/bottom-coded")
    v, n = to_number("-"); assert np.isnan(v) and n == "suppressed"
    v, n = to_number("(X)"); assert n == "suppressed"

def test_tract_name():
    assert tract_name("12095016510") == "165.10" and tract_name("12095016500") == "165"

def _src(gq=0.0, pop=5000, pov=30.0, moe=2.0, far=120.0):
    g = "12095016510"
    usda = pd.DataFrame([dict(GEOID=g, urban=True, population_2020=pop, homes_2020=2000, group_quarters_pct=gq, usda_poverty_pct=pov,
        usda_snap_homes=200, homes_without_car=50, usda_low_income_low_access=1, people_far_from_store=100,
        low_income_people_far_from_store=50, low_income_far_from_store_pct=far, car_free_homes_far_from_store=5)])
    acs = pd.DataFrame([dict(GEOID=g, households=2000, snap_households_pct=10.0, snap_households_pct_moe=moe, poverty_pct=pov, poverty_pct_moe=moe,
        median_household_income=50000, population_2024=pop)])
    places = pd.DataFrame([dict(GEOID=g, food_insecurity_pct=np.nan, lack_transportation_pct=np.nan, diabetes_pct=12.0)])
    return dict(acs=acs, usda=usda, places=places, stores=pd.DataFrame(columns=["county", "snap_stores_in_county"]), files=["a"], log=Log())

def test_flags_group_quarters_and_caps():
    t, issues, s = clean(_src(gq=47.0, far=121.5))
    r = t.iloc[0]
    assert r.left_out_of_ranking and "dorms" in r.review_reasons
    assert r.low_income_far_from_store_pct == 100.0
    assert set(issues.type) >= {"missing", "group quarters", "fixed"}

def test_shaky_and_tiny():
    t, issues, s = clean(_src(pop=300, moe=9.0, pov=10.0))
    assert "unreliable" in set(issues.type) and "tiny population" in set(issues.type)

def test_user_upload_join():
    up = pd.DataFrame({"Tract ID": ["1400000US12095016510", "99999"], "Pantry visits": [10, 3]})
    t, _, s = clean(_src(), up, "Tract ID")
    assert s["user_match"] == (1, 2) and t.iloc[0].your_pantry_visits == 10

def test_routing():
    from routing import haversine, nearest_stores, match_inventory
    assert abs(haversine(28.5383, -81.3792, 28.0395, -81.9498) - 47.4) < 2
    need = pd.DataFrame({"GEOID": ["a", "b"], "label": ["A", "B"], "lat": [28.0, 28.5], "lon": [-81.9, -81.4], "demand": [300, 100]})
    st = pd.DataFrame({"Store_Name": ["X", "Y"], "Store_Type": ["Supermarket"] * 2, "Store_Street_Address": ["1", "2"], "City": ["c", "d"], "Latitude": [28.01, 28.51], "Longitude": [-81.9, -81.4]})
    ns = nearest_stores(need, st, k=1); assert list(ns.store) == ["X", "Y"]
    inv = pd.DataFrame({"name": ["near_a", "near_b"], "lat": [28.0, 28.5], "lon": [-81.9, -81.4], "pounds_available": [100, 300]})
    plan, left = match_inventory(need, inv)
    assert plan.pounds.sum() == 400 and left.left.sum() == 0
    assert plan[plan.GEOID == "a"].pounds.sum() == 300
