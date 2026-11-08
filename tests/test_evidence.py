"""Independent acceptance fixtures for the approved evidence-review design."""
import importlib.util
import io
import zipfile
import json
import numpy as np
import pandas as pd
import pytest


def test_redesign_modules_exist():
    for name in ('indicators', 'quality_rules', 'review_store', 'need'):
        assert importlib.util.find_spec(name) is not None, f'Missing redesigned module: {name}'


def test_safe_parsing_does_not_guess_or_erase_codes():
    from indicators import normalize_id, parse_cell
    assert normalize_id('1400000US12095016510') == '12095016510'
    assert normalize_id('01001020100') == '01001020100'
    assert normalize_id('12095016510.0', {'12095016510'}) == '12095016510'
    assert normalize_id('12-095-016510') is None
    assert normalize_id('1.2095e10') is None
    assert normalize_id('1001020100') is None
    assert normalize_id('1001020100', {'01001020100'}) == '01001020100'
    assert parse_cell('-')['missing_reason'] == 'suppressed_or_unavailable_source_code'
    assert parse_cell('N')['value_numeric'] is None
    bound = parse_cell('250,000+')
    assert bound['bound'] == 'at_least' and bound['value_numeric'] is None
    assert bound['bound_value'] == 250000 and bound['value_raw'] == '250,000+'
    assert parse_cell('garbage')['missing_reason'] == 'parse_error'
    assert parse_cell('')['missing_reason'] == 'source_reason_unknown'


def fixture(n=40):
    # Percentiles intentionally have variation and a stable, independently known order.
    return pd.DataFrame(dict(tract_id=[f'12095{i:06}' for i in range(n)],
        community_id='fl', poverty_pct=np.arange(n, dtype=float),
        poverty_moe90=1., snap_pct=10., snap_moe90=2.,
        population_2020=1000., households_acs=400., poverty_universe=900.,
        group_quarters_pct=0., lila_half10_driving=1., lila_one10_driving=1.,
        lila_half10_straight=1., low_access_population_pct_half10=np.arange(n, dtype=float),
        transport_lack_pct=np.nan, transport_ci_low=np.nan, transport_ci_high=np.nan,
        usda_poverty_pct=np.arange(n, dtype=float), income_moe90=999999.,
        median_household_income=40000., income_bound='', lat=28.5, lon=-81.3))


def test_all_eighteen_rules_have_explicit_detectors():
    from quality_rules import RULES, detect
    t = fixture()
    t.loc[0, 'poverty_pct'] = 150
    t.loc[1, 'poverty_pct'] = 0; t.loc[1, 'poverty_moe90'] = 5
    t.loc[2, 'group_quarters_pct'] = 70
    t.loc[3, 'population_2020'] = 20
    t.loc[4, 'poverty_pct'] = np.nan
    t.loc[5, 'usda_poverty_pct'] = 40
    t.loc[6, 'lila_half10_straight'] = 0
    t.loc[7, 'transport_lack_pct'] = 30
    t.loc[7, 'transport_ci_low'] = 1; t.loc[7, 'transport_ci_high'] = 50
    t.loc[8, 'income_bound'] = 'at_least'
    t.loc[9, 'low_access_population_pct_half10'] = 120
    # R16 requires a nonzero IQR; an otherwise constant field cannot support it.
    t['median_household_income'] = 40000. + np.arange(len(t))*100
    t.loc[10, 'median_household_income'] = 1e9
    meta = {'import_events': [{'rule_id': 'R01', 'field': 'headers', 'tract_id': '', 'before': 'BOM', 'after': 'UTF-8'},
                              {'rule_id': 'R02', 'field': 'tract_id', 'tract_id': t.loc[0,'tract_id'], 'before':'1400000US'+t.loc[0,'tract_id'], 'after':t.loc[0,'tract_id']},
                              {'rule_id': 'R03', 'field': 'tract_id', 'tract_id':'', 'before':'duplicate', 'after':'quarantined'},
                              {'rule_id': 'R04', 'field': 'snap_pct', 'tract_id': t.loc[0,'tract_id'], 'before':'-', 'after':None}],
            'missing_usda_ids': [t.loc[39,'tract_id']]}
    q = detect(t, meta)
    assert set(RULES) == {f'R{i:02}' for i in range(1,19)}
    assert set(q.rule_id) == set(RULES)
    assert (q[q.rule_id.eq('R12')].tract_id == '').all()  # coverage once, never hundreds of fake fixes
    assert q[q.rule_id.eq('R08')].reason.str.contains('imprecise|uncertainty').all()
    assert not q.reason.str.contains('dorm|prison', case=False).any()
    assert not q[q.rule_id.isin(['R06','R08','R10','R16'])].auto_applied.any()


