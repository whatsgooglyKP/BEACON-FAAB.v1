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
    pd.testing.assert_frame_equal(replayed[expected.columns],expected,check_dtype=False,check_exact=False)


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
    text,mode=make_report(b,q,client_factory=Down)
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
    assert any('Step 1' in h.value for h in a.header)

