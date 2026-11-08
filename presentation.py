"""Plain-language display views only: never rename, round or change source/export data."""
from datetime import datetime
from zoneinfo import ZoneInfo
import re
import pandas as pd

HEADERS={
 'display_name':'Place name','priority':'Order','why_line':'Why it is on this list','tract_id':'Neighborhood (census tract)','county':'County','score':'Priority score','model_rank':'Priority rank',
 'poverty_pct':'% in poverty','low_access_population_pct_half10':'% of people far from a grocery store',
 'snap_pct':'% of households receiving SNAP','transport_lack_pct':'% of adults lacking reliable transportation',
 'review_status':'Review status','confidence':'Evidence confidence','review_tier':'Review needed','gap_type':'Food-access pattern',
 'operational_position':'Team priority','need_feedback':'Team view of need','action_status':'Action decision',
 'replacement_action':'Team replacement action','human_reason':'Team reasons','resource_category':'Suggested type of support',
 'source':'Public source','source_id':'Public source','field':'Indicator','indicator_id':'Indicator',
 'tract_rows':'Neighborhoods in file','usable':'With a usable number','missing_by_design':'Known coverage gap',
 'period':'Years covered','universe':'Who or what is measured','unit':'Unit','rule_id':'Check',
 'before':'Original value','after':'Reviewed value','reviewer':'Reviewer','action':'Decision','note':'Reason / context',
 'value':'Chosen value','evidence':'Supporting link','created_at':'Saved (ET)',
 'source_column':'Original source column','source_row':'Row in source file',
 'value_raw':'Original source cell','value_numeric':'Numeric estimate','reference_start':'First year','reference_end':'Last year',
 'moe90':'Margin of error (90%)','ci95_low':'Lower estimate (95% range)','ci95_high':'Upper estimate (95% range)',
 'missing_reason':'Why a number is missing','homes_2020':'Occupied homes (2020)',
}
FIELDS={**HEADERS,'source_periods':'Data years','usda_geography':'Neighborhood boundaries',
 'lila_half10_driving':'Low income + low grocery access (driving)',
 'lila_half10_straight':'Low income + low grocery access (straight-line)',
 'lila_one10_driving':'Low income + low grocery access (1-mile comparison)',
 'low_access_population_half10':'People far from a grocery store',
 'low_income_low_access_population_half10':'Low-income people far from a grocery store',
 'population_2020':'Population (2020)','population_acs':'Population (ACS 2020–24)',
 'population_moe90':'Population margin of error','poverty_moe90':'Poverty margin of error',
 'snap_moe90':'SNAP margin of error','poverty_universe':'People with reported poverty status',
 'households_acs':'Households (ACS 2020–24)','snap_households_acs':'Households receiving SNAP',
 'median_household_income':'Median household income','income_moe90':'Income margin of error',
 'group_quarters_pct':'% of people in group settings','group_quarters_usda_flag':'USDA group-settings flag',
 'urban':'Urban / rural classification','usda_poverty_pct':'Poverty estimate in USDA source',
 'usda_snap_homes':'Homes receiving SNAP in USDA source','food_insecurity_adult_pct':'% of adults experiencing food insecurity',
 'low_access_half10_driving':'Low grocery access (distance only)',
}
SOURCES={'acs_S1701':'Census · poverty','acs_S2201':'Census · SNAP participation',
 'acs_S0101':'Census · population','acs_S1901':'Census · household income',
 'usda_general':'USDA · neighborhood facts','usda_driving':'USDA · driving access',
 'usda_straight':'USDA · straight-line access','places':'CDC PLACES · modeled adult estimates'}
STATUSES={'accepted_provisional':'Accepted (one reviewer)','accepted_agreed':'Accepted (reviewers agree)',
 'rejected_provisional':'Rejected (one reviewer)','rejected_agreed':'Rejected (reviewers agree)',
 'pending':'Not reviewed yet','disputed':'Reviewers disagree','resolved':'Disagreement resolved',
 'reviewed baseline':'Reviewed source data'}