def test_ranking_is_midrank_review_gated_not_a_prediction():
    from need import rank
    t = fixture(); t['review_complete'] = True; t['review_status'] = 'accepted_provisional'
    t.loc[0, 'poverty_pct'] = np.nan
    out = rank(t)
    assert pd.isna(out.set_index('tract_id').loc[t.loc[0,'tract_id'],'score'])
    top = out.sort_values('model_rank').iloc[0]
    assert top.tract_id == t.iloc[-1].tract_id
    assert top.score == pytest.approx(100 * (38.5 / 39))
    assert top.confidence == 'Medium'  # population base still 2020, even after acknowledgment
    assert top.gap_type == 'Classic food access gap'
    assert out.transport_lack_pct.isna().all()
    assert not out.gap_type.str.contains('Transport').any()
    t.loc[39, 'review_complete'] = False
    assert rank(t).set_index('tract_id').loc[t.loc[39,'tract_id'],'review_tier'] == 'Review required'
    assert not rank(t).set_index('tract_id').loc[t.loc[39,'tract_id'],'ready_to_use']
    assert rank(fixture(8).assign(review_complete=True)).gap_type.eq('Insufficient differentiation').all()
    same = fixture(); same['poverty_pct'] = 5
    assert rank(same).gap_type.eq('Insufficient differentiation').all()


def test_transport_and_blind_spot_are_explained():
    from need import rank
    t=fixture(); t['community_id']='nyc'; t['transport_lack_pct']=np.arange(40,dtype=float)
    out=rank(t.assign(review_complete=True))
    assert 'Transport-compounded' in out.iloc[-1].gap_type
    assert out.iloc[24].gap_type == 'Possible blind spot'
    assert out.iloc[24].resource_category == 'No automatic recommendation'
    assert out.iloc[24].review_tier == 'Review required'


def test_store_requires_evidence_and_preserves_disputes(tmp_path):
    from review_store import ReviewStore, StaleVersion
    s=ReviewStore(tmp_path/'review.db')
    p=dict(proposal_id='p', tract_id='12095000100', field='poverty_pct', before=10., after=20., rule_id='R15', kind='value_change', reason='conflict', confidence='High')
    s.register('run', pd.DataFrame([p]), {'hash':'abc'})
    with pytest.raises(ValueError): s.decide('run','p','Accept','','')
    with pytest.raises(ValueError): s.decide('run','p','Edit','A','guess',value=30.)
    s.decide('run','p','Accept','Alice','checked source', expected_version=0)
    assert s.state('run','p')['status'] == 'accepted_provisional'
    with pytest.raises(StaleVersion): s.decide('run','p','Reject','Bob','late', expected_version=0)
    s.decide('run','p','Reject','Bob','different source', expected_version=1)
    assert s.state('run','p')['status']=='disputed'
    base=pd.DataFrame([dict(tract_id='12095000100',poverty_pct=10.)])
    assert s.apply('run',base).iloc[0].poverty_pct == 10
    s.resolve('run','p','Accept','Resolver','source verified', expected_version=2)
    assert s.apply('run',base).iloc[0].poverty_pct == 20
    s.decide('run','p','Reject','Bob','new contrary evidence',expected_version=3)
    assert s.state('run','p')['status']=='disputed'
    assert len(s.events('run'))==4
    reopened=ReviewStore(tmp_path/'review.db')
    assert reopened.state('run','p')['status']=='disputed'
    assert len(reopened.events('run'))==4
    assert s.replay('run', base).equals(s.apply('run', base))


