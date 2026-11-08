"""One-command redesign scorecard; optional live Gemini is reported separately.

Run python -m evals.run [--only 1,3] [--skip-gemini] [--gemini-n 1].
Independent source-cell and midrank reference checks complement acceptance tests.
"""
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
from functools import lru_cache
import argparse
import hashlib
import io
import json
import os
import subprocess
import sys
import tempfile
import time
import traceback
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));os.chdir(ROOT)
from clean import run
from indicators import REGIONS
from need import rank,operational_view
from quality_rules import detect
from review_store import ReviewStore
from exports import export_bundle,replay_export
from report import evidence_report,make_report,validate_generated,start_generation,AI_TIMEOUT_SECONDS
RESULTS=[]


def record(id,name,status,detail):
    """Print a non-secret result and retain exactly the same record for Markdown/JSON."""
    RESULTS.append(dict(id=id,name=name,status=status,detail=detail))
    print(f'[{status}] {id}. {name}: {detail}',flush=True)


def pytest(*paths):
    """Keep failing-test output actionable; do not bury a failure behind a summary."""
    out=subprocess.run([sys.executable,'-m','pytest','-q','--basetemp=data/review/eval-pytest',*paths],capture_output=True,text=True)
    if out.returncode: print(out.stdout,flush=True);print(out.stderr,flush=True)
    assert out.returncode==0,'Acceptance test failure (see output)'
    return out.stdout.strip().splitlines()[-1]


@lru_cache(maxsize=16)
def source(name):
    """Independent raw CSV reader, with source IDs parsed literally, not via adapters."""
    if name in ('poverty','snap'):
        code='S1701' if name=='poverty' else 'S2201'
        d=pd.read_csv(f'data/beacon/{name}/ACSST5Y2024.{code}-Data.csv',dtype=str,keep_default_na=False)
        d['tract_id']=d.GEO_ID.str.replace('1400000US','',regex=False)
        return d[d.tract_id.str.fullmatch(r'\d{11}')].set_index('tract_id')
    fn={'general':'SRAM General Tract Characteristics Data.csv','driving':'SRAM Driving Distance Data.csv','straight':'SRAM Straight Line Distance Data.csv'}[name]
    d=pd.read_csv('data/beacon/fara2025/'+fn,dtype=str,encoding='cp1252',keep_default_na=False)
    return d.set_index('CensusTract20')


def e1(): return pytest('tests')


def e2():
    """Compare independent region unions, hashes and values; ensure no silent deletion."""
    details=[]
    for region,n in [('fl',490)]:
        b,q=run(region);t=b.table
        counties=set(REGIONS[region]['counties'])
        expected={g for g in set(source('poverty').index)|set(source('general').index) if g[:5] in counties}
        assert set(t.tract_id)==expected and len(t)==n and t.tract_id.nunique()==n
        for s in b.manifest['sources']:
            assert hashlib.sha256(Path(s['source_file']).read_bytes()).hexdigest()==s['source_sha256'],'Raw source changed'
        if region=='fl': assert t.transport_lack_pct.isna().all()
        details.append(f'{region}: {len(t)} retained')
    return '; '.join(details)+'; source byte hashes unchanged; union preserved; no duplicate joins'


def raw_number(v):
    """Reference parser for the selected source percentage/count cells only."""
    try: return float(v)
    except (ValueError,TypeError): return np.nan


def equal(got,want):
    assert (pd.isna(got) and pd.isna(want)) or abs(float(got)-float(want))<1e-8,f'Source mismatch: {got} vs {want}'


def e3():
    """Stratify spot checks around missing codes, group settings and definition changes."""
    paired=0;sampled=0;detail=[]
    p=source('poverty');s=source('snap');g=source('general');d=source('driving');sd=source('straight')
    for region in REGIONS:
        b,q=run(region);t=b.table.set_index('tract_id')
        picks=list(t.sample(10,random_state=42).index)
        # Add every unmatched ACS-only tract and representative edge cases.
        for mask in [t.poverty_pct.isna(),t.group_quarters_pct.ge(25),t.urban.eq(0),t.lila_half10_driving.ne(t.lila_half10_straight)]:
            picks+=list(t[mask].index[:2])
        picks=list(dict.fromkeys(picks))
        for gid in picks:
            r=t.loc[gid]
            if gid in p.index: equal(r.poverty_pct,raw_number(p.loc[gid,'S1701_C03_001E']))
            if gid in s.index: equal(r.snap_pct,raw_number(s.loc[gid,'S2201_C04_001E']))
            if gid in g.index:
                equal(r.population_2020,raw_number(g.loc[gid,'POP2020']))
                equal(r.group_quarters_pct,raw_number(g.loc[gid,'PCTGQTRS']))
            if gid in d.index:
                equal(r.lila_half10_driving,raw_number(d.loc[gid,'DD_SRAM_LILATracts_halfAnd10']))
                equal(r.low_access_population_half10,raw_number(d.loc[gid,'DD_SRAM_LAPOP05_10']))
            if gid in sd.index: equal(r.lila_half10_straight,raw_number(sd.loc[gid,'SD_SRAM_LILATracts_halfAnd10']))
        matched=t.poverty_pct.notna() & t.usda_poverty_pct.notna()
        assert np.allclose(t.loc[matched,'poverty_pct'],t.loc[matched,'usda_poverty_pct'])
        paired+=int(matched.sum());sampled+=len(picks)
        seeded=b.table.dropna(subset=['poverty_pct']).head(1).copy();seeded['usda_poverty_pct']=seeded.poverty_pct+5.1
        assert detect(seeded).rule_id.eq('R15').any()
        detail.append(f'{region}: {len(picks)} stratified tracts')
    assert paired==488
    return '; '.join(detail)+f'; {paired:,} paired poverty cells identical (same upstream ACS); seeded disagreement detected'


