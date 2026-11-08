"""Rebuild Central Florida place labels from official Census TIGER/Line 2024.

Run from the repository root: python scripts/build_place_names.py [--verify].
Polygons and tract internal points are cached locally, never committed. Labels
use supplied map points first; one missing point uses its TIGER tract internal
point. A point outside every incorporated place/CDP gets an unincorporated label.
This is point containment, not majority area, a neighborhood identity or a service
boundary. No score, raw observation or supplied map coordinate is altered.
"""
from pathlib import Path
import argparse
import hashlib
import json
import sys
import urllib.request
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pandas as pd
from indicators import load_community,SOURCE_URL

RAW=Path('data/geography/raw')
OUT=Path('data/clean/tract_place_names.csv')
META=Path('data/clean/tract_place_names.sources.json')
URLS={
 'tl_2024_12_place.zip':'https://www2.census.gov/geo/tiger/TIGER2024/PLACE/tl_2024_12_place.zip',
 'tl_2024_12_tract.zip':'https://www2.census.gov/geo/tiger/TIGER2024/TRACT/tl_2024_12_tract.zip',
}


def fetch_sources():
    """Download public boundary archives once; always record their exact SHA-256."""
    RAW.mkdir(parents=True,exist_ok=True);sources=[]
    for name,url in URLS.items():
        path=RAW/name
        if not path.exists():
            with urllib.request.urlopen(url,timeout=120) as response:
                data=response.read()
            path.write_bytes(data)
        sources.append(dict(file=name,url=url,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),vintage='2024'))
    return sources


def build_lookup(table,places,tracts):
    """Point-in-polygon join, with a documented internal-point fallback and no guesses."""
    import geopandas as gpd
    places=places.to_crs('EPSG:4326').sort_values('GEOID')
    tracts=tracts.set_index('GEOID');rows=[]
    for r in table.sort_values('tract_id').itertuples():
        lat,lon=r.lat,r.lon;point_source='Beacon PLACES map point';point_url=SOURCE_URL
        if pd.isna(lat) or pd.isna(lon):
            if r.tract_id not in tracts.index: raise ValueError(f'No official point for tract {r.tract_id}')
            point=tracts.loc[r.tract_id];lat=float(point.INTPTLAT);lon=float(point.INTPTLON)
            point_source='TIGER/Line 2024 tract internal point';point_url=URLS['tl_2024_12_tract.zip']
        rows.append(dict(tract_id=r.tract_id,county=r.county,point_lat=float(lat),point_lon=float(lon),point_source=point_source,point_source_url=point_url))
    points=pd.DataFrame(rows)
    geo=gpd.GeoDataFrame(points,geometry=gpd.points_from_xy(points.point_lon,points.point_lat),crs='EPSG:4326')
    joined=gpd.sjoin(geo,places[['GEOID','NAME','CLASSFP','geometry']],how='left',predicate='covered_by')
    # Exactly-on-boundary ties are deterministic and explicitly noted, not hidden.
    multiple=joined.groupby('tract_id').size().gt(1)
    joined=joined.sort_values(['tract_id','GEOID'],na_position='last').drop_duplicates('tract_id')
    output=[]
    for r in joined.itertuples():
        found=pd.notna(r.NAME)
        display=f'{r.NAME}, {r.county} County' if found else f'Unincorporated {r.county} County'
        method='point_in_census_place' if found else 'point_outside_census_places'
        if multiple.get(r.tract_id,False): method+=';boundary_tie_lowest_place_geoid'
        output.append(dict(tract_id=r.tract_id,display_name=display,method=method,
            source_url=URLS['tl_2024_12_place.zip'],source_vintage='TIGER/Line 2024 (January 1, 2024 boundaries)',
            place_geoid=str(r.GEOID) if found else '',place_type='CDP' if found and str(r.CLASSFP).startswith('U') else 'Incorporated place' if found else 'Outside incorporated places/CDPs',
            point_source=r.point_source,point_lat=r.point_lat,point_lon=r.point_lon,point_source_url=r.point_source_url))
    return pd.DataFrame(output).sort_values('tract_id').reset_index(drop=True)


def main():
    """Generate a small reproducible CSV; --verify compares bytes and source hashes."""
    import geopandas as gpd
    parser=argparse.ArgumentParser();parser.add_argument('--verify',action='store_true');args=parser.parse_args()
    sources=fetch_sources();bundle=load_community('fl')
    result=build_lookup(bundle.table,gpd.read_file(RAW/'tl_2024_12_place.zip'),gpd.read_file(RAW/'tl_2024_12_tract.zip'))
    data=result.to_csv(index=False,lineterminator='\n').encode()
    metadata=dict(scope='Central Florida: Lake, Orange, Osceola, Seminole',sources=sources,
        lookup_sha256=hashlib.sha256(data).hexdigest(),total=len(result),
        named=int(result.place_geoid.ne('').sum()),unincorporated=int(result.place_geoid.eq('').sum()),
        point_fallback=int(result.point_source.str.startswith('TIGER').sum()),
        method='Containment of supplied map point; fallback to official tract internal point. Not majority area. No nearest-place assignment.')
    if args.verify:
        assert OUT.read_bytes()==data,'Lookup differs: review source or script changes before rebuilding'
        assert json.loads(META.read_text())==metadata,'Provenance/source hash mismatch'
    else:
        OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_bytes(data);META.write_text(json.dumps(metadata,indent=2)+'\n')
    print(json.dumps(metadata,indent=2))


if __name__=='__main__':main()