def test_review_order_and_undo(tmp_path):
    from review_store import ReviewStore
    for order in [('Accept','Reject'),('Reject','Accept')]:
        s=ReviewStore(tmp_path/f'{order[0]}.db')
        s.register('r',pd.DataFrame([dict(proposal_id='p',tract_id='x',field='poverty_pct',before=1,after=2,rule_id='R15',kind='value_change')]),{})
        for name, action in zip(['A','B'],order): s.decide('r','p',action,name,'reason')
        assert s.state('r','p')['status']=='disputed'
        s.decide('r','p','Undo','B','withdraw my vote')
        assert 'provisional' in s.state('r','p')['status']


def test_real_regions_and_counts():
    from indicators import load_community
    for region, n, flags in [('fl',490,157),('nyc',2327,37),('slc',268,48)]:
        b=load_community(region)
        assert len(b.table)==n and b.table.tract_id.nunique()==n
        assert b.table.lila_half10_driving.sum()==flags
        assert not b.observations.empty
        assert {'source_sha256','source_row','value_raw','missing_reason','universe','reference_end','definition_id'}.issubset(b.observations)
        assert b.observations.source_sha256.str.len().eq(64).all()
        assert b.manifest['run_id']
        if region=='fl':
            assert b.table.transport_lack_pct.isna().all()
            f=b.table[b.table.lila_half10_driving.eq(1)]
            cv=sum(((f[m]/1.645/f[e].abs()>.30)&f[e].gt(0)).sum() for e,m in [('poverty_pct','poverty_moe90'),('snap_pct','snap_moe90')])
            assert cv==129
        if region=='nyc':
            assert set(['36047990100','36081990100','36085990100']).issubset(set(b.table.tract_id))


def test_known_coverage_reasons_live_in_observations_not_only_ui():
    from indicators import load_community
    b=load_community('fl')
    obs=b.observations[b.observations.indicator_id.eq('transport_lack_pct')]
    assert obs.missing_reason.eq('not_available_for_region').all()
    ny=load_community('nyc').table
    r=ny[ny.tract_id.eq('36047990100')].iloc[0]
    assert r.lila_half10_driving_missing_reason=='source_row_absent'
    assert r.low_access_population_pct_half10_missing_reason=='source_row_absent'


def test_zero_base_ratio_is_blocked_and_invalid_domain_is_not_a_distribution_outlier():
    from quality_rules import detect
    t=fixture();t.loc[0,'population_2020']=0
    t.loc[1,'poverty_pct']=999
    q=detect(t)
    assert ((q.rule_id=='R07')&(q.tract_id==t.loc[0,'tract_id'])).any()
    assert not ((q.rule_id=='R16')&(q.tract_id==t.loc[1,'tract_id'])&(q.field=='poverty_pct')).any()


def test_resolution_only_reopens_for_a_new_conflicting_vote(tmp_path):
    from review_store import ReviewStore
    s=ReviewStore(tmp_path/'r.db')
    p=dict(proposal_id='p',tract_id='x',field='poverty_pct',before=1.,after=2.,kind='value_change')
    s.register('r',pd.DataFrame([p]),{})
    s.decide('r','p','Accept','A','source checked')
    s.decide('r','p','Reject','B','mapping concern')
    s.resolve('r','p','Accept','Resolver','selected existing source')
    s.decide('r','p','Accept','A','affirm the resolution')
    assert s.state('r','p')['status']=='resolved'
    s.decide('r','p','Reject','B','new conflicting information')
    assert s.state('r','p')['status']=='disputed'


def test_unrelated_national_source_ids_do_not_block_selected_community():
    from clean import run
    for region in ('fl','nyc','slc'):
        b,q=run(region)
        assert not b.manifest['quarantined'], 'Out-of-region national IDs must be scoped before quarantine'
        assert q[(q.rule_id=='R02')&(~q.auto_applied)].empty