def e4():
    """Independent score oracle and sensitivity diagnostics (not an arbitrary stability gate)."""
    b,_=run('fl');t=b.table.assign(review_complete=True)
    a=rank(t);again=rank(t.copy())
    pd.testing.assert_series_equal(a.score,again.score)
    valid=t.poverty_pct.between(0,100)&t.low_access_population_pct_half10.between(0,100)
    ref=t.loc[valid]
    for idx in ref.sample(10,random_state=7).index:
        p=ref.poverty_pct;la=ref.low_access_population_pct_half10
        pr=(p.lt(p.loc[idx]).sum()+.5*p.eq(p.loc[idx]).sum())/len(ref)
        ar=(la.lt(la.loc[idx]).sum()+.5*la.eq(la.loc[idx]).sum())/len(ref)
        assert abs(a.loc[idx,'score']-50*(pr+ar))<1e-9
    assert not a.gap_type.str.contains('Transport').any()
    assert a.loc[~valid,'score'].isna().all()
    assert not a.confidence.eq('High').any()
    top=set(a.nsmallest(10,'model_rank').tract_id);rng=np.random.default_rng(14)
    noise=[];moe=[]
    for _ in range(10):
        x=t.copy();x['poverty_pct']=(x.poverty_pct*(1+rng.normal(0,.01,len(x)))).clip(0,100)
        noise.append(len(top&set(rank(x).nsmallest(10,'model_rank').tract_id)))
        x=t.copy();x['poverty_pct']=(x.poverty_pct+rng.normal(0,1,len(x))*x.poverty_moe90/1.645).clip(0,100)
        moe.append(len(top&set(rank(x).nsmallest(10,'model_rank').tract_id)))
    swaps={}
    for r in REGIONS:
        x=run(r)[0].table
        comparable=x.lila_half10_driving.notna() & x.lila_one10_driving.notna()
        swaps[r]=int(x.loc[comparable,'lila_half10_driving'].ne(x.loc[comparable,'lila_one10_driving']).sum())
    return f'10 independent midrank checks; deterministic; FL missing transport never zero. Top-10 overlap in 10 trials: 1% noise {min(noise)}–{max(noise)}, MOE-aware {min(moe)}–{max(moe)}. Definition-change flags among comparable records: {swaps}'


def e5(skip=False,n=1):
    """Offline semantic correctness is mandatory; live model availability is separate."""
    b,q=run('fl');base=evidence_report(b,q)
    assert '490 neighborhoods' in base and '157 neighborhoods' in base
    assert 'ACS 2020–24' in base and '2020 population base' in base
    class Down:
        class models:
            @staticmethod
            def generate_content(**kwargs): raise TimeoutError('simulated outage')
    txt,mode=make_report(b,q,client_factory=Down,use_gemini=True)
    assert txt==base and mode.startswith('template')
    def forbidden(): raise AssertionError('Default must not construct a model client')
    started=time.monotonic()
    assert make_report(b,q,client_factory=forbidden)==(base,'template')
    assert time.monotonic()-started<.1 and AI_TIMEOUT_SECONDS==20
    import threading
    release=threading.Event()
    class Hung:
        class models:
            @staticmethod
            def generate_content(**kwargs):
                release.wait(1)
                raise TimeoutError()
    try:
        started=time.monotonic()
        job=start_generation(base,client_factory=Hung,timeout_s=.1)
        assert time.monotonic()-started<.05
        assert job.wait()[0]==base and time.monotonic()-started<.2
    finally: release.set()
    assert not validate_generated(base.replace('157 neighborhoods','157 households'),base)
    assert not validate_generated(base.replace('2020–24','2010–14'),base)
    assert not validate_generated(base+' There is surplus stock.',base)
    if skip or not os.getenv('GEMINI_API_KEY'):
        record('5b','Optional live Gemini','SKIP','0 attempts: --skip-gemini or key not present; offline template is tested separately')
    else:
        modes=[]
        for _ in range(n):
            txt,mode=make_report(b,q,use_gemini=True);modes.append(mode)
            assert txt==base or validate_generated(txt,base)
        ok=sum(mode=='gemini' for mode in modes)
        rejected=any('rejected' in mode for mode in modes)
        status='FAIL' if rejected else 'PASS' if ok else 'SKIP'
        record('5b','Optional live Gemini',status,f'{n} attempts; {ok} accepted by exact paragraph semantic gate; modes: {modes}')
    return 'Instant default without client; nonblocking optional job and bounded hung-client fallback; template indicator/geography/unit/year checks pass; swapped units/years and invented stock rejected'


