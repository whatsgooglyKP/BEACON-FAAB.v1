"""Immutable public-source adapters for the Central Florida Beacon prototype.

The wide table is an analytical *view*, not a replacement for the supplied files.
Every numeric view cell has a raw observation, source coordinate, and SHA-256.
No inferred fills, retailer joins, or mixed-year SNAP percentages are produced.
"""
from dataclasses import dataclass
from pathlib import Path
from functools import lru_cache
from datetime import datetime
from zoneinfo import ZoneInfo
import hashlib
import json
import re
import pandas as pd

VERSION = 'beacon-evidence-2.3'
DEFINITION = 'driving-LILA-half-mile-urban-10-mile-rural'
REGIONS = {
    'fl': {'name': 'Central Florida', 'counties': {'12069':'Lake','12095':'Orange','12097':'Osceola','12117':'Seminole'}},
}
SOURCE_URL = 'https://drive.google.com/drive/folders/1zuwSZjkK3gcvEzNFPJ8THFRw9ulCgA-p'
CODES = {'-', 'N', '(X)', '**', '***', '*****', 'null'}

# ## Common field dictionary
# All four Central Florida counties use these exact mappings. Period and universe are part of a
# measure's identity; adult, person, household, and housing-unit rates differ.
ACS = {
 'poverty': ('S1701', {'poverty_pct':'S1701_C03_001E','poverty_moe90':'S1701_C03_001M','poverty_universe':'S1701_C01_001E'}),
 'snap': ('S2201', {'households_acs':'S2201_C01_001E','snap_households_acs':'S2201_C03_001E','snap_pct':'S2201_C04_001E','snap_moe90':'S2201_C04_001M'}),
 'pop': ('S0101', {'population_acs':'S0101_C01_001E','population_moe90':'S0101_C01_001M'}),
 'income': ('S1901', {'median_household_income':'S1901_C01_012E','income_moe90':'S1901_C01_012M'}),
}
USDA = {
 'general': ('SRAM General Tract Characteristics Data.csv', {'population_2020':'POP2020','homes_2020':'OHU2020','group_quarters_pct':'PCTGQTRS','group_quarters_usda_flag':'GroupQuartersFlag','urban':'Urban','usda_poverty_pct':'PovertyRate','usda_snap_homes':'TractSNAP'}),
 'driving': ('SRAM Driving Distance Data.csv', {'lila_half10_driving':'DD_SRAM_LILATracts_halfAnd10','lila_one10_driving':'DD_SRAM_LILATracts_1And10','low_access_half10_driving':'DD_SRAM_LAhalfand10','low_access_population_half10':'DD_SRAM_LAPOP05_10','low_income_low_access_population_half10':'DD_SRAM_LALOWI05_10'}),
 'straight': ('SRAM Straight Line Distance Data.csv', {'lila_half10_straight':'SD_SRAM_LILATracts_halfAnd10'}),
}
PLACES = {'transport_lack_pct':'LACKTRPT_CrudePrev','food_insecurity_adult_pct':'FOODINSECU_CrudePrev'}


def normalize_id(value, universe=None):
    """Normalize only reversible, exact tract encodings; never guess damaged IDs.

    Padding and integer-looking decimal forms require a verified source universe.
    Scientific notation and arbitrary punctuation are deliberately quarantined.
    """
    s = str(value).strip()
    if s.startswith('1400000US'): s = s[9:]
    if re.fullmatch(r'\d{11}', s): return s
    if universe is not None:
        if re.fullmatch(r'\d{11}\.0', s) and s[:-2] in universe: return s[:-2]
        if re.fullmatch(r'\d{10}', s) and s.zfill(11) in universe: return s.zfill(11)
    return None


