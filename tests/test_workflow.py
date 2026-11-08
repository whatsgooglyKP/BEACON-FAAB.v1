"""Workflow, export replay, and semantic report tests (no network required)."""
import importlib.util
import io
import json
import zipfile
import pandas as pd
import pytest


def test_export_and_new_report_interfaces_exist():
    import report
    assert hasattr(report,'evidence_report'), 'Report must explain the redesigned, not legacy pipeline'
    assert importlib.util.find_spec('exports') is not None


def test_edits_and_operational_choices_do_not_mutate_raw_or_model(tmp_path):
    from review_store import ReviewStore
    from need import rank, operational_view
    from test_evidence import fixture
    t=fixture().assign(review_complete=True)
    before=rank(t)
    s=ReviewStore(tmp_path/'r.db');s.register('r',pd.DataFrame(),{})
    gid=t.iloc[-1].tract_id
    s.add_note('r',gid,'Alice','Local knowledge: ask partner about program access.')
    s.recommend('r',gid,'Confirm need','Alice','Evidence checked')
    s.recommend('r',gid,'Challenge need','Bob','Needs local context')
    s.recommend('r',gid,'Reorder','Alice','Schedule review first',position=1)
    s.recommend('r',gid,'Replace action','Alice','Use practitioner check',replacement='Practitioner consultation')
    after=operational_view(before,s.recommendations('r'))
    assert after.score.equals(before.score) and after.model_rank.equals(before.model_rank)
    r=after[after.tract_id.eq(gid)].iloc[0]
    assert r.need_feedback=='Disputed' and r.review_tier=='Review required'
    assert r.replacement_action=='Practitioner consultation'
    assert len(s.notes('r'))==1


def test_bundle_replays_and_contains_no_private_inventory(tmp_path):
    from clean import run
    from review_store import ReviewStore
    from exports import export_bundle, replay_export
    b,q=run('fl');s=ReviewStore(tmp_path/'r.db')
    rid=b.manifest['run_id'];s.register(rid,q,b.manifest)
    p=q[q.rule_id.eq('R14')].iloc[0]
    s.decide(rid,p.proposal_id,'Accept','Reviewer','Understand the component years and 2020 base.')
    raw=export_bundle(b,q,s)
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        assert {'manifest.json','baseline.csv','reviewed.csv','decisions.json','unresolved.csv','observations.csv','shortlist.csv','notes.csv','field_dictionary.csv','health_report.md'} <= set(z.namelist())
        assert not any('inventory' in n or '.env' in n or 'secret' in n for n in z.namelist())
        view=pd.read_csv(z.open('reviewed.csv'),dtype={'tract_id':str},keep_default_na=False)
        assert len(view)==490
    replayed=replay_export(raw)
    expected=s.apply(rid,b.table)
    pd.testing.assert_frame_equal(replayed[expected.columns],expected,check_dtype=False,check_exact=True)


def test_template_and_model_fallback_are_semantically_gated():
    from clean import run
    from report import evidence_report, make_report, validate_generated, answer_question
    b,q=run('fl')
    base=evidence_report(b,q)
    assert '157' in base and '490' in base
    assert 'ACS 2020–24' in base and '2020 population base' in base
    assert 'transportation data is not available for Central Florida' in base
    assert 'qualify but not enrolled' not in base.lower()
    class Down:
        class models:
            @staticmethod
            def generate_content(**kwargs): raise RuntimeError('simulated 503')
    text,mode=make_report(b,q,client_factory=Down,use_gemini=True)
    assert text==base and mode.startswith('template')
    assert not validate_generated(base.replace('ACS 2020–24','ACS 2010–14'),base)
    assert not validate_generated(base+' People qualify but not enrolled.',base)
    assert not validate_generated(base.replace('157 neighborhoods','157 households'),base)
    response,_=answer_question('What information is missing?',b,q)
    assert 'transportation' in response.lower()


def test_app_initial_load_is_redesigned():
    from streamlit.testing.v1 import AppTest
    a=AppTest.from_file(str(__import__('pathlib').Path('app.py').resolve()),default_timeout=90).run()
    assert not a.exception
    assert any('Evidence Review' in t.value for t in a.title)
    assert any('Your top 10' in h.value for h in a.header)
    a.radio(key='step').set_value('1 · Load').run()
    assert not a.exception and any('Step 1' in h.value for h in a.header)



