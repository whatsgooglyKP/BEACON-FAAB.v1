"""Create an explicitly simulated, separate reviewer workspace over real data.

Run .venv/bin/python scripts/prepare_demo.py, then use the environment values
printed below. Never seeds the ordinary application database or changes sources.
"""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from clean import run
from review_store import ReviewStore


def prepare(path='data/review/demo.sqlite3'):
    """Seed one explained acknowledgment and one unresolved two-reviewer example."""
    s=ReviewStore(path)
    for region in ('fl',):
        b,q=run(region);rid=b.manifest['run_id'];s.register(rid,q,b.manifest,b.observations,b.table)
        p=q[q.rule_id.eq('R14')].iloc[0]
        if s.state(rid,p.proposal_id)['version']==0:
            s.decide(rid,p.proposal_id,'Accept','Demo reviewer A','SIMULATED DEMO: I understand the component years; this does not make the 2020 base current.')
        p=q[q.rule_id.eq('R17')].iloc[0]
        if s.state(rid,p.proposal_id)['version']==0:
            s.decide(rid,p.proposal_id,'Accept','Demo reviewer A','SIMULATED DEMO: use the appendix driving half/10 definition and preserve sensitivity.')
            s.decide(rid,p.proposal_id,'Reject','Demo reviewer B','SIMULATED DEMO: request local review of definition sensitivity before acting.')
            s.add_note(rid,p.tract_id,'Demo reviewer B','SIMULATED DEMO note: ask a practitioner about this pattern. No source figure has been changed.')
        print(region,len(b.table),'real tracts; ready after simulated regional acknowledgment:',int(s.apply(rid,b.table).review_complete.sum()))
    print(f'Demo only: BEACON_REVIEW_DB={path} BEACON_DEMO_MODE=1 .venv/bin/streamlit run app.py --server.port 8510')


if __name__=='__main__': prepare()
