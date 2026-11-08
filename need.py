"""An explained within-community shortlist, NOT a shortage prediction.

Equal-weight poverty and continuous access-share midrank percentiles are the only
score inputs. Transportation is context, never a hidden Florida penalty. Human
operational order is a separate overlay and cannot rewrite measured need.
"""
import numpy as np
import pandas as pd

RESOURCES={
 'fl':('Second Harvest food finder','https://feedhopenow.org/find-help/food-finder/'),
 'nyc':('NYC Food Help','https://finder.nyc.gov/foodhelp/locations?mView=map'),
 'slc':('211 Utah','https://portal.forwardplatform.com/screener/211-utah/browse'),
}


def midranks(series):
    """Empirical midrank (average rank minus half) / n; equal values get equal scores."""
    n=int(series.notna().sum())
    return (series.rank(method='average')-.5)/n if n else series*float('nan')


def rank(table):
    """Keep every tract visible; only reviewed, valid evidence enters the usable list.

    Scores for unreviewed tracts are explicitly previews, never endorsed actions.
    The result preserves input order; model_rank provides a stable deterministic
    score-descending, tract-ID-ascending ordering, with missing scores unranked.
    """
    t=table.copy()
    for field in ('poverty_pct','low_access_population_pct_half10'):
        t[field]=pd.to_numeric(t.get(field,np.nan),errors='coerce')
        t.loc[~t[field].between(0,100),field]=np.nan
    if 'transport_lack_pct' in t:
        t['transport_lack_pct']=pd.to_numeric(t.transport_lack_pct,errors='coerce').where(t.transport_lack_pct.between(0,100))
    complete=t.poverty_pct.notna() & t.low_access_population_pct_half10.notna()
    n=int(complete.sum())
    t['poverty_percentile']=midranks(t.poverty_pct.where(complete))
    t['access_percentile']=midranks(t.low_access_population_pct_half10.where(complete))
    t['transport_percentile']=midranks(t.get('transport_lack_pct',pd.Series(np.nan,index=t.index)))
    t['score']=50*(t.poverty_percentile+t.access_percentile)
    t['cohort_size']=n; t['score_method']='50 × (poverty midrank percentile + access midrank percentile); within-community only'
    ordered=t.loc[complete].sort_values(['score','tract_id'],ascending=[False,True]).index
    t['model_rank']=np.nan; t.loc[ordered,'model_rank']=np.arange(1,len(ordered)+1)
    good_cohort=n>=20
    for f in ('poverty_pct','low_access_population_pct_half10'):
        values=t.loc[complete,f]
        if values.empty or values.quantile(.75)-values.quantile(.25)<=0 or values.quantile(.75)==values.quantile(.5): good_cohort=False
    p75=t.loc[complete,'poverty_pct'].quantile(.75)
    tr=t.get('transport_lack_pct',pd.Series(np.nan,index=t.index)); tr75=tr.quantile(.75)
    tr_ok=tr.notna().sum()>=20 and tr.quantile(.75)>tr.quantile(.25) and tr.quantile(.75)>tr.quantile(.5)
    t['gap_type']='No defined gap pattern'; t['confidence']='Medium'
    t['review_tier']='Review recommended'; t['resource_category']='Investigate local context'
    t['why']=''; t['limitations']='2020 population base; conditions may have changed. ACS 2020–24; June 2025 retailer snapshot. Evidence-quality label, not a prediction probability.'
    for i,r in t.iterrows():
        if not complete.loc[i]:
            t.at[i,'gap_type']='Insufficient data'; t.at[i,'confidence']='Insufficient evidence';t.at[i,'review_tier']='Review required'
            t.at[i,'why']='Poverty or continuous low-access share is missing/invalid. Not scored; missing does not mean zero.'
            continue
        gaps=[]
        if not good_cohort: gaps=['Insufficient differentiation']
        else:
            if r.poverty_pct>=p75 and r.get('lila_half10_driving')==1: gaps.append('Classic food access gap')
            if tr_ok and r.get('lila_half10_driving')==1 and pd.notna(r.get('transport_lack_pct')) and r.transport_lack_pct>=tr75:
                gaps.append('Transport-compounded')
            core=[r.poverty_percentile,r.access_percentile]
            if pd.notna(r.transport_percentile): core.append(r.transport_percentile)
            if not gaps and all(v<.75 for v in core) and sum(.5<=v<.75 for v in core)>=2: gaps.append('Possible blind spot')
        t.at[i,'gap_type']=' + '.join(gaps) if gaps else 'No defined gap pattern'
        if 'Classic food access gap' in gaps: t.at[i,'resource_category']='Food bank/pantry or listed mobile pantry programs'
        if 'Transport-compounded' in gaps: t.at[i,'resource_category']='Investigate mobile/delivery or transit-accessible programs'
        if any(g in gaps for g in ('Possible blind spot','Insufficient differentiation')):
            t.at[i,'resource_category']='No automatic recommendation'; t.at[i,'review_tier']='Review required'
        moe=r.get('poverty_moe90',np.nan)
        imprecise=pd.isna(moe) or (r.poverty_pct==0 and moe>0) or (r.poverty_pct!=0 and moe/1.645/abs(r.poverty_pct)>.30)
        if imprecise or r.get('has_dispute',False) or r.get('has_source_conflict',False): t.at[i,'confidence']='Low';t.at[i,'review_tier']='Review required'
        if 'Transport-compounded' in gaps:
            lo,hi=r.get('transport_ci_low',np.nan),r.get('transport_ci_high',np.nan)
            if pd.isna(lo) or pd.isna(hi) or not 0<=lo<=hi<=100 or hi-lo>20 or lo<=tr75<=hi:
                t.at[i,'confidence']='Low';t.at[i,'review_tier']='Review required'
        if r.get('group_quarters_pct',0)>=25 or r.get('population_2020',1000)<500 or r.get('poverty_universe',1000)<100:
            t.at[i,'confidence']='Low';t.at[i,'review_tier']='Review required'
        if pd.isna(r.get('lila_half10_driving',np.nan)):
            t.at[i,'review_tier']='Review required'
        if not r.get('review_complete',False): t.at[i,'review_tier']='Review required'
        t.at[i,'why']=(f'Poverty {r.poverty_pct:g}% of persons with poverty status determined (ACS 2020–24); '
            f'{r.low_access_population_pct_half10:.2f}% of the 2020 population beyond ½ mile urban / 10 miles rural by driving. '
            f'Within-community percentiles {r.poverty_percentile:.3f} and {r.access_percentile:.3f}; equal weights, cohort {n}. '
            f'LILA driving flag: {r.get("lila_half10_driving")}. '+('Poverty estimate is imprecise or uncertainty is unknown. ' if imprecise else '')+
            ('Not yet fully reviewed.' if not r.get('review_complete',False) else 'Reviewed evidence; limitations remain.'))
    if 'review_complete' not in t: t['review_complete']=False
    t['ready_to_use']=t.review_complete & complete & ~t.get('has_dispute',pd.Series(False,index=t.index))
    t['resource_name']=t.get('community_id',pd.Series('fl',index=t.index)).map(lambda x:RESOURCES.get(x,RESOURCES['fl'])[0])
    t['resource_url']=t.get('community_id',pd.Series('fl',index=t.index)).map(lambda x:RESOURCES.get(x,RESOURCES['fl'])[1])
    return t