def test_irrelevant_operational_form_fields_do_not_create_false_disagreements(tmp_path):
    from review_store import ReviewStore
    from need import rank, operational_view
    from test_evidence import fixture
    t=rank(fixture().assign(review_complete=True));gid=t.iloc[-1].tract_id
    s=ReviewStore(tmp_path/'r.db')
    s.recommend('r',gid,'Approve','A','checked',replacement='unused',position=1)
    s.recommend('r',gid,'Approve','B','checked independently',replacement='ignored',position=5)
    row=operational_view(t,s.recommendations('r')).iloc[-1]
    assert row.action_status=='Approve'


def test_relevant_transport_uncertainty_and_unresolved_source_conflict_reduce_confidence(tmp_path):
    from review_store import ReviewStore
    from need import rank
    from test_evidence import fixture
    t=fixture();t['community_id']='synthetic_context_fixture';t['transport_lack_pct']=range(40)
    t['transport_ci_low']=1.;t['transport_ci_high']=50.
    assert rank(t.assign(review_complete=True)).iloc[-1].confidence=='Low'
    p=dict(proposal_id='p',tract_id=t.iloc[-1].tract_id,field='poverty_pct',before=39.,after=30.,rule_id='R15',kind='value_change',affects_ranking=True)
    s=ReviewStore(tmp_path/'r.db');s.register('r',pd.DataFrame([p]),{})
    baseline=t.copy();baseline['transport_lack_pct']=float('nan')
    assert rank(s.apply('r',baseline)).iloc[-1].confidence=='Low'


def test_actual_dashboard_map_is_centered_on_supplied_points(tmp_path,monkeypatch):
    from pathlib import Path
    from streamlit.testing.v1 import AppTest
    from clean import run
    from review_store import ReviewStore
    import json
    path=tmp_path/'map.db';monkeypatch.setenv('BEACON_REVIEW_DB',str(path))
    b,q=run('fl');rid=b.manifest['run_id'];s=ReviewStore(path);s.register(rid,q,b.manifest)
    p=q[q.rule_id.eq('R14')].iloc[0]
    s.decide(rid,p.proposal_id,'Accept','Map test reviewer','SIMULATED TEST: understand the 2020 base limitation.')
    a=AppTest.from_file(str(Path('app.py').resolve()),default_timeout=90).run()
    a.radio(key='step').set_value('3 · Use').run()
    assert not a.exception
    center=json.loads(a.get('plotly_chart')[0].proto.spec)['layout']['map']['center']
    assert 28<center.get('lat',0)<30 and -83<center.get('lon',0)<-80, 'Map must not default to the ocean at (0,0)'


def test_actual_form_rejects_a_stale_rendered_version(tmp_path,monkeypatch):
    from pathlib import Path
    from streamlit.testing.v1 import AppTest
    from clean import run
    from review_store import ReviewStore
    path=tmp_path/'stale-form.db';monkeypatch.setenv('BEACON_REVIEW_DB',str(path))
    b,q=run('fl');rid=b.manifest['run_id'];s=ReviewStore(path);s.register(rid,q,b.manifest)
    pid=q[q.rule_id.eq('R14')].iloc[0].proposal_id
    a=AppTest.from_file(str(Path('app.py').resolve()),default_timeout=90).run()
    a.radio(key='step').set_value('2 · Review').run()
    next(w for w in a.selectbox if w.label=='Queue view').select('All review records').run()
    next(w for w in a.selectbox if w.label=='Choose a review card').select(pid).run()
    # Another reviewer saves AFTER the card was rendered; don't rerender A's form.
    s.decide(rid,pid,'Accept','Other reviewer','SIMULATED TEST: concurrent acknowledgment',expected_version=0)
    a.text_input(key='reviewer').set_value('Stale reviewer')
    next(w for w in a.text_area if w.label=='Reason / context (required)').set_value('SIMULATED TEST: stale form must not save.')
    next(w for w in a.button if w.label=='Save decision').click().run()
    assert any('changed' in error.value for error in a.error), 'The UI must submit the rendered version, not fetch a newer version and pretend it was seen.'
    assert len(s.events(rid,pid))==1
