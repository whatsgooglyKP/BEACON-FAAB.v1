"""Kevin's follow-up: instant offline text, bounded optional AI, and readable views."""
import importlib.util
import threading
import time
from pathlib import Path
import pandas as pd
import pytest


def test_offline_default_never_constructs_a_model_client():
    from clean import run
    from report import evidence_report, make_report
    b,q=run('fl');calls=[]
    def forbidden():
        calls.append(True)
        raise AssertionError('Default must never request Gemini')
    start=time.monotonic()
    text,mode=make_report(b,q,client_factory=forbidden)
    assert text==evidence_report(b,q) and mode=='template'
    assert not calls and time.monotonic()-start<.1


def test_ai_deadline_api_is_available():
    import report
    assert getattr(report,'AI_TIMEOUT_SECONDS',None)==20
    assert hasattr(report,'start_generation'), 'UI needs nonblocking optional AI jobs'


def test_hung_model_is_bounded_and_late_result_cannot_replace_template():
    import report
    release=threading.Event()
    class Hung:
        class models:
            @staticmethod
            def generate_content(**kwargs):
                release.wait(25)
                return type('Answer',(),{'text':'{"paragraphs":["Built-in facts"]}'})()
    try:
        start=time.monotonic()
        job=report.start_generation('Built-in facts',client_factory=Hung,timeout_s=.1)
        assert time.monotonic()-start<.05
        text,mode=job.wait()
        assert text=='Built-in facts' and mode.startswith('template')
        assert time.monotonic()-start<.2
        release.set();time.sleep(.02)
        assert job.poll()==(text,mode), 'A late result must stay discarded'
    finally: release.set()


def test_actual_twenty_second_cap_even_if_client_ignores_transport_timeout():
    import report
    release=threading.Event()
    class Hung:
        class models:
            @staticmethod
            def generate_content(**kwargs):
                release.wait(25)
                raise TimeoutError()
    try:
        start=time.monotonic()
        text,mode=report.start_generation('Always available',client_factory=Hung).wait()
        elapsed=time.monotonic()-start
        assert elapsed<=20, f'Total AI latency exceeded 20 seconds: {elapsed}'
        assert text=='Always available' and mode.startswith('template')
    finally: release.set()


def test_readable_presentation_exists():
    assert importlib.util.find_spec('presentation') is not None


def test_friendly_table_rounds_only_the_view_and_hides_internal_columns():
    from presentation import friendly_table, field_label, status_label
    original=pd.DataFrame([dict(tract_id='01001020100',poverty_pct=7.84,
        low_access_population_pct_half10=82.246112,review_status='accepted_provisional',
        source_sha256='internal',proposal_id='internal',lat=28.5,homes_2020=55)])
    view=friendly_table(original)
    assert 'Neighborhood (census tract)' in view
    assert '% in poverty' in view and view.iloc[0]['% in poverty']==7.8
    assert view.iloc[0]['% of people far from a grocery store']==82.2
    assert view.iloc[0]['Review status']=='Accepted (one reviewer)'
    assert view.iloc[0]['Neighborhood (census tract)']=='01001020100'
    assert not {'source_sha256','proposal_id','lat'} & set(view.columns)
    assert original.iloc[0].poverty_pct==7.84
    assert 'homes' in field_label('homes_2020').lower()
    assert '_' not in status_label('rejected_provisional')


def test_dashboard_shows_builtin_summary_and_explicit_ai_buttons_without_network(monkeypatch,tmp_path):
    from streamlit.testing.v1 import AppTest
    import report
    calls=[]
    monkeypatch.setenv('BEACON_REVIEW_DB',str(tmp_path/'ui.db'))
    def forbidden(*args,**kwargs):
        calls.append(True)
        raise AssertionError('No automatic AI request')
    monkeypatch.setattr(report,'_generate',forbidden)
    a=AppTest.from_file(str(Path('app.py').resolve()),default_timeout=90).run()
    a.radio(key='step').set_value('3 · Use').run()
    assert not a.exception and not calls
    assert any(w.label=='Generate AI summary (optional, Gemini)' for w in a.button)
    assert any('490 neighborhoods' in w.value for w in a.markdown)
    frame=a.dataframe[0].value
    assert '% in poverty' in frame and 'tract_id' not in frame
    question=next(w for w in a.text_input if w.label=='Question')
    question.set_value('What information is missing?')
    next(w for w in a.button if w.label=='Ask').click().run()
    assert not calls and not a.exception
    assert any('transportation data is not available for Central Florida' in w.value for w in a.markdown)
    assert any(w.label=='Generate AI answer (optional, Gemini)' for w in a.button)


def test_sdk_gets_one_attempt_and_bounded_transport_timeout(monkeypatch):
    import report
    from google import genai
    seen=[]
    class Down:
        def __init__(self,**kwargs): seen.append(kwargs['http_options'])
        class models:
            @staticmethod
            def generate_content(**kwargs): raise RuntimeError('503 simulated')
        def close(self): pass
    monkeypatch.setenv('GEMINI_API_KEY','test-only-not-a-real-key')
    monkeypatch.setattr(genai,'Client',Down)
    assert report.start_generation('Offline facts').wait()[0]=='Offline facts'
    assert len(seen)==1 and 0<seen[0]['timeout']<=19000
    assert seen[0]['retry_options']=={'attempts':1}


def test_optional_ai_click_does_not_block_and_errors_keep_builtin(monkeypatch,tmp_path):
    from streamlit.testing.v1 import AppTest
    import report
    release=threading.Event();calls=[];jobs=[]
    original_start=report.start_generation
    def capture_job(*args,**kwargs):
        job=original_start(*args,**kwargs);jobs.append(job);return job
    monkeypatch.setattr(report,'start_generation',capture_job)
    def hung(base,client_factory,deadline):
        calls.append(True);release.wait(25)
        return base,'template (Gemini unavailable)'
    monkeypatch.setenv('BEACON_REVIEW_DB',str(tmp_path/'optional.db'))
    monkeypatch.setenv('GEMINI_API_KEY','test-only-not-a-real-key')
    monkeypatch.setattr(report,'_call_model',hung)
    a=AppTest.from_file(str(Path('app.py').resolve()),default_timeout=90).run()
    a.radio(key='step').set_value('3 · Use').run()
    assert not calls
    try:
        started=time.monotonic()
        next(w for w in a.button if w.label=='Generate AI summary (optional, Gemini)').click().run(timeout=10)
        assert time.monotonic()-started<5 and not a.exception and len(calls)==1
        assert any('490 neighborhoods' in w.value for w in a.markdown)
        assert any('background' in w.value for w in a.caption)
        release.set()
        # Synchronize only the test; the UI itself never awaits a model job.
        job=jobs[-1]
        job.wait()
        a.run()
        assert not a.exception
        assert any(report.AI_UNAVAILABLE_NOTE==w.value for w in a.info)
        assert any('490 neighborhoods' in w.value for w in a.markdown)
    finally: release.set()
