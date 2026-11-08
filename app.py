"""Beacon Evidence Review: one clear Load → Review → Use workflow.

UI state selects a view; source data stays immutable. All writes go through the
versioned SQLite review store. Nothing is dispatched, deployed, or shared.
"""
import os
from pathlib import Path
import json
import hashlib
import pandas as pd
import streamlit as st
import plotly.express as px
from clean import run
from indicators import REGIONS, VERSION, SOURCE_URL
from review_store import ReviewStore, StaleVersion
from need import rank, operational_view
from exports import export_bundle
from shortlist import quick_checks, working_shortlist, shortlist_change
from report import evidence_report, answer_question, start_generation, AI_UNAVAILABLE_NOTE
from presentation import friendly_table, field_label, status_label, readable_text, short_reason, HEADERS

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


# ## Presentation is a copy: exports, scores, and raw evidence retain full precision.
def show_table(frame,columns=None):
    """One consistent friendly display policy for every table in the application."""
    view=friendly_table(frame,columns)
    formats={c:st.column_config.NumberColumn(format='%.1f') for c in view if pd.api.types.is_float_dtype(view[c])}
    st.dataframe(view,hide_index=True,width='stretch',column_config=formats)


@st.fragment(run_every=.5)
def optional_ai_text(base,panel_key,button_label='Generate AI summary (optional, Gemini)'):
    """Paint offline text first. Optional daemon work is polled, never awaited by UI."""
    st.markdown(base)
    digest=hashlib.sha256(base.encode()).hexdigest()[:16]
    key=f'ai-job-{panel_key}-{digest}'
    job=st.session_state.get(key)
    result=job.poll() if job is not None else None
    pending=job is not None and result is None
    if st.button(button_label,key='button-'+key,disabled=pending or not bool(os.getenv('GEMINI_API_KEY'))):
        job=start_generation(base)
        st.session_state[key]=job
        result=job.poll()
        pending=result is None
    if pending:
        st.caption('AI is optional and running in the background. You can keep using the built-in text. Maximum wait: 20 seconds.')
    elif result is not None:
        text,mode=result
        if mode=='gemini':
            with st.expander('Optional AI version',expanded=True): st.markdown(text)
        else: st.info(AI_UNAVAILABLE_NOTE)


st.title('Beacon · Evidence Review')
st.caption('A public-data prototype built for Beacon · DevFest Florida 2026 · Not an official DataKind product')
st.write('Start with ten places to look next. Check only what could change that starting list.')
if os.getenv('BEACON_DEMO_MODE')=='1':
    st.info('Demonstration workspace: real public source data with explicitly simulated reviewer decisions. This is not practitioner validation.')
with st.sidebar:
    st.subheader('Your workspace')
    region=st.selectbox('Community',list(REGIONS),format_func=lambda r:REGIONS[r]['name'],key='region')
    reviewer=st.text_input('Reviewer display name',key='reviewer',placeholder='Your name')
    st.caption('Prototype names are not verified accounts. Reviewers share this local workspace one at a time.')
    st.divider()
    st.markdown('**Public data only**')
    st.caption('No private uploads, inventory, dispatch, or shortage forecasts. All originals remain unchanged.')
    st.markdown('[Challenge brief](https://docs.google.com/document/d/1UFeoveMyn0UYYCc3oj4fVDRtXSA5nHvSzRTJfswc_Do/edit) · [Appendix B](https://docs.google.com/document/d/1L25DTxI31BlrH3QvB7k8H0rt6eowMiYA3YqHEwfJer0/edit)')
    st.caption(f'Rules/config: {VERSION} · Times shown in ET')

steps=['1 · Load','2 · Review','3 · Use']
home='Top 10 · Start here'
with st.expander('Advanced / full review'):
    st.radio('Workspace',[home]+steps,horizontal=True,key='step',label_visibility='collapsed')
    st.caption('All 18 checks, full source coverage, notes, disagreements, audit trail and exports remain here.')
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