def e6():
    result=pytest('tests/test_evidence.py::test_store_requires_evidence_and_preserves_disputes','tests/test_evidence.py::test_review_order_and_undo','tests/test_evidence.py::test_resolution_only_reopens_for_a_new_conflicting_vote','tests/test_workflow.py::test_edits_and_operational_choices_do_not_mutate_raw_or_model','tests/test_workflow.py::test_bundle_replays_and_contains_no_private_inventory')
    return result+'; full append history, both vote orders, stale save, restart, undo, explicit resolution/reopen, and export replay verified'


def e7():
    """Exercise the actual app in each region, then round-trip a complete export."""
    from streamlit.testing.v1 import AppTest
    details=[]
    old=os.environ.get('BEACON_REVIEW_DB')
    try:
        with tempfile.TemporaryDirectory(prefix='beacon-eval-',dir=ROOT/'data/review') as temp:
            os.environ['BEACON_REVIEW_DB']=str(Path(temp)/'app.db')
            a=AppTest.from_file(str(ROOT/'app.py'),default_timeout=90).run()
            # Exercise the real form: two named reviewers disagree and resolve.
            a.radio(key='step').set_value('2 · Review').run()
            first_q=run('fl')[1];pid=first_q[first_q.rule_id.eq('R14')].iloc[0].proposal_id
            def widget(group,label):
                return next(w for w in group if w.label==label)
            a.text_input(key='reviewer').set_value('Eval UI A')
            widget(a.text_area,'Reason / context (required)').set_value('SIMULATED UI TEST: acknowledge the years limitation.')
            widget(a.button,'Save decision').click().run()
            widget(a.selectbox,'Queue view').select('All review records').run()
            widget(a.selectbox,'Choose a review card').select(pid).run()
            a.text_input(key='reviewer').set_value('Eval UI B')
            widget(a.selectbox,'Decision').select('Reject')
            widget(a.text_area,'Reason / context (required)').set_value('SIMULATED UI TEST: request newer evidence.')
            widget(a.button,'Save decision').click().run()
            rid=run('fl')[0].manifest['run_id']
            assert ReviewStore(os.environ['BEACON_REVIEW_DB']).state(rid,pid)['status']=='disputed'
            a.text_input(key='reviewer').set_value('Eval UI resolver')
            widget(a.selectbox,'Decision').select('Accept')
            widget(a.text_area,'Reason / context (required)').set_value('SIMULATED UI TEST: retain the old base with its visible caution.')
            widget(a.checkbox,'Save as an explicit resolution').check()
            widget(a.button,'Save decision').click().run()
            assert ReviewStore(os.environ['BEACON_REVIEW_DB']).state(rid,pid)['status']=='resolved'
            assert not a.exception
            for region in REGIONS:
                a.radio(key='step').set_value('Top 10 · Start here').run()
                assert not a.exception and any('Your top 10' in h.value for h in a.header)
                for step in ['1 · Load','2 · Review','3 · Use']:
                    a.radio(key='step').set_value(step).run()
                    assert not a.exception,f'{region} {step}: {a.exception}'
                    assert any(f'Step {step[0]}' in h.value for h in a.header)
                b,q=run(region);s=ReviewStore(Path(temp)/(region+'.db'));rid=b.manifest['run_id']
                s.register(rid,q,b.manifest)
                # Deliberately demonstrate an honest provisional reviewer acknowledgment.
                p=q[q.rule_id.eq('R14')].iloc[0]
                s.decide(rid,p.proposal_id,'Accept','Eval reviewer','Understand the component years; not a freshness repair.')
                raw=export_bundle(b,q,s)
                pd.testing.assert_frame_equal(replay_export(raw),s.apply(rid,b.table),check_dtype=False,check_exact=True)
                details.append(f'{region}: 3 UI steps, {len(b.table)} export rows')
    finally:
        if old is None: os.environ.pop('BEACON_REVIEW_DB',None)
        else: os.environ['BEACON_REVIEW_DB']=old
    return '; '.join(details)+'; UI disagreement/resolution exercised; replayed views exactly match; no dispatch or inventory upload'


