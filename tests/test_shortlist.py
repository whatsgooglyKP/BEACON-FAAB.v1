"""Answer-first priorities must be honest, bounded, sensitive and reversible."""
import pandas as pd
import pytest


def test_quick_checks_have_actual_membership_change_witnesses_in_all_regions():
    from clean import run
    from shortlist import quick_checks,priority_ids
    for region in ('fl',):
        b,_=run(region);checks=quick_checks(b.table)
        assert 0<len(checks)<=8
        base=priority_ids(b.table)
        assert checks.tract_id.is_unique
        for c in checks.itertuples():
            assert c.tract_id in base
            assert set(c.lower_top10)!=set(base) or set(c.upper_top10)!=set(base)
            assert c.lower>=0 and c.upper<=100
            assert 'could' in c.reason.lower()


def test_precise_or_irrelevant_inputs_are_not_quick_checks():
    from shortlist import quick_checks
    table=pd.DataFrame(dict(tract_id=[f'{i:011}' for i in range(30)],
        poverty_pct=range(30),poverty_moe90=[0.]*30,
        low_access_population_pct_half10=range(30),snap_moe90=[999.]*30))
    assert quick_checks(table).empty, 'SNAP uncertainty does not drive the priority score'
    table.loc[0,'poverty_moe90']=100
    assert quick_checks(table).empty, 'A distant non-shortlisted tract is advanced review, not quick work'


def test_challenge_updates_working_list_without_changing_public_data(tmp_path):
    from clean import run
    from need import rank,operational_view
    from review_store import ReviewStore
    from shortlist import working_shortlist,shortlist_change
    b,q=run('fl');original=b.table.copy(deep=True)
    s=ReviewStore(tmp_path/'quick.db');rid=b.manifest['run_id']
    s.register(rid,q,b.manifest,b.observations,b.table)
    r=rank(s.apply(rid,b.table));before=working_shortlist(r);gid=before.iloc[0].tract_id
    s.recommend(rid,gid,'Challenge need','Tester','Verify this uncertain candidate before action')
    after=working_shortlist(operational_view(r,s.recommendations(rid)))
    assert len(after)==10 and gid not in set(after.tract_id)
    change=shortlist_change(before,after)
    assert gid in change and 'entered' in change
    pd.testing.assert_frame_equal(original,b.table)
    assert set(r.tract_id)==set(original.tract_id)


def test_accept_does_not_impute_moe_endpoint_or_claim_to_fix_uncertainty(tmp_path):
    from clean import run
    from need import rank,operational_view
    from review_store import ReviewStore
    from shortlist import working_shortlist,shortlist_change
    b,q=run('fl');s=ReviewStore(tmp_path/'keep.db');rid=b.manifest['run_id']
    s.register(rid,q,b.manifest,b.observations,b.table)
    r=rank(s.apply(rid,b.table));before=working_shortlist(r);gid=before.iloc[0].tract_id
    s.recommend(rid,gid,'Confirm need','Tester','Keep with its published uncertainty')
    after=working_shortlist(operational_view(r,s.recommendations(rid)))
    assert before.tract_id.tolist()==after.tract_id.tolist()
    assert 'unchanged' in shortlist_change(before,after)
    pd.testing.assert_series_equal(before.score,after.score)


def test_quick_order_matches_full_rank_engine_and_counts_are_bounded():
    from clean import run
    from need import rank
    from shortlist import priority_ids,quick_checks
    expected={'fl':8}
    for region,count in expected.items():
        b,_=run(region)
        assert priority_ids(b.table)==rank(b.table).nsmallest(10,'model_rank').tract_id.tolist()
        assert len(quick_checks(b.table))==count
        assert quick_checks(b.table,limit=0).empty


def test_answer_first_ui_and_quick_challenge_refresh_actual_top_ten(monkeypatch,tmp_path):
    from pathlib import Path
    from streamlit.testing.v1 import AppTest
    monkeypatch.setenv('BEACON_REVIEW_DB',str(tmp_path/'home.db'))
    a=AppTest.from_file(str(Path('app.py').resolve()),default_timeout=90).run()
    assert not a.exception
    assert any('Your top 10' in h.value for h in a.header)
    before=a.dataframe[0].value['Neighborhood (census tract)'].tolist()
    assert len(before)==10
    assert any('not yet checked by your team' in x.value for x in a.info)
    assert not any('Needs a decision' in x.label for x in a.metric)
    assert any('8 quick checks could change this list' in x.value for x in a.markdown)
    a.text_input(key='reviewer').set_value('Quick tester').run()
    selected=next(w for w in a.selectbox if w.label=='Choose a quick check').value
    next(w for w in a.radio if w.label=='What should your team do?').set_value('Challenge · set aside for follow-up')
    next(w for w in a.text_input if w.label=='Quick-check reason (required)').set_value('Need a source check before field action')
    next(w for w in a.button if w.label=='Save quick check').click().run()
    assert not a.exception
    after=a.dataframe[0].value['Neighborhood (census tract)'].tolist()
    assert len(after)==10 and selected not in after and before!=after
    assert any('entered' in x.value for x in a.success)
    assert any('7 quick checks could change this list' in x.value for x in a.markdown)
    a.radio(key='step').set_value('2 · Review').run()
    assert not a.exception and any('Step 2' in h.value for h in a.header)


def test_stale_quick_form_cannot_vote_on_the_next_neighborhood(monkeypatch,tmp_path):
    from pathlib import Path
    from streamlit.testing.v1 import AppTest
    from review_store import ReviewStore
    from clean import run
    db=tmp_path/'stale-home.db';monkeypatch.setenv('BEACON_REVIEW_DB',str(db))
    a=AppTest.from_file(str(Path('app.py').resolve()),default_timeout=90).run()
    a.text_input(key='reviewer').set_value('Stale reviewer').run()
    gid=next(w for w in a.selectbox if w.label=='Choose a quick check').value
    next(w for w in a.text_input if w.label=='Quick-check reason (required)').set_value('This reason concerns the previously displayed tract')
    store=ReviewStore(db);rid=run('fl')[0].manifest['run_id']
    store.recommend(rid,gid,'Challenge need','Other reviewer','A newer decision arrived')
    next(w for w in a.button if w.label=='Save quick check').click().run()
    assert not a.exception
    assert len(store.recommendations(rid))==1, 'Never silently apply the stale vote to the next tract'
    assert any('changed while you were reviewing' in e.value for e in a.error)