MISSING={'':'Available','not_available_for_region':'Not available for this community',
 'outside_supplied_sample':'Outside the supplied area','suppressed_or_unavailable_source_code':'Withheld or unavailable at source',
 'source_row_absent':'Not in this source','parse_error':'Could not read the source value',
 'invalid_value':'Outside the possible range','unverified_definition':'Definition needs checking',
 'source_reason_unknown':'Source does not explain the blank','bounded_not_exact':'A bound, not an exact number',
 'not_applicable':'Does not apply'}


def field_label(value):
    """Give a readable indicator/source name without leaking internal identifiers."""
    s=str(value)
    if s in FIELDS: return FIELDS[s]
    if s in SOURCES: return SOURCES[s]
    if ' / ' in s: return ' / '.join(field_label(part) for part in s.split(' / '))
    return s.replace('_',' ').capitalize()


def status_label(value):
    """Keep provisional/agreed/disputed meanings visible in ordinary language."""
    return STATUSES.get(str(value),str(value).replace('_',' '))


def friendly_table(frame,columns=None):
    """Copy a safe subset, translate labels/statuses, and round display numbers only."""
    if 'tract_id' in frame and 'display_name' not in frame:
        from place_names import read_lookup
        frame=frame.copy()
        frame['display_name']=frame.tract_id.map(read_lookup().set_index('tract_id').display_name).fillna('Place label unavailable')
        frame.loc[frame.tract_id.fillna('').eq(''),'display_name']='Central Florida (regional notice)'
    columns=list(columns) if columns is not None else list(frame.columns)
    if 'tract_id' in columns and 'display_name' in frame:
        columns=[c for c in columns if c!='display_name'];columns.insert(columns.index('tract_id'),'display_name')
    columns=[c for c in columns if c in HEADERS and c in frame]
    out=frame[columns].copy()
    for c in out:
        if c in ('before','after','value_raw','value'):
            out[c]=out[c].map(lambda v:'' if v is None or (not isinstance(v,(list,dict)) and pd.isna(v)) else str(v))
        elif c in ('field','indicator_id'): out[c]=out[c].map(field_label)
        elif c in ('source','source_id'): out[c]=out[c].map(lambda v:SOURCES.get(str(v),field_label(v)))
        elif c=='review_status': out[c]=out[c].map(status_label)
        elif c=='missing_reason': out[c]=out[c].map(lambda v:MISSING.get(str(v),str(v).replace('_',' ')))
        elif c=='missing_by_design': out[c]=out[c].map({True:'Yes',False:'No'})
        elif c=='created_at':
            out[c]=out[c].map(lambda v:datetime.fromisoformat(str(v)).astimezone(ZoneInfo('America/New_York')).strftime('%b %d, %I:%M %p ET'))
        elif pd.api.types.is_numeric_dtype(out[c]):
            out[c]=out[c].round(1)
            if c in ('priority','model_rank','operational_position','tract_rows','usable','homes_2020','source_row','reference_start','reference_end'): out[c]=out[c].astype('Int64')
    return out.rename(columns=HEADERS)


def readable_text(text):
    """Translate known internal measure tokens and round displayed percentages only."""
    text=str(text)
    for key in sorted(FIELDS,key=len,reverse=True): text=re.sub(r'\b'+re.escape(key)+r'\b',FIELDS[key],text)
    text=text.replace('TractSNAP','USDA SNAP count').replace('OHU2020','2020 occupied homes')
    return re.sub(r'(?<![\w.])(\d+\.\d+)%',lambda m:f'{float(m[1]):.1f}%',text)


def short_reason(proposal):
    """One understandable reason first; full detection details remain expandable."""
    if proposal.rule_id=='R08': return 'This estimate is imprecise. Its margin of error is large compared with the estimate. Review conclusions that depend on it.'
    if proposal.rule_id=='R07': return 'We use the direct Census SNAP percentage, not a ratio of counts from different years or populations.' if proposal.field=='snap_pct' else readable_text(proposal.reason)
    if proposal.rule_id=='R14': return 'The population base is from 2020; conditions may have changed. Census estimates cover 2020–24. PLACES observation years are unverified.'
    return readable_text(proposal.reason)