def parse_cell(value):
    """Keep raw source codes and income bounds, rather than turning them into zero."""
    s = '' if value is None or pd.isna(value) else str(value)
    out = dict(value_raw=s, value_numeric=None, missing_reason='', bound='', bound_value=None)
    v=s.strip()
    if not v: out['missing_reason']='source_reason_unknown'
    elif v in CODES: out['missing_reason']='suppressed_or_unavailable_source_code'
    elif re.fullmatch(r'\d[\d,]*(?:\.\d+)?[+-]', v):
        out.update(bound='at_least' if v[-1]=='+' else 'at_most', bound_value=float(v[:-1].replace(',','')), missing_reason='bounded_not_exact')
    else:
        try:
            n=float(v.replace(',',''))
            if not pd.notna(n) or n in (float('inf'),float('-inf')): raise ValueError()
            out['value_numeric']=n
        except ValueError: out['missing_reason']='parse_error'
    return out


def field_info(field, source):
    """Human-readable units and observation period; release year is not survey year."""
    if source.startswith('acs'):
        period=('2020','2024'); kind='ACS five-year survey'; release='2025'
    elif source=='places':
        period=('unverified','unverified'); kind='modeled adult prevalence'; release='2025'
    elif field in ('usda_poverty_pct','usda_snap_homes'):
        period=('2020','2024'); kind='ACS-derived (same upstream ACS)'; release='2026-07'
    else:
        period=('2020','2020'); kind='2020 population/spatial allocation' if 'access' in field else 'Census 2020'; release='2026-07'
    if field.startswith('lila') or field in ('urban','group_quarters_usda_flag','low_access_half10_driving'):
        unit='flag'; universe='2020 census tract'
        if field.startswith('lila') or field.startswith('low_access'): period=('2025','2025'); kind='retailer snapshot June 2025, population base 2020'
    elif 'pct' in field or 'moe90' in field and field in ('poverty_moe90','snap_moe90'):
        unit='percentage points' if 'moe' in field else 'percent'
        universe='adults' if source=='places' else ('households' if field.startswith('snap') else 'persons with poverty status determined' if 'poverty' in field else 'persons')
    elif 'income' in field: unit='USD'; universe='households'
    elif 'household' in field: unit='households'; universe='households'
    elif 'homes' in field: unit='housing units'; universe='occupied homes (housing units)'
    else: unit='persons'; universe='persons'
    if field=='poverty_universe': universe='persons with poverty status determined'
    return dict(unit=unit, universe=universe, reference_start=period[0], reference_end=period[1], estimate_kind=kind, release_date=release)


@dataclass
class EvidenceBundle:
    """Immutable baseline plus provenance, coverage, and deterministic import recipe."""
    table: pd.DataFrame
    observations: pd.DataFrame
    manifest: dict
    coverage: pd.DataFrame
    place_names: pd.DataFrame | None = None  # Display-only lookup snapshot, attached after source loading.


def sha256(path):
    """Hash raw bytes without modifying or copying the source."""
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
    return h.hexdigest()


