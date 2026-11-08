"""Beacon Evidence Review: one clear Load → Review → Use workflow.

UI state selects a view; source data stays immutable. All writes go through the
versioned SQLite review store. Nothing is dispatched, deployed, or shared.
"""
import os
from pathlib import Path
import json
import pandas as pd
import streamlit as st
import plotly.express as px
from clean import run
from indicators import REGIONS, VERSION, SOURCE_URL
from review_store import ReviewStore, StaleVersion
from need import rank, operational_view
from exports import export_bundle
from report import evidence_report, make_report, answer_question

st.set_page_config(page_title='Beacon · Evidence Review',page_icon='◉',layout='wide')
# Brand CSS is static local content, never source data or user-supplied HTML.
st.markdown('<style>'+Path('assets/beacon.css').read_text()+'</style>',unsafe_allow_html=True)

# ## Load once per community; a new source hash creates a new review run.
@st.cache_data(show_spinner='Reading public sources and checking their provenance…')
def load(region):
    """Cache immutable data only; decisions are always read freshly from SQLite."""
    return run(region)


def go(step):
    """Move to another workflow step without hiding the preserved review state."""
    st.session_state['step']=step


st.title('Beacon · Evidence Review')
st.caption('A public-data prototype built for Beacon · DevFest Florida 2026 · Not an official DataKind product')
st.write('Clean the format. Understand the evidence. Decide together where to look next.')
with st.sidebar:
    st.subheader('Your workspace')
    region=st.selectbox('Community',list(REGIONS),format_func=lambda r:REGIONS[r]['name'],key='region')
    reviewer=st.text_input('Reviewer display name',key='reviewer',placeholder='Your name')
    st.caption('Self-entered prototype identities, not authenticated accounts. Local SQLite supports sequential reviewers on this computer.')
    st.divider()
    st.markdown('**Public data only**')
    st.caption('No private uploads, inventory, dispatch, or shortage forecasts. All originals remain unchanged.')
    st.markdown('[Challenge brief](https://docs.google.com/document/d/1UFeoveMyn0UYYCc3oj4fVDRtXSA5nHvSzRTJfswc_Do/edit) · [Appendix B](https://docs.google.com/document/d/1L25DTxI31BlrH3QvB7k8H0rt6eowMiYA3YqHEwfJer0/edit)')
    st.caption(f'Rules/config: {VERSION} · Times shown in ET')

steps=['1 · Load','2 · Review','3 · Use']
st.radio('Load → Review → Use',steps,horizontal=True,key='step',label_visibility='collapsed')
bundle,proposals=load(region);rid=bundle.manifest['run_id']
store=ReviewStore(os.getenv('BEACON_REVIEW_DB','data/review/evidence.sqlite3'))
registered=f'registered-{store.path}-{rid}'
if registered not in st.session_state:
    store.register(rid,proposals,bundle.manifest,bundle.observations,bundle.table)
    st.session_state[registered]=True
reviewed=store.apply(rid,bundle.table)
ranked=operational_view(rank(reviewed),store.recommendations(rid))
states=store.states(rid)
queue=proposals.copy();queue['review_status']=queue.proposal_id.map(lambda p:states.get(p,{}).get('status','pending'))
nonauto=queue[~queue.auto_applied]

# ## LOAD: show coverage before proposing any changes.
if st.session_state.step==steps[0]:
    st.header('Step 1 · Load your community’s public evidence')
    st.write('One common field mapping, three communities. Nothing here is a live count of hunger or pantry stock.')
    c1,c2,c3=st.columns(3)
    c1.metric('Neighborhoods retained',f'{len(bundle.table):,}')
    c2.metric('Source LILA flags',f'{int(bundle.table.lila_half10_driving.eq(1).sum()):,}')
    c3.metric('Public source tables',len(bundle.manifest['sources']))
    st.info('**Definition:** Low income AND low access, ½ mile urban / 10 miles rural, driving distance. Straight-line and 1-mile definitions are sensitivity comparisons, not interchangeable fixes.')
    st.markdown('**Footprint:** '+', '.join(REGIONS[region]['counties'].values())+'. All valid tract IDs are retained, including unmatched source rows.')
    if region=='fl': st.warning('Coverage limitation — transportation data is not available for Central Florida. Supplied food-insecurity estimates are also absent. Missing does not mean zero.')
    else: st.info('Transportation describes modeled adults; its 95% intervals are separate from ACS margins of error. PLACES reference years are unverified; 2025 is its release year.')
    st.markdown('**Years, not just release dates:** ACS 2020–24; access uses 2020 population and June 2025 retailers. USDA initial release: July 2026. The 2020 base has not been updated recently; conditions may have changed.')
    with st.expander('See field-by-field coverage and measurement units',expanded=True):
        st.dataframe(bundle.coverage,hide_index=True,width='stretch')
    with st.expander('What is safe to clean automatically?'):
        st.write('Exact tract prefixes, label rows, encoding and documented missing codes. Numeric estimates are not guessed, capped or silently filled. Income bounds remain bounds. Mixed-year SNAP ratios are blocked, not “corrected.”')
        st.dataframe(queue[queue.auto_applied][['rule_id','field','before','after']],hide_index=True,width='stretch')
    with st.expander('Original-source manifest (hash-locked)'):
        st.json({k:v for k,v in bundle.manifest.items() if k!='import_events'})
    st.button('Start review →',type='primary',on_click=go,args=(steps[1],))

