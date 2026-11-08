"""Eighteen transparent checks: detection is separate from a person's decision.

High confidence means confidence in a check or proposed action, never a measured
probability of hunger. Statistical/context thresholds are prototype heuristics.
No rule silently caps a number, invents an institution type, or imputes a value.
"""
import hashlib
import json
import numpy as np
import pandas as pd
from indicators import VERSION

# ## The rule catalogue is also the UI's plain-English help and export dictionary.
RULES = {
 'R01': ('Format / encoding','High','This file has an extra label row or formatting mark. We can standardize its format without changing the measurements.'),
 'R02': ('Tract ID','High','These sources name the same neighborhood differently. Original IDs are preserved beside standardized IDs; damaged IDs are quarantined, not guessed.'),
 'R03': ('Duplicate / join cardinality','High','Two rows share an ID. Joining them as-is could count this neighborhood twice.'),
 'R04': ('Source codes','High','The source does not provide a usable number here. A blank does not mean zero.'),
 'R05': ('Bounded income','High','This income is a bound, not an exact dollar amount. The source text is preserved and excluded from exact arithmetic.'),
 'R06': ('Impossible domain','High','This value is outside the possible range. We will not guess the correct number or cap it.'),
 'R07': ('Denominator / universe','High','These numbers describe different populations or years, so dividing them could give a misleading percentage. We use the direct ACS SNAP percentage, never TractSNAP divided by 2020 homes.'),
 'R08': ('ACS imprecision','High','This estimate is imprecise. Its margin of error is large compared with the estimate; this does not prove the survey sample was small.'),
 'R09': ('Modeled uncertainty','Medium','This modeled estimate has a wide range of plausible values or crosses the regional threshold. The transportation conclusion needs review.'),
 'R10': ('Group settings','Medium','Many residents live in group settings. These household measures may not describe everyone here. The type of setting is not known.'),
 'R11': ('Small geography','Medium','This is a small neighborhood or reporting group. Percentages can change substantially with relatively few people. Population is not survey sample size.'),
 'R12': ('Coverage limitation','High','Transportation data is not available for Central Florida, nor is the supplied food-insecurity measure. We have not treated missing indicators as zero.'),
 'R13': ('Unexpected missingness','Medium','We expected this field or row but could not use it. Please check the source or import; no replacement has been fabricated.'),
 'R14': ('Years / freshness','High','These measures describe different years. The population base is from 2020 and has not been updated recently; conditions may have changed. ACS figures are 2020–24. PLACES reference years have not been verified.'),
 'R15': ('Comparable-source disagreement','High','Two comparable sources disagree by more than 5 percentage points. We kept both rather than choosing silently. USDA and direct ACS poverty share the same upstream source.'),
 'R16': ('Unusual distribution','Low','This value is unusual for this community. It may be correct; please check before changing it.'),
 'R17': ('Definition sensitivity','High','This neighborhood’s flag changes when we change the distance definition. That is a methodology choice, not a corrected data error.'),
 'R18': ('Geographic coverage','High','This source covers a different area or set of neighborhood boundaries. We have not dropped unmatched neighborhoods.'),
}
CORE_FIELDS={'poverty_pct','low_access_population_pct_half10','lila_half10_driving'}
PROPOSAL_COLUMNS=['proposal_id','tract_id','rule_id','rule_name','field','before','after','kind','confidence','reason','severity','auto_applied','affects_ranking','impact','rule_version','source_id','source_row','source_column','source_sha256']


