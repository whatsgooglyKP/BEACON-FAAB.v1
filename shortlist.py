"""A ten-neighborhood starting answer, not ten confirmed service needs.

Quick checks are actual one-at-a-time sensitivity witnesses, not every warning
renamed as urgent work. Published poverty margins of error define scenarios, not
replacement measurements or probabilities. Team challenges withhold candidates
from a working list; they never rewrite the public estimates or analytical ranks.
"""
import pandas as pd
from need import midranks

QUICK_CHECK_LIMIT=8
COLUMNS=['tract_id','lower','upper','lower_top10','upper_top10','reason']


def priority_ids(table,limit=10):
    """Independent vectorized score ordering, identical to need.rank's core method."""
    p=pd.to_numeric(table.poverty_pct,errors='coerce')
    a=pd.to_numeric(table.low_access_population_pct_half10,errors='coerce')
    valid=p.between(0,100)&a.between(0,100)
    score=50*(midranks(p.where(valid))+midranks(a.where(valid)))
    return table[['tract_id']].assign(score=score).dropna(subset=['score']).sort_values(
        ['score','tract_id'],ascending=[False,True]).head(limit).tract_id.tolist()


def quick_checks(table,limit=QUICK_CHECK_LIMIT):
    """At most eight current top-ten tracts whose membership changes at ±90% MOE.

    Test each tract alone, recomputing the full regional percentile cohort. Only
    changing membership, not merely order or a large unrelated SNAP margin, counts.
    The fixed snapshot selection is not refilled after a team decision. Other
    uncertainties, joint effects, access uncertainty and outside contenders remain
    in advanced review: this is a bounded starting set, not exhaustive clearance.
    """
    if limit<=0: return pd.DataFrame(columns=COLUMNS)
    base=priority_ids(table);found=[];byid=table.set_index('tract_id',drop=False)
    for gid in base:
        row=byid.loc[gid];moe=row.get('poverty_moe90')
        if pd.isna(moe) or moe<=0: continue
        low=max(0,float(row.poverty_pct)-float(moe))
        high=min(100,float(row.poverty_pct)+float(moe))
        scenarios=[]
        for value in (low,high):
            scenario=table.copy()
            scenario.loc[scenario.tract_id.eq(gid),'poverty_pct']=value
            scenarios.append(priority_ids(scenario))
        if any(set(ids)!=set(base) for ids in scenarios):
            found.append(dict(tract_id=gid,lower=low,upper=high,lower_top10=scenarios[0],upper_top10=scenarios[1],
                reason='Published poverty uncertainty could move this neighborhood out of the top 10.'))
        if len(found)>=min(QUICK_CHECK_LIMIT,max(0,limit)): break
    return pd.DataFrame(found,columns=COLUMNS)


def working_shortlist(ranked,limit=10):
    """Display top scored candidates except uncontested team challenges; retain all data."""
    frame=ranked.copy()
    if 'need_feedback' in frame:
        frame=frame[frame.need_feedback.ne('Challenge need')].copy()
        frame.loc[frame.need_feedback.eq('Disputed'),'confidence']='Low'
    result=frame.dropna(subset=['score']).sort_values(['model_rank','tract_id']).head(limit).copy()
    result['priority']=range(1,len(result)+1)
    result['why_line']=result.apply(lambda r:f'{r.poverty_pct:.1f}% in poverty; {r.low_access_population_pct_half10:.1f}% far from a grocery store.',axis=1)
    return result


def shortlist_change(before,after):
    """State actual membership changes; accepting a caution must not fabricate reranking."""
    old=before.tract_id.tolist();new=after.tract_id.tolist()
    removed=[g for g in old if g not in new];added=[g for g in new if g not in old]
    if not removed and not added:
        return 'Top 10 membership unchanged. Your team decision was saved; public estimates and uncertainty are unchanged.'
    def describe(gid,frame):
        if 'display_name' not in frame: return gid
        row=frame[frame.tract_id.eq(gid)].iloc[0]
        return f'{row.display_name} (tract {gid})'
    return ('Working top 10 updated: '+', '.join(describe(g,before) for g in removed)+' withheld after a team challenge; '+', '.join(describe(g,after) for g in added)+
        ' entered. Public estimates and original scores are unchanged.')
