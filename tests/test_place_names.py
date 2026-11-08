"""Readable geographic labels must be complete, sourced and analytically inert."""
from pathlib import Path
import pandas as pd
import pytest


def test_committed_place_lookup_covers_all_retained_tracts():
    from indicators import load_community
    path=Path('data/clean/tract_place_names.csv')
    assert path.exists(), 'A small sourced lookup must be committed'
    names=pd.read_csv(path,dtype={'tract_id':str},keep_default_na=False)
    assert names.tract_id.is_unique and len(names)==490
    assert names.display_name.str.strip().ne('').all()
    assert names.method.str.strip().ne('').all() and names.source_url.str.startswith('https://').all()
    assert names.source_vintage.str.strip().ne('').all()
    for region,n in [('fl',490)]:
        b=load_community(region)
        assert len(set(b.table.tract_id)&set(names.tract_id))==n


def test_names_are_display_only_and_exports_keep_the_lookup(tmp_path):
    import io,zipfile
    from clean import run
    from indicators import load_community
    from need import rank
    from review_store import ReviewStore
    from exports import export_bundle,replay_export
    b,q=run('fl');raw=load_community('fl')
    assert 'display_name' in b.table and b.table.display_name.str.strip().ne('').all()
    pd.testing.assert_series_equal(rank(b.table).score,rank(raw.table).score)
    store=ReviewStore(tmp_path/'names.db');store.register(b.manifest['run_id'],q,b.manifest,b.observations,b.table)
    blob=export_bundle(b,q,store)
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        assert 'tract_place_names.csv' in z.namelist()
        for name in ('baseline.csv','reviewed.csv','shortlist.csv','proposals.csv','unresolved.csv','observations.csv'):
            frame=pd.read_csv(z.open(name),dtype={'tract_id':str},keep_default_na=False)
            assert list(frame.columns)[:2]==['display_name','tract_id']
            assert frame.loc[frame.tract_id.ne(''),'display_name'].str.strip().ne('').all()
    pd.testing.assert_frame_equal(replay_export(blob),store.apply(b.manifest['run_id'],b.table),check_dtype=False,check_exact=True)


def test_place_name_is_the_primary_landing_label(monkeypatch,tmp_path):
    from streamlit.testing.v1 import AppTest
    monkeypatch.setenv('BEACON_REVIEW_DB',str(tmp_path/'labels.db'))
    app=AppTest.from_file(str(Path('app.py').resolve()),default_timeout=90).run()
    assert not app.exception
    assert not any(w.key=='region' for w in app.selectbox)
    view=app.dataframe[0].value
    assert 'Place name' in view and view['Place name'].str.strip().ne('').all()
    assert list(view.columns).index('Place name')<list(view.columns).index('Neighborhood (census tract)')
    assert any('a tract can span more than one area' in c.value for c in app.caption)
    quick=next(w for w in app.selectbox if w.label=='Choose a quick check')
    assert quick.value in set(view['Neighborhood (census tract)'])
    assert any('County' in option and 'tract' in option for option in quick.options)


def test_sample_names_match_independent_official_census_queries():
    import json
    names=pd.read_csv('data/clean/tract_place_names.csv',dtype=str,keep_default_na=False).set_index('tract_id')
    checks=json.loads(Path('data/clean/place_name_checks.json').read_text())['checks']
    expected={'12095013507':'Orlando, Orange County','12095016746':'Alafaya, Orange County',
        '12097041102':'Poinciana, Osceola County','12095012000':'Pine Hills, Orange County',
        '12095017023':'Unincorporated Orange County'}
    assert {c['tract_id'] for c in checks}==set(expected)
    for c in checks:
        row=names.loc[c['tract_id']]
        assert row.display_name==c['display_name']==expected[c['tract_id']]
        assert all(u.startswith('https://tigerweb.geo.census.gov/') for u in c['verification_urls'])
        if row.place_geoid:
            assert row.place_geoid in {a['GEOID'] for a in c['official_features']}
        else:
            assert not c['official_features'], 'Unincorporated means no incorporated-place or CDP hit, not a guess'


def test_florida_scope_is_the_only_exposed_adapter():
    from indicators import REGIONS
    assert set(REGIONS)=={'fl'}


def test_selected_tract_chat_reason_names_the_place_and_keeps_geoid():
    from clean import run
    from need import rank
    from report import answer_question
    b,q=run('fl');tract=rank(b.table).nsmallest(1,'model_rank').iloc[0]
    text,mode=answer_question('Why this tract?',b,q,tract,use_gemini=False)
    assert text.startswith(tract.display_name) and tract.tract_id in text
    assert mode=='template'