def operational_view(ranked, events):
    """Show human decisions alongside, never instead of, algorithmic ranks.

    Conflicting named reviewers are shown as disputed. Within each control family,
    a reviewer's own later choice supersedes their earlier choice without deleting
    history. Operational reordering changes only a separate position column.
    """
    out=ranked.copy(); out['operational_position']=out.model_rank
    out['need_feedback']='Not reviewed';out['action_status']='Not approved';out['human_reason']='';out['replacement_action']=''
    groups={}
    for e in events:
        family='need' if e['action'] in ('Confirm need','Challenge need') else 'order' if e['action']=='Reorder' else 'action'
        groups.setdefault((e['tract_id'],family),{})[e['reviewer']]=e
    for (gid,family),votes in groups.items():
        mask=out.tract_id.eq(gid); last=list(votes.values())[-1]
        sigs={(e['action'],e.get('replacement',''),e.get('position')) for e in votes.values()}
        disputed=len(sigs)>1
        out.loc[mask,'human_reason']+=' | '.join(f"{e['reviewer']}: {e['action']} — {e['note']}" for e in votes.values())+' '
        if family=='need': out.loc[mask,'need_feedback']='Disputed' if disputed else last['action']
        elif family=='action':
            out.loc[mask,'action_status']='Disputed' if disputed else last['action']
            if not disputed and last['action']=='Replace action': out.loc[mask,'replacement_action']=last['replacement']
        elif not disputed: out.loc[mask,'operational_position']=last['position']
        if disputed or last['action']=='Challenge need': out.loc[mask,'review_tier']='Review required'
    return out