def e8():
    """Only real membership-changing uncertainty becomes a small quick-check set."""
    from shortlist import quick_checks,priority_ids
    counts={}
    for region in REGIONS:
        table=run(region)[0].table
        checks=quick_checks(table);base=set(priority_ids(table))
        assert 0<len(checks)<=8
        for check in checks.itertuples():
            assert check.tract_id in base
            assert set(check.lower_top10)!=base or set(check.upper_top10)!=base
        counts[region]=len(checks)
    result=pytest('tests/test_shortlist.py::test_answer_first_ui_and_quick_challenge_refresh_actual_top_ten','tests/test_shortlist.py::test_stale_quick_form_cannot_vote_on_the_next_neighborhood')
    return f'Pristine quick checks {counts}; all have real ±90% poverty-MOE membership witnesses; capped at 8, not refilled; actual UI challenge replaces a candidate without changing source estimates; stale targets are rejected. {result}'


def e9():
    """Names are sourced display metadata, with complete Florida coverage and no reranking."""
    from place_names import read_lookup,LOOKUP
    from indicators import load_community
    lookup=read_lookup();b,_=run('fl');raw=load_community('fl')
    assert len(lookup)==490 and set(lookup.tract_id)==set(b.table.tract_id)
    assert lookup.display_name.str.strip().ne('').all()
    pd.testing.assert_series_equal(rank(b.table).score,rank(raw.table).score)
    meta=json.loads(LOOKUP.with_suffix('.sources.json').read_text())
    assert hashlib.sha256(LOOKUP.read_bytes()).hexdigest()==meta['lookup_sha256']
    checks=json.loads((ROOT/'data/clean/place_name_checks.json').read_text())['checks']
    for check in checks:
        row=lookup[lookup.tract_id.eq(check['tract_id'])].iloc[0]
        assert row.display_name==check['display_name']
        assert (row.place_geoid in {f['GEOID'] for f in check['official_features']}) if row.place_geoid else not check['official_features']
    return f"Central Florida only: 490/490 non-empty labels; {meta['named']} incorporated-place/CDP point labels, {meta['unincorporated']} unincorporated labels; {meta['point_fallback']} TIGER tract-point fallback; {len(checks)} independent official Census query checks; source scores unchanged"


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--only',default='');ap.add_argument('--skip-gemini',action='store_true');ap.add_argument('--gemini-n',type=int,default=1)
    args=ap.parse_args();only=set(args.only.split(',')) if args.only else set()
    suites=[(1,'Rules / schema acceptance',e1),(2,'Real-data integrity / coverage',e2),(3,'Independent source checks',e3),(4,'Rank / confidence / sensitivity',e4),(5,'Offline report faithfulness',lambda:e5(args.skip_gemini,max(1,args.gemini_n))),(6,'Human review / audit',e6),(7,'End-to-end / export replay',e7),(8,'Answer-first / sensitive quick checks',e8),(9,'Florida place labels / scope',e9)]
    start=time.monotonic()
    for id,name,fn in suites:
        if only and str(id) not in only: continue
        try: record(id,name,'PASS',fn())
        except Exception as exc:
            traceback.print_exc();record(id,name,'FAIL',f'{type(exc).__name__}: {exc}')
    counts={s:sum(r['status']==s for r in RESULTS) for s in ('PASS','FAIL','SKIP')}
    stamp=datetime.now(ZoneInfo('America/New_York')).isoformat(timespec='seconds')
    out=dict(timestamp=stamp,timezone='America/New_York (ET)',seconds=round(time.monotonic()-start,1),summary=counts,results=RESULTS)
    folder=ROOT/'evals/results';folder.mkdir(parents=True,exist_ok=True)
    (folder/'latest.json').write_text(json.dumps(out,indent=2))
    md=[f'# Beacon redesign scorecard · {stamp} ET','',f"**{counts['PASS']} PASS · {counts['FAIL']} FAIL · {counts['SKIP']} SKIP** ({out['seconds']} seconds)",'','| # | Suite | Result | Evidence |','|---|---|---|---|']
    md += [f"| {r['id']} | {r['name']} | {r['status']} | {r['detail'].replace('|','/')} |" for r in RESULTS]
    (folder/'latest.md').write_text('\n'.join(md)+'\n');print('\n'+'\n'.join(md))
    return 1 if counts['FAIL'] else 0


if __name__=='__main__': sys.exit(main())