@lru_cache(maxsize=4)
def load_community(community_id='fl', base='data/beacon'):
    """Load the union of valid IDs with one-to-one joins and cell-level provenance.

    Unexpected schema stops import. Conflicting duplicate keys are quarantined,
    not resolved by picking the first row. Exact duplicates keep one analytical
    instance while the original row references remain in the import manifest.
    """
    region=REGIONS[community_id]; base=Path(base)
    tables=[]; observations=[]; sources=[]; events=[]; coverage=[]; quarantine=[]

    def ingest(path, source, id_col, mapping, encoding='utf-8-sig', extra=()):
        """Read a documented schema; preserve CSV row coordinates before filtering."""
        allcols=list(pd.read_csv(path,nrows=0,encoding=encoding).columns)
        requested=[id_col,*mapping.values(),*extra]+(['State'] if source.startswith('usda_') else [])
        missing=set(requested)-set(allcols)
        if missing: raise ValueError(f'Unexpected schema in {path.name}: {sorted(missing)}')
        raw=pd.read_csv(path,dtype=str,keep_default_na=False,encoding=encoding,usecols=requested)
        raw['_source_row']=raw.index+2
        # Scope the national USDA file using its explicit state label *before*
        # assessing ID damage. Other states' leading-zero encodings must not
        # create a blocking quarantine in the selected community.
        if source.startswith('usda_'):
            raw=raw[raw.State.eq({'fl':'Florida','nyc':'New York','slc':'Utah'}[community_id])].copy()
        raw['tract_id']=raw[id_col].map(normalize_id)
        label=raw.tract_id.isna() & ~raw[id_col].str.contains(r'\d',regex=True)
        if label.any(): events.append(dict(rule_id='R01',tract_id='',field=source,before=f'{int(label.sum())} label row',after='excluded from analysis; raw preserved',affected_count=int(label.sum())))
        malformed=raw[raw.tract_id.isna() & ~label]
        if len(malformed):
            quarantine.extend(dict(source=source,source_row=int(r._source_row),raw_id=r[id_col],reason='invalid tract ID') for _,r in malformed.iterrows())
            events.append(dict(rule_id='R02',tract_id='',field=source,before=f'{len(malformed)} ambiguous IDs',after='quarantined',auto_applied=False))
        raw=raw[raw.tract_id.str[:5].isin(region['counties'])].copy()
        digest=sha256(path)
        sources.append(dict(source_id=source,source_file=str(path),source_sha256=digest,source_url=SOURCE_URL,rows_in_region=len(raw),encoding=encoding))
        fmt=raw[id_col].ne(raw.tract_id)
        if fmt.any(): events.append(dict(rule_id='R02',tract_id='',field=source,before='exact ACS 1400000US prefix',after='11-digit string; raw preserved',affected_count=int(fmt.sum())))
        # No many-to-many expansion: conflicting rows never enter analysis.
        dup=raw.tract_id.duplicated(keep=False)
        if dup.any():
            for gid, group in raw[dup].groupby('tract_id'):
                exact=len(group[list(mapping.values())].drop_duplicates())==1
                events.append(dict(rule_id='R03',tract_id=gid,field=source,before=group['_source_row'].tolist(),after='one exact instance' if exact else 'conflict quarantined',auto_applied=exact))
                if not exact:
                    quarantine.append(dict(source=source,tract_id=gid,source_rows=group['_source_row'].tolist(),reason='conflicting duplicate'))
                    raw=raw[raw.tract_id.ne(gid)]
            raw=raw.drop_duplicates('tract_id')
        out=raw[['tract_id']].copy().set_index('tract_id')
        if 'NAME' in raw: out['tract_name']=raw.set_index('tract_id').NAME
        for field,column in mapping.items():
            cells=[parse_cell(v) for v in raw[column]]
            if community_id=='fl' and source=='places':
                for cell in cells: cell['missing_reason']='not_available_for_region'
            out[field]=[c['value_numeric'] for c in cells]
            out[field]=pd.to_numeric(out[field],errors='coerce')
            out[field+'_raw']=[c['value_raw'] for c in cells]
            out[field+'_missing_reason']=[('not_available_for_region' if community_id=='fl' and source=='places' else c['missing_reason']) for c in cells]
            out[field+'_selected_source']=source
            if field=='median_household_income': out['income_bound']=[c['bound'] for c in cells]
            info=field_info(field,source)
            for (_,row), cell in zip(raw.iterrows(), cells):
                obs=dict(community_id=community_id,tract_id=row.tract_id,geography_vintage='2020',indicator_id=field,
                    source_id=source,source_file=str(path),source_member=path.name,source_column=column,source_row=int(row._source_row),
                    source_sha256=digest,definition_id=DEFINITION if 'half10' in field else field,denominator_field='population_2020' if 'access_population' in field else '',
                    moe90=None,ci95_low=None,ci95_high=None,quality_flags='',**info,**cell)
                if source.startswith('acs') and field in ('poverty_pct','snap_pct'):
                    mcol=mapping[field.replace('_pct','_moe90')]
                    obs['moe90']=parse_cell(row[mcol])['value_numeric']
                if source=='places':
                    ci_col=column.replace('CrudePrev','Crude95CI')
                    nums=re.findall(r'\d+(?:\.\d+)?',row[ci_col])
                    if len(nums)==2: obs.update(ci95_low=float(nums[0]),ci95_high=float(nums[1]))
                observations.append(obs)
                if cell['missing_reason']=='suppressed_or_unavailable_source_code':
                    events.append(dict(rule_id='R04',tract_id=row.tract_id,field=field,before=cell['value_raw'],after=None,source_id=source,source_row=int(row._source_row),source_column=column))
            coverage.append(dict(source=source,field=field,tract_rows=len(raw),usable=int(out[field].notna().sum()),missing_by_design=community_id=='fl' and source=='places',period=f"{info['reference_start']}–{info['reference_end']}",universe=info['universe']))
        if source=='places':
            for field,column in mapping.items():
                ci=raw[column.replace('CrudePrev','Crude95CI')].str.extract(r'\(\s*([\d.]+),\s*([\d.]+)\)')
                stem='transport' if field=='transport_lack_pct' else 'food_insecurity'
                out[stem+'_ci_low']=pd.to_numeric(ci[0],errors='coerce').values
                out[stem+'_ci_high']=pd.to_numeric(ci[1],errors='coerce').values
            coords=raw.Geolocation.str.extract(r'POINT \(([-\d.]+) ([-\d.]+)\)')
            out['lon']=pd.to_numeric(coords[0],errors='coerce').values
            out['lat']=pd.to_numeric(coords[1],errors='coerce').values
        tables.append(out)
        return set(out.index)

    for folder,(table,mapping) in ACS.items():
        ingest(base/folder/f'ACSST5Y2024.{table}-Data.csv',f'acs_{table}','GEO_ID',mapping,extra=['NAME'] if folder=='poverty' else [])
    usda_ids=set()
    for source,(filename,mapping) in USDA.items():
        ids=ingest(base/'fara2025'/filename,'usda_'+source,'CensusTract20',mapping,encoding='cp1252')
        if source=='general': usda_ids=ids
    ingest(base/'places.csv','places','TractFIPS',PLACES,extra=['LACKTRPT_Crude95CI','FOODINSECU_Crude95CI','Geolocation'])
    wide=pd.concat(tables,axis=1,join='outer').sort_index().reset_index()
    wide['community_id']=community_id; wide['county_fips']=wide.tract_id.str[:5]
    wide['county']=wide.county_fips.map(region['counties'])
    wide['tract_name']=wide.tract_name.fillna(wide.tract_id)
    # A valid zero numerator remains zero; a missing or nonpositive base is NOT zero.
    wide['low_access_population_pct_half10']=100*wide.low_access_population_half10/wide.population_2020.where(wide.population_2020.gt(0))
    wide['low_access_population_pct_half10_raw']=wide.low_access_population_pct_half10
    wide['access_selected_source']='derived:usda_driving/USDA_POP2020'
    fields=[field for _,mapping in ACS.values() for field in mapping]+[field for _,mapping in USDA.values() for field in mapping]
    for field in fields:
        wide[field+'_missing_reason']=wide[field+'_missing_reason'].fillna('source_row_absent')
    wide['low_access_population_pct_half10_missing_reason']=''
    missing=wide.low_access_population_pct_half10.isna()
    wide.loc[missing,'low_access_population_pct_half10_missing_reason']='source_row_absent'
    wide.loc[wide.population_2020.le(0),'low_access_population_pct_half10_missing_reason']='invalid_value'
    for field in PLACES:
        if community_id=='fl':
            wide[field]=float('nan'); wide[field+'_missing_reason']='not_available_for_region'
        else: wide[field+'_missing_reason']=wide[field+'_missing_reason'].fillna('source_row_absent')
    identity=dict(version=VERSION,definition=DEFINITION,community_id=community_id,source_hashes={s['source_id']:s['source_sha256'] for s in sources})
    run_id=hashlib.sha256(json.dumps(identity,sort_keys=True).encode()).hexdigest()[:20]
    manifest=dict(**identity,run_id=run_id,created_at=datetime.now(ZoneInfo('America/New_York')).isoformat(),region=region,
        sources=sources,import_events=events,quarantined=quarantine,missing_usda_ids=sorted(set(wide.tract_id)-usda_ids),
        definition_notes='USDA LILA AND low-income, driving ½ mile urban / 10 miles rural. Access: June 2025 stores, population allocation 2020. ACS 2020–24. PLACES reference years unverified.')
    return EvidenceBundle(wide,pd.DataFrame(observations),manifest,pd.DataFrame(coverage))