# ## START WITH AN ANSWER: automatic cleaning is not team approval.
if st.session_state.step==home:
    st.header('Your top 10 places to look next')
    st.caption(f'Data cleaned automatically: {int(proposals.auto_applied.sum())} safe formatting fixes recorded; originals kept.')
    st.info('Automatically cleaned, not yet checked by your team. This is a starting list—not confirmed hunger, eligibility or a service recommendation.')
    st.caption('ACS 2020–24 · grocery distance: ½ mile urban / 10 miles rural, driving · 2020 population base and June 2025 stores. Conditions may have changed; confidence cannot exceed Medium.')
    if region=='fl': st.caption('Transportation data is not available for Central Florida. Missing does not mean zero.')
    current=working_shortlist(ranked)
    change_key='shortlist-change-'+rid
    if st.session_state.get(change_key): st.success(st.session_state[change_key])
    if ranked.need_feedback.eq('Disputed').any(): st.warning('Your team disagrees on a shortlist choice. Disputed candidates stay visible with Low confidence; see Advanced / full review.')
    show_table(current,['priority','tract_id','county','why_line','confidence'])
    mapped=current.dropna(subset=['lat','lon'])
    if not mapped.empty:
        fig=px.scatter_map(mapped,lat='lat',lon='lon',hover_name='tract_id',color='confidence',
            hover_data={'county':True,'why_line':True,'lat':False,'lon':False},labels=HEADERS,
            color_discrete_map={'Low':'#F79122','Medium':'#6B8FA8','High':'#388D58'},
            center={'lat':float(mapped.lat.mean()),'lon':float(mapped.lon.mean())},zoom=8 if region!='nyc' else 9,
            height=310,map_style='open-street-map')
        fig.update_layout(margin=dict(l=0,r=0,t=0,b=0));st.plotly_chart(fig,width='stretch')
    st.caption(f'{len(mapped)} of {len(current)} neighborhoods have supplied map points. Points are neighborhood references, not facilities or service areas.')
    # Keep a bounded, evidence-specific set: acknowledging one does not replace it
    # with another warning and create an endless queue. Numeric edits make a new set.
    snapshot=reviewed[['tract_id','poverty_pct','poverty_moe90','low_access_population_pct_half10']]
    fingerprint=hashlib.sha256(pd.util.hash_pandas_object(snapshot,index=False).values.tobytes()).hexdigest()[:16]
    cache_key='quick-snapshot-'+rid+'-'+fingerprint
    if cache_key not in st.session_state: st.session_state[cache_key]=quick_checks(snapshot)
    checks=st.session_state[cache_key]
    handled=set(ranked.loc[ranked.need_feedback.ne('Not reviewed'),'tract_id'])
    remaining=checks[~checks.tract_id.isin(handled)]
    st.subheader('Quick checks')
    st.write(f'{len(remaining)} quick checks could change this list.')
    st.caption('Only top-10 membership changes within the published poverty margin of error appear here. These are scenarios, not corrected measurements. Keep with caution, or challenge a candidate for follow-up.')
    if not remaining.empty:
        choice=st.selectbox('Choose a quick check',remaining.tract_id.tolist(),key='quick-'+rid)
        check=remaining[remaining.tract_id.eq(choice)].iloc[0]
        r=ranked[ranked.tract_id.eq(choice)].iloc[0]
        with st.container(border=True):
            st.markdown(f'**{choice} · {r.county}** · **Confidence: {r.confidence}**')
            st.write(check.reason)
            st.write(f'The poverty estimate is {r.poverty_pct:.1f}%; its published 90% margin-of-error range is {check.lower:.1f}%–{check.upper:.1f}%.')
            with st.form('quick-check-'+rid):
                decision=st.radio('What should your team do?',['Accept · keep with caution','Challenge · set aside for follow-up'],key='quick-decision-'+rid+'-'+choice)
                why=st.text_input('Quick-check reason (required)',key='quick-reason-'+rid+'-'+choice)
                save=st.form_submit_button('Save quick check',type='primary')
            # Preserve the tract actually shown before the submission rerun.
            # Another reviewer can remove it from the options in the meantime.
            seen_key='quick-rendered-target-'+rid
            if not save: st.session_state[seen_key]=choice
            if save:
                try:
                    if st.session_state.get(seen_key)!=choice:
                        raise StaleVersion('This check changed while you were reviewing it. No decision was saved. Reload quick checks and try again.')
                    op='Challenge need' if decision.startswith('Challenge') else 'Confirm need'
                    store.recommend(rid,choice,op,reviewer,why)
                    after=working_shortlist(operational_view(rank(reviewed),store.recommendations(rid)))
                    st.session_state[change_key]=shortlist_change(current,after)
                    st.rerun()
                except ValueError as exc: st.error(str(exc))
            if st.button('Reload quick checks'): st.rerun()
            st.caption('A team choice does not fix uncertainty or complete the full evidence review. Challenge withholds only this working-list candidate; every source record stays available.')
    else: st.caption('No remaining checks in this starting set. This does not mean all evidence is verified.')
    with st.expander('How these quick checks were selected'):
        st.write('At most eight of the current source-ranked top ten are selected. For each, poverty is varied alone across its published 90% margin of error, within 0–100%, and all community percentiles are recomputed. A card appears only if the top-ten membership changes, not merely its order. Other estimates, outside contenders, joint changes and missing uncertainty remain in full review. The list is not replenished after each answer.')
    st.button('Open advanced / full review',on_click=go,args=(steps[1],))
    st.button('Open reviewed-only dashboard and exports',on_click=go,args=(steps[2],))

