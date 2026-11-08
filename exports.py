"""Local, replayable evidence bundle. No upload, raw-data redistribution or secrets.

The bundle includes source hashes/coordinates, all decisions and unresolved issues,
so a reviewer can reproduce the analytical view without trusting a screenshot.
"""
import io
import json
import zipfile
import pandas as pd
from review_store import ReviewStore, _json
from need import rank, operational_view
from report import evidence_report


def export_bundle(bundle,proposals,store):
    """Package the immutable baseline and append-only overlay, not just a cleaned CSV."""
    rid=bundle.manifest['run_id'];reviewed=store.apply(rid,bundle.table)
    states=store.states(rid); queue=proposals.copy()
    queue['review_status']=queue.proposal_id.map(lambda p:states.get(p,{}).get('status','pending'))
    actions=operational_view(rank(reviewed),store.recommendations(rid))
    out=io.BytesIO()
    dictionary=bundle.observations[['indicator_id','unit','universe','reference_start','reference_end','estimate_kind','definition_id','source_id','denominator_field']].drop_duplicates()
    with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
        def csv(name,df): z.writestr(name,df.to_csv(index=False))
        csv('baseline.csv',bundle.table);csv('reviewed.csv',reviewed);csv('observations.csv',bundle.observations)
        z.writestr('baseline.schema.json',bundle.table.to_json(orient='table',index=False))
        csv('proposals.csv',queue);csv('unresolved.csv',queue[queue.review_status.isin(['pending','disputed'])])
        csv('coverage.csv',bundle.coverage);csv('field_dictionary.csv',dictionary)
        csv('shortlist.csv',actions);csv('notes.csv',pd.DataFrame(store.notes(rid),columns=['tract_id','reviewer','note','evidence','created_at']))
        csv('decisions.csv',pd.DataFrame(store.events(rid)));csv('recommendation_events.csv',pd.DataFrame(store.recommendations(rid)))
        z.writestr('decisions.json',_json(store.events(rid)));z.writestr('recommendation_events.json',_json(store.recommendations(rid)))
        z.writestr('manifest.json',_json(bundle.manifest));z.writestr('health_report.md',evidence_report(bundle,proposals,reviewed))
        z.writestr('REPLAY.md','Use exports.replay_export(zip_bytes) to reconstruct reviewed.csv. CSV tract IDs must be read as strings. Baseline raw columns, source observations and null reasons are preserved. Model rank is separate from operational position. Reviewer-cited edits are not independently verified by the prototype. No source bytes or secrets are bundled.')
    return out.getvalue()


def replay_export(blob):
    """Replay the full exported audit log without the SQLite database or source files."""
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        # Schema-bearing snapshot prevents CSV inference from converting raw '3529'
        # to 3529 or losing an empty string / source-coded missing value.
        baseline=pd.read_json(io.StringIO(z.read('baseline.schema.json').decode()),orient='table')
        proposals=pd.read_csv(z.open('proposals.csv'),keep_default_na=False).to_dict('records')
        # Prefer exact proposal payloads from events, while pending proposals retain
        # numeric before/after from CSV when relevant to value patches.
        for p in proposals:
            for f in ('before','after'):
                if p['kind'] in ('value_change','exclude'):
                    p[f]=None if p[f]=='' else float(p[f])
            for f in ('affects_ranking','auto_applied'):
                if isinstance(p[f],str): p[f]=p[f]=='True'
        events=json.loads(z.read('decisions.json'));groups={}
        for event in events: groups.setdefault(event['proposal_id'],[]).append(event)
        return ReviewStore._apply(baseline,proposals,{p:ReviewStore.fold(es) for p,es in groups.items()})