# ## REVIEW: every meaning-changing action requires a named, explained decision.
elif st.session_state.step==steps[1]:
    st.header('Step 2 · Review what needs judgment')
    pending=nonauto.review_status.eq('pending')
    c1,c2,c3=st.columns(3)
    c1.metric('Needs a decision',int(pending.sum()))
    c2.metric('Cautions to understand',len(nonauto))
    c3.metric('Ready to use',int(ranked.ready_to_use.sum()))
    st.caption(f'{int(queue.auto_applied.sum())} format/code standardizations recorded separately · {nonauto.tract_id[nonauto.tract_id.ne("")].nunique()} unique tracts with cautions · accepting a limitation does not resolve missing data.')
    filters=st.columns([1,2])
    scope=filters[0].selectbox('Queue view',['Needs a decision','Disagreements','All review records'])
    tract_filter=filters[1].selectbox('Filter neighborhood',['All neighborhoods','Regional notices']+bundle.table.tract_id.tolist(),key=f'filter-{region}')
    q=queue.copy()
    if scope=='Needs a decision': q=q[q.review_status.eq('pending') & ~q.auto_applied]
    elif scope=='Disagreements': q=q[q.review_status.eq('disputed')]
    if tract_filter=='Regional notices': q=q[q.tract_id.eq('')]
    elif tract_filter!='All neighborhoods': q=q[q.tract_id.eq(tract_filter)]
    q=q.assign(_order=q.rule_id.map({'R14':0,'R15':1,'R06':2,'R03':3,'R18':4}).fillna(10)).sort_values(['_order','tract_id','rule_id'])
    if q.empty: st.success('No records in this view. Other limitations and rejected decisions remain available under All review records.')
    else:
        options=q.proposal_id.tolist()
        byid=q.set_index('proposal_id')
        selected=st.selectbox('Choose a review card',options,format_func=lambda p:f"{byid.loc[p,'rule_id']} · {byid.loc[p,'rule_name']} · {byid.loc[p,'tract_id'] or 'Regional notice'} · {byid.loc[p,'field']}",key=f'card-{region}-{scope}-{tract_filter}')
        p=byid.loc[selected];state=states.get(selected,dict(status='pending',version=0,votes=[]))
        with st.container(border=True):
            st.subheader(p.rule_name+' · '+(p.tract_id or REGIONS[region]['name']))
            st.markdown(f'**Action confidence: {p.confidence}** · {p.severity} · **Review state: {state["status"]}**')
            st.write(p.reason)
            a,b=st.columns(2)
            a.markdown('**Original source / before**');a.code(str(p.before))
            b.markdown('**Proposed analytical action**')
            b.write(f'Select alternative observation: {p.after}' if p.kind=='value_change' else 'Exclude invalid analytical value; keep original.' if p.kind=='exclude' else 'Retain the valid observation; acknowledge, reject or add context. No guessed numeric replacement.')
            st.caption(p.impact+' The common score is never silently recomputed from a pending patch.')
            cells=bundle.observations[(bundle.observations.tract_id==p.tract_id)&(bundle.observations.indicator_id==p.field)]
            with st.expander('Source cell, year, universe and evidence trail',expanded=False):
                st.markdown(f'[Public source folder]({SOURCE_URL}) · `{p.source_id}` · column `{p.source_column}` · CSV row `{p.source_row}`')
                st.code('SHA-256: '+str(p.source_sha256))
                if not cells.empty:
                    st.dataframe(cells[['source_file','source_column','source_row','value_raw','value_numeric','unit','universe','reference_start','reference_end','moe90','ci95_low','ci95_high','missing_reason']],hide_index=True,width='stretch')
                else: st.write(bundle.manifest['definition_notes'])
            if state['status']=='disputed':
                st.error('Disagreement is visible. No contested patch is applied. A named resolver must choose with a reason; a new conflicting vote reopens the dispute.')
                st.dataframe(pd.DataFrame(state['votes'])[['reviewer','action','value','note','created_at']],hide_index=True,width='stretch')
            choices=['Accept','Reject','Edit','Undo'] if p.kind in ('value_change','exclude') else ['Accept','Reject','Undo']
            with st.form('review-'+selected):
                action=st.selectbox('Decision',choices)
                note=st.text_area('Reason / context (required)',placeholder='Why is this action appropriate? What remains uncertain?')
                evidence=st.text_input('Public evidence link (required for a numeric Edit)',placeholder='https://… or source:'+str(p.source_id))
                value=st.number_input('Edited numeric value (used only for Edit)',value=float(p.after) if isinstance(p.after,(int,float)) and pd.notna(p.after) else 0.,disabled=p.kind not in ('value_change','exclude'))
                resolve=st.checkbox('Save as an explicit resolution',disabled=state['status']!='disputed')
                submitted=st.form_submit_button('Save decision',type='primary')
            if submitted:
                try:
                    fn=store.resolve if resolve else store.decide
                    fn(rid,selected,action,reviewer,note,value=value if action=='Edit' else None,evidence=evidence,expected_version=state['version'])
                    st.rerun()
                except (ValueError,StaleVersion) as exc: st.error(str(exc))
            if p.kind not in ('value_change','exclude'): st.caption('Edit the interpretation with a tract note below; contextual knowledge must not rewrite official statistics.')
    with st.expander('Add a neighborhood note or flag'):
        with st.form('tract-note'):
            note_gid=st.selectbox('Neighborhood',bundle.table.tract_id.tolist())
            tract_note=st.text_area('Local context / question')
            note_link=st.text_input('Supporting public link (optional)')
            saved=st.form_submit_button('Save tract note')
        if saved:
            try: store.add_note(rid,note_gid,reviewer,tract_note,note_link);st.success('Note preserved. No official number changed.')
            except ValueError as exc: st.error(str(exc))
        if store.notes(rid): st.dataframe(pd.DataFrame(store.notes(rid)),hide_index=True,width='stretch')
    with st.expander('Full append-only audit log (ET)'):
        ev=store.events(rid)
        st.dataframe(pd.DataFrame(ev)[['proposal_id','reviewer','action','note','before','after','version','previous_event_id','created_at']] if ev else pd.DataFrame(),hide_index=True,width='stretch')
    st.button('Open the explained dashboard →',type='primary',on_click=go,args=(steps[2],))