# ## LOAD: show coverage before proposing any changes.
elif st.session_state.step==steps[0]:
    st.header('Step 1 · Load your community’s public evidence')
    st.write('One common field mapping, three communities. Nothing here is a live count of hunger or pantry stock.')
    c1,c2,c3=st.columns(3)
    c1.metric('Neighborhoods retained',f'{len(bundle.table):,}')
    c2.metric('Low income + low grocery access',f'{int(bundle.table.lila_half10_driving.eq(1).sum()):,}')
    c3.metric('Public source tables',len(bundle.manifest['sources']))
    st.info('**Definition:** Low income AND low access, ½ mile urban / 10 miles rural, driving distance. Straight-line and 1-mile definitions are sensitivity comparisons, not interchangeable fixes.')
    st.markdown('**Footprint:** '+', '.join(REGIONS[region]['counties'].values())+'. All valid tract IDs are retained, including unmatched source rows.')
    if region=='fl': st.warning('Coverage limitation — transportation data is not available for Central Florida. Supplied food-insecurity estimates are also absent. Missing does not mean zero.')
    else: st.info('Transportation describes modeled adults; its 95% intervals are separate from ACS margins of error. PLACES reference years are unverified; 2025 is its release year.')
    st.markdown('**Years, not just release dates:** ACS 2020–24; access uses 2020 population and June 2025 retailers. USDA initial release: July 2026. The 2020 base has not been updated recently; conditions may have changed.')
    with st.expander('See field-by-field coverage and measurement units',expanded=True):
        core=bundle.coverage[bundle.coverage.field.isin(['poverty_pct','snap_pct','low_access_population_half10','lila_half10_driving','transport_lack_pct'])]
        show_table(core,['field','usable','tract_rows','period','universe'])
    with st.expander('All source indicators and coverage details'):
        show_table(bundle.coverage)
    with st.expander('What is safe to clean automatically?'):
        st.write('Exact tract prefixes, label rows, encoding and documented missing codes. Numeric estimates are not guessed, capped or silently filled. Income bounds remain bounds. Mixed-year SNAP ratios are blocked, not “corrected.”')
        show_table(queue[queue.auto_applied],['rule_id','field','before','after'])
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
    st.caption('Formatting is standardized; uncertain evidence still needs your review. Acknowledging a limitation does not fix missing data.')
    with st.expander('Review counts and how they work'):
        analytical=queue.kind.isin(['value_change','exclude'])
        accepted=queue.review_status.isin(['accepted_provisional','accepted_agreed','resolved'])
        st.write(f'{int(queue.auto_applied.sum())} formatting records; {nonauto.tract_id[nonauto.tract_id.ne("")].nunique()} neighborhoods with cautions. These are not all data errors.')
        st.write(f'{int(analytical.sum())} proposed value changes; {int((analytical & accepted).sum())} accepted proposals; {int(queue.rule_id.eq("R12").sum())} regional coverage notices. Some formatting records cover a whole file.')
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
        selected=st.selectbox('Choose a review card',options,format_func=lambda p:f"{byid.loc[p,'rule_id']} · {byid.loc[p,'rule_name']} · {byid.loc[p,'tract_id'] or 'Regional notice'} · {field_label(byid.loc[p,'field'])}",key=f'card-{region}-{scope}-{tract_filter}')
        p=byid.loc[selected];state=states.get(selected,dict(status='pending',version=0,votes=[]))
        with st.container(border=True):
            st.subheader(p.rule_name+' · '+(p.tract_id or REGIONS[region]['name']))
            st.markdown(f'**Check confidence: {p.confidence}** · {p.severity} · **Review status: {status_label(state["status"])}**')
            st.write(short_reason(p))
            a,b=st.columns(2)
            a.markdown('**Original source / before**');a.code(str(p.before))
            b.markdown('**Proposed analytical action**')
            b.write(f'Select alternative observation: {p.after}' if p.kind=='value_change' else 'Exclude invalid analytical value; keep original.' if p.kind=='exclude' else 'Retain the valid observation; acknowledge, reject or add context. No guessed numeric replacement.')
            st.caption('No proposed value change affects the priority list until it is reviewed.')
            cells=bundle.observations[(bundle.observations.tract_id==p.tract_id)&(bundle.observations.indicator_id==p.field)]
            with st.expander('Source, years and full explanation',expanded=False):
                st.write(readable_text(p.reason))
                st.markdown(f'[Public source folder]({SOURCE_URL}) · `{p.source_id}` · column `{p.source_column}` · CSV row `{p.source_row}`')
                st.code('SHA-256: '+str(p.source_sha256))
                if not cells.empty:
                    show_table(cells,['source_id','value_raw','value_numeric','unit','universe','reference_start','reference_end','moe90','ci95_low','ci95_high','missing_reason'])
                else: st.write(bundle.manifest['definition_notes'])
            if state['status']=='disputed':
                st.error('Disagreement is visible. No contested patch is applied. A named resolver must choose with a reason; a new conflicting vote reopens the dispute.')
                show_table(pd.DataFrame(state['votes']),['reviewer','action','value','note','created_at'])
            choices=['Accept','Reject','Edit','Undo'] if p.kind in ('value_change','exclude') else ['Accept','Reject','Undo']
            with st.form('review-'+selected):
                action=st.selectbox('Decision',choices)
                note=st.text_area('Reason / context (required)',placeholder='Why is this action appropriate? What remains uncertain?')
                evidence=st.text_input('Public evidence link (required for a numeric Edit)',placeholder='https://… or source:'+str(p.source_id))
                value=st.number_input('Edited numeric value (used only for Edit)',value=float(p.after) if isinstance(p.after,(int,float)) and pd.notna(p.after) else 0.,disabled=p.kind not in ('value_change','exclude'))
                resolve=st.checkbox('Save as an explicit resolution',disabled=state['status']!='disputed')
                submitted=st.form_submit_button('Save decision',type='primary')
            # Remember the version the person actually saw. A form submission
            # reruns this script, so using freshly read state here would silently
            # bypass the stale-save guard. Only a non-submission render refreshes it.
            seen_key=f'rendered-version-{rid}-{selected}'
            if not submitted: st.session_state[seen_key]=state['version']
            if submitted:
                try:
                    fn=store.resolve if resolve else store.decide
                    fn(rid,selected,action,reviewer,note,value=value if action=='Edit' else None,evidence=evidence,expected_version=st.session_state.get(seen_key,state['version']))
                    st.rerun()
                except (ValueError,StaleVersion) as exc: st.error(str(exc))
            if st.button('Reload this review card'): st.rerun()
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
        if store.notes(rid): show_table(pd.DataFrame(store.notes(rid)))
    with st.expander('Full append-only audit log (ET)'):
        ev=store.events(rid)
        if ev: show_table(pd.DataFrame(ev),['reviewer','action','note','before','after','created_at'])
        else: st.caption('No decisions have been saved yet.')
    st.button('Open the explained dashboard →',type='primary',on_click=go,args=(steps[2],))

