"""Load → Check orchestration for the Beacon Evidence Review prototype.

Cleaning here means reversible formatting plus a queue, not hidden value changes.
The old cleaner and dashboard are preserved in archive/ and app_v0_dashboard.py.
"""
from indicators import load_community
from quality_rules import detect
from place_names import enrich_bundle, attach_names


def run(community_id='fl',base='data/beacon'):
    """Return immutable evidence and review proposals, with precise source links."""
    bundle=load_community(community_id,base)
    bundle=enrich_bundle(bundle)
    proposals=attach_names(detect(bundle.table,bundle.manifest),bundle.place_names)
    obs=bundle.observations
    lookup={(r.tract_id,r.indicator_id,r.source_id):r for r in obs.itertuples(index=False)}
    for idx,p in proposals.iterrows():
        field='low_access_population_half10' if p.field=='low_access_population_pct_half10' else p.field
        source='usda_driving' if 'access' in field or field.startswith('lila_') else p.source_id
        cell=lookup.get((p.tract_id,field,source))
        if cell is not None:
            for f in ('source_id','source_row','source_column','source_sha256'):
                proposals.at[idx,f]=getattr(cell,f)
    return bundle,proposals