def detect(table, manifest=None):
    """Generate stable proposals from validated source values, without applying patches.

    Regional coverage and mixed-year notices are single cards, not per-cell errors.
    A field's uncertainty only blocks conclusions that actually depend on it.
    """
    manifest=manifest or {}; rows=[]; t=table.copy()
    def add(rule, gid='', field='', before=None, after=None, kind='caution', auto=False, relevant=True, extra='', **source):
        name,confidence,reason=RULES[rule]
        raw=dict(tract_id=gid,rule_id=rule,field=field,before=before,after=after)
        pid=hashlib.sha256(json.dumps(raw,sort_keys=True,default=str).encode()).hexdigest()[:20]
        rows.append(dict(proposal_id=pid,**raw,rule_name=name,kind=kind,confidence=confidence,
            reason=reason+(' '+extra if extra else ''),severity='Blocking' if rule in ('R03','R06','R15','R18') else 'Caution',
            auto_applied=auto,affects_ranking=relevant,impact='May change the score or review tier; compare the validated baseline in Use.' if relevant else 'Context only; does not change the common two-input score.',
            rule_version=VERSION,source_id=source.get('source_id',''),source_row=source.get('source_row',''),source_column=source.get('source_column',''),source_sha256=source.get('source_sha256','')))
    for e in manifest.get('import_events',[]):
        r=e['rule_id']; auto=e.get('auto_applied',r in ('R01','R02','R04'))
        add(r,e.get('tract_id',''),e.get('field',''),e.get('before'),e.get('after'),kind='format' if r in ('R01','R02','R03') else 'source_code',auto=auto,
            relevant=not auto,**{k:e[k] for k in ('source_id','source_row','source_column') if k in e})
    add('R07',field='snap_pct',extra='Mixed-denominator derivation blocked; ready-made percentages retained.',relevant=False)
    add('R14',field='source_periods')
    is_fl='community_id' in t and t.community_id.eq('fl').all()
    if is_fl: add('R12',field='transport_lack_pct / food_insecurity_adult_pct',relevant=False,extra=f'Affects {len(t)} tracts; coverage limitation, not fixed cells.')
    q3=t.get('transport_lack_pct',pd.Series(dtype=float)).quantile(.75)
    for _,r in t.iterrows():
        gid=r.tract_id
        for f in ('poverty_pct','snap_pct','group_quarters_pct','low_access_population_pct_half10','transport_lack_pct','food_insecurity_adult_pct'):
            v=r.get(f)
            if pd.notna(v) and not 0<=v<=100: add('R06',gid,f,float(v),None,kind='exclude',relevant=f in CORE_FIELDS or f=='transport_lack_pct')
        for f in ('population_2020','households_acs','poverty_universe'):
            v=r.get(f)
            if pd.notna(v) and v<0: add('R06',gid,f,float(v),None,kind='exclude')
        for f in ('lila_half10_driving','lila_half10_straight','lila_one10_driving'):
            v=r.get(f)
            if pd.notna(v) and v not in (0,1): add('R06',gid,f,float(v),None,kind='exclude')
        if r.get('income_bound','') in ('at_least','at_most'): add('R05',gid,'median_household_income',r.get('median_household_income_raw','bounded'),relevant=False)
        for f,m in [('poverty_pct','poverty_moe90'),('snap_pct','snap_moe90'),('median_household_income','income_moe90')]:
            v,moe=r.get(f),r.get(m)
            if pd.notna(v) and (pd.isna(moe) or (v==0 and moe>0) or (v!=0 and moe/1.645/abs(v)>.30)):
                add('R08',gid,f,float(v),relevant=f=='poverty_pct',extra=f'Estimate {v:g}; 90% margin of error {moe}. CV>30% is our prototype review threshold; zero estimates or missing margins have unknown uncertainty.')
        lo,hi=r.get('transport_ci_low'),r.get('transport_ci_high')
        if pd.notna(lo) and pd.notna(hi):
            if not 0<=lo<=hi<=100: add('R06',gid,'transport_lack_pct',r.get('transport_lack_pct'),None,kind='exclude')
            elif hi-lo>20 or (pd.notna(q3) and lo<=q3<=hi): add('R09',gid,'transport_lack_pct',r.get('transport_lack_pct'),extra=f'Modeled 95% interval: {lo:g}–{hi:g}%. Not an ACS margin of error.')
        if pd.notna(r.get('group_quarters_pct')) and r.group_quarters_pct>=25:
            add('R10',gid,'group_quarters_pct',float(r.group_quarters_pct),extra='USDA official ≥67% flag.' if r.group_quarters_pct>=67 else '≥25% is a prototype caution, not the USDA ≥67% rule.')
        for f,lim in [('population_2020',500),('households_acs',100),('poverty_universe',100)]:
            v=r.get(f)
            if pd.notna(v) and 0<=v<lim: add('R11',gid,f,float(v),relevant=f!='households_acs',extra=f'Prototype threshold: {lim}; zero bases cannot produce a rate.')
        for f in ('poverty_pct','low_access_population_pct_half10','lila_half10_driving'):
            if pd.isna(r.get(f)): add('R13',gid,f,r.get(f+'_raw','absent'),extra=f'Field: {f}; reason: {r.get(f+"_missing_reason","source_row_absent")}.')
        if pd.notna(r.get('poverty_pct')) and pd.notna(r.get('usda_poverty_pct')) and abs(r.poverty_pct-r.usda_poverty_pct)>5:
            add('R15',gid,'poverty_pct',float(r.poverty_pct),float(r.usda_poverty_pct),kind='value_change',source_id='usda_general',source_column='PovertyRate')
        primary=r.get('lila_half10_driving')
        if pd.notna(primary) and any(pd.notna(r.get(f)) and r.get(f)!=primary for f in ('lila_one10_driving','lila_half10_straight')):
            add('R17',gid,'lila_half10_driving',float(primary),extra=f'Half/10 driving={primary:g}; 1/10 driving={r.get("lila_one10_driving")}; half/10 straight={r.get("lila_half10_straight")}. Default unchanged.')
    for f in ('poverty_pct','snap_pct','low_access_population_pct_half10','median_household_income'):
        if f not in t: continue
        valid=t[f].dropna()
        if len(valid)<20: continue
        a,b=valid.quantile([.25,.75]); spread=b-a
        if spread<=0: continue
        for _,r in t[t[f].lt(a-3*spread)|t[f].gt(b+3*spread)].iterrows():
            add('R16',r.tract_id,f,float(r[f]),relevant=f in CORE_FIELDS,extra='Prototype threshold: outside three interquartile ranges; no clipping.')
    for gid in manifest.get('missing_usda_ids',[]): add('R18',gid,'usda_geography','source row absent',extra='ACS-only tract retained in union, not dropped.')
    result=pd.DataFrame(rows,columns=PROPOSAL_COLUMNS).drop_duplicates('proposal_id')
    # Attach traceability to every tract-specific card, even when detection is derived.
    sources={s['source_id']:s for s in manifest.get('sources',[])}
    for idx,r in result.iterrows():
        sid=r.source_id or ('acs_S1701' if r.field.startswith('poverty') else 'acs_S2201' if r.field.startswith('snap') else 'places' if r.field.startswith('transport') else 'usda_general')
        result.at[idx,'source_id']=sid
        result.at[idx,'source_sha256']=sources.get(sid,{}).get('source_sha256','')
    return result