# ## USE: keep the dashboard, but separate evidence from operational decisions.
else:
    st.header('Step 3 · Use an explained priority list')
    st.write('Places to review for food-access support — not predicted shortages. Start with the ranked list, then inspect the map and the reason behind a tract.')
    c1,c2,c3=st.columns(3)
    c1.metric('Reviewed, scored neighborhoods',int(ranked.ready_to_use.sum()))
    c2.metric('Still needs review / information',int((~ranked.ready_to_use).sum()))
    c3.metric('Disputed data decisions',int(queue.review_status.eq('disputed').sum()))
    st.caption('Score = 50 × (poverty midrank percentile + low-access-share midrank percentile). Equal weights; within this community only. Missing required input = unscored. Confidence is evidence quality, not a prediction probability.')
    st.info('2020 population base remains a limitation, even after review; confidence cannot exceed Medium. Transportation is optional context, never a missing-data penalty for Florida.')
    preview=st.checkbox('Show unreviewed preview too (not an approved shortlist)',value=False)
    visible=ranked if preview else ranked[ranked.ready_to_use]
    visible=visible.sort_values(['model_rank','tract_id'],na_position='last')
    if visible.empty: st.warning('No fully reviewed neighborhoods yet. In Review, acknowledge the regional years notice and review a neighborhood’s relevant flags. You can inspect unreviewed previews without presenting them as approved.')
    cols=['model_rank','tract_id','county','score','poverty_pct','low_access_population_pct_half10','gap_type','confidence','review_tier','review_status','operational_position','need_feedback','action_status']
    st.dataframe(visible[cols],hide_index=True,width='stretch',column_config={'score':st.column_config.NumberColumn('Model score',format='%.2f'),'model_rank':'Model rank','operational_position':'Human position'})
    with st.expander('Map of the displayed neighborhoods',expanded=True):
        mapped=visible.dropna(subset=['lat','lon','score'])
        st.caption(f'{len(mapped)} of {len(visible)} displayed tracts have supplied PLACES point coordinates. These points are neighborhood references, not facilities or precise service areas. Unmapped tracts remain in the list.')
        if not mapped.empty:
            fig=px.scatter_map(mapped,lat='lat',lon='lon',color='score',hover_name='tract_id',hover_data=['county','confidence','gap_type'],color_continuous_scale=['#6B8FA8','#F79122'],zoom=8 if region!='nyc' else 9,height=400,map_style='open-street-map')
            fig.update_layout(margin=dict(l=0,r=0,t=0,b=0));st.plotly_chart(fig,width='stretch')
    st.subheader('Why this neighborhood?')
    picks=ranked.sort_values(['model_rank','tract_id'],na_position='last').tract_id.tolist()
    gid=st.selectbox('Inspect a neighborhood',picks,key=f'inspect-{region}')
    r=ranked[ranked.tract_id.eq(gid)].iloc[0]
    with st.container(border=True):
        st.markdown(f'**{gid} · {r.county}** · {r.gap_type} · **Confidence: {r.confidence}**')
        st.write(r.why);st.caption(r.limitations)
        st.markdown(f'**Suggested category:** {r.resource_category}. [{r.resource_name}]({r.resource_url}) — verify services and hours manually; no nearest-facility or capacity claim.')
        if r.evidence_cautions: st.warning(r.evidence_cautions)
        st.write(f'Model rank: {r.model_rank} · Human operational position: {r.operational_position} · {r.need_feedback} · {r.action_status}')
        if r.human_reason: st.write(r.human_reason)
        if r.replacement_action: st.write('Human replacement action: '+r.replacement_action)
    with st.expander('Confirm/challenge need or change the recommended action'):
        with st.form('recommendation'):
            op=st.selectbox('Operational decision',['Confirm need','Challenge need','Approve','Reject','Replace action','Reorder'])
            reason=st.text_area('Operational reason (required)')
            replacement=st.text_input('Replacement action category')
            position=st.number_input('Human priority position (Reorder only)',min_value=1,value=1,step=1)
            save=st.form_submit_button('Save operational decision')
        if save:
            try:
                store.recommend(rid,gid,op,reviewer,reason,replacement,position);st.rerun()
            except ValueError as exc: st.error(str(exc))
        st.caption('Approvals do not make unreviewed evidence ready. Conflicting reviewer choices are shown as disputed, never silently overwritten. Reorder changes only the human position, not the score.')
    with st.expander('Ask about this evidence (bounded chat prototype)'):
        st.caption('Offline answers work immediately. Optional Gemini can only reorder validated sentences, never invent data. Timeout: 150 seconds; template fallback is always usable.')
        use_ai=st.checkbox('Try optional Gemini paragraph ordering',value=False,disabled=not bool(os.getenv('GEMINI_API_KEY')))
        question=st.text_input('Question',placeholder='What information is missing? Why was this tract flagged?')
        if st.button('Ask') and question.strip():
            with st.spinner('Preparing grounded answer…'):
                text,mode=answer_question(question,bundle,proposals,r,use_gemini=use_ai)
            st.markdown(text);st.caption('Answer mode: '+mode)
    with st.expander('Download the evidence and complete audit trail'):
        st.markdown(evidence_report(bundle,proposals,reviewed))
        if st.button('Prepare replayable export bundle'):
            st.session_state[f'export-{rid}']=export_bundle(bundle,proposals,store)
        if f'export-{rid}' in st.session_state:
            st.download_button('Download evidence bundle (.zip)',st.session_state[f'export-{rid}'],file_name=f'beacon-{region}-{rid}.zip',mime='application/zip')
        st.download_button('Download current dashboard CSV',ranked.to_csv(index=False),file_name=f'beacon-{region}-dashboard.csv',mime='text/csv')
        st.caption('Local download only. Includes originals-as-observed, source hashes, decisions, unresolved issues, notes and recommendations. No raw source files, key, private uploads or stock-routing examples.')
    st.button('← Back to review',on_click=go,args=(steps[1],))