# ## USE: keep the dashboard, but separate evidence from operational decisions.
else:
    st.header('Step 3 · Use an explained priority list')
    st.write('Places to review for food-access support — not predicted shortages. Start with the ranked list, then inspect the map and the reason behind a tract.')
    c1,c2,c3=st.columns(3)
    c1.metric('Reviewed, scored neighborhoods',int(ranked.ready_to_use.sum()))
    c2.metric('Still needs review / information',int((~ranked.ready_to_use).sum()))
    c3.metric('Disputed data decisions',int(queue.review_status.eq('disputed').sum()))
    st.caption('Priority combines poverty and distance from grocery stores equally, within this community. Confidence describes the evidence—not the chance of hunger.')
    with st.expander('How the priority score works'):
        st.write('Score = 50 × (poverty midrank percentile + grocery-distance-share midrank percentile). Missing either input means unscored, never zero. Equal values share a percentile; the score is not a comparison between cities.')
    st.info('2020 population base remains a limitation, even after review; confidence cannot exceed Medium. Transportation is optional context, never a missing-data penalty for Florida.')
    preview=st.checkbox('Show unreviewed preview too (not an approved shortlist)',value=False)
    visible=ranked if preview else ranked[ranked.ready_to_use]
    visible=visible.sort_values(['model_rank','tract_id'],na_position='last')
    if visible.empty: st.warning('No fully reviewed neighborhoods yet. In Review, acknowledge the regional years notice and review a neighborhood’s relevant flags. You can inspect unreviewed previews without presenting them as approved.')
    cols=['model_rank','tract_id','county','score','poverty_pct','low_access_population_pct_half10','gap_type','confidence','review_status']
    show_table(visible,cols)
    with st.expander('Team decisions and operational priorities'):
        show_table(visible,['tract_id','operational_position','need_feedback','action_status','replacement_action','human_reason'])
    with st.expander('Map of the displayed neighborhoods',expanded=True):
        mapped=visible.dropna(subset=['lat','lon','score'])
        st.caption(f'{len(mapped)} of {len(visible)} displayed tracts have supplied PLACES point coordinates. These points are neighborhood references, not facilities or precise service areas. Unmapped tracts remain in the list.')
        if not mapped.empty:
            # Plotly's map center defaults to (0,0); center on supplied points
            # so the selected community, not an empty ocean, is in view.
            fig=px.scatter_map(mapped,lat='lat',lon='lon',color='score',hover_name='tract_id',hover_data={'county':True,'confidence':True,'gap_type':True,'score':':.1f'},labels=HEADERS,color_continuous_scale=['#6B8FA8','#F79122'],center={'lat':float(mapped.lat.mean()),'lon':float(mapped.lon.mean())},zoom=8 if region!='nyc' else 9,height=400,map_style='open-street-map')
            fig.update_layout(margin=dict(l=0,r=0,t=0,b=0));st.plotly_chart(fig,width='stretch')
    st.subheader('Why this neighborhood?')
    inspector=visible if not visible.empty else ranked
    if visible.empty: st.caption('Unreviewed evidence inspector only: these records are not in the usable shortlist.')
    picks=inspector.sort_values(['model_rank','tract_id'],na_position='last').tract_id.tolist()
    gid=st.selectbox('Inspect a neighborhood',picks,key=f'inspect-{region}')
    r=ranked[ranked.tract_id.eq(gid)].iloc[0]
    with st.container(border=True):
        st.markdown(f'**{gid} · {r.county}** · {r.gap_type} · **Confidence: {r.confidence}**')
        if pd.notna(r.poverty_pct) and pd.notna(r.low_access_population_pct_half10):
            st.write(f'{r.poverty_pct:.1f}% in poverty among people with reported poverty status (ACS 2020–24). {r.low_access_population_pct_half10:.1f}% of people are far from a grocery store, using the 2020 population base and June 2025 store locations.')
        else: st.write('A required measure is missing or invalid, so this neighborhood is not scored. Missing does not mean zero.')
        st.caption(r.limitations)
        with st.expander('Detailed reasoning and scoring inputs'): st.write(readable_text(r.why))
        st.markdown(f'**Suggested category:** {r.resource_category}. [{r.resource_name}]({r.resource_url}) — verify services and hours manually; no nearest-facility or capacity claim.')
        if r.evidence_cautions:
            with st.expander('Evidence cautions to keep in mind'): st.write(readable_text(r.evidence_cautions))
        position=str(int(r.operational_position)) if pd.notna(r.operational_position) else 'Not set'
        st.write(f'Team priority: {position} · {r.need_feedback} · {r.action_status}')
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
    st.subheader('Community summary')
    optional_ai_text(evidence_report(bundle,proposals,reviewed),'report-'+rid)
    with st.expander('Ask about this evidence (bounded chat prototype)'):
        st.caption('Built-in answers appear immediately. Gemini is optional, stays in the background, and has a 20-second total limit.')
        question=st.text_input('Question',placeholder='What information is missing? Why was this neighborhood flagged?')
        chat_key=f'chat-{rid}-{gid}'
        if st.button('Ask') and question.strip():
            text,_=answer_question(question,bundle,proposals,r,use_gemini=False)
            st.session_state[chat_key]=(question,text)
        if chat_key in st.session_state:
            asked,text=st.session_state[chat_key]
            st.caption('Your question: '+asked)
            optional_ai_text(text,chat_key,'Generate AI answer (optional, Gemini)')
    with st.expander('Download the evidence and complete audit trail'):
        st.markdown(evidence_report(bundle,proposals,reviewed))
        if st.button('Prepare replayable export bundle'):
            st.session_state[f'export-{rid}']=export_bundle(bundle,proposals,store)
        if f'export-{rid}' in st.session_state:
            st.download_button('Download evidence bundle (.zip)',st.session_state[f'export-{rid}'],file_name=f'beacon-{region}-{rid}.zip',mime='application/zip')
        st.download_button('Download current dashboard CSV',ranked.to_csv(index=False),file_name=f'beacon-{region}-dashboard.csv',mime='text/csv')
        st.caption('Local download only. Includes originals-as-observed, source hashes, decisions, unresolved issues, notes and recommendations. No raw source files, key, private uploads or stock-routing examples.')
    st.button('← Back to review',on_click=go,args=(steps[1],))
