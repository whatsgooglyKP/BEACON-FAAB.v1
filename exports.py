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
        # Python JSON uses a round-trip float representation. Pandas to_json's
        # default precision can move even source percentages by one binary ULP.
        snapshot=dict(columns=bundle.table.columns.tolist(),dtypes={c:str(d) for c,d in bundle.table.dtypes.items()},data=bundle.table.to_dict('records'))
        z.writestr('baseline.schema.json',_json(snapshot))
        z.writestr('proposals.json',_json(queue.to_dict('records')))
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
        # Use the standard JSON parser for exact IEEE-754 float round trips;
        # restore explicit dtypes rather than letting CSV/JSON inference guess.
        snapshot=json.loads(z.read('baseline.schema.json'))
        baseline=pd.DataFrame(snapshot['data'],columns=snapshot['columns'])
        for field,dtype in snapshot['dtypes'].items():
            if dtype=='object': baseline[field]=baseline[field].where(baseline[field].notna(),float('nan'))
            baseline[field]=baseline[field].astype(dtype)
        proposals=json.loads(z.read('proposals.json'))
        events=json.loads(z.read('decisions.json'));groups={}
        for event in events: groups.setdefault(event['proposal_id'],[]).append(event)
        return ReviewStore._apply(baseline,proposals,{p:ReviewStore.fold(es) for p,es in groups.items()})
