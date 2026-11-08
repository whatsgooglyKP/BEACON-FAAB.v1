"""Append-only, local SQLite decisions over immutable evidence.

Names are self-entered prototype identities, not authenticated accounts. This is
sequential collaboration, not production multi-user authorization. Every save is
optimistically versioned and earlier votes survive resolution, revision and undo.
"""
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import json
import math
import sqlite3
import pandas as pd
import numpy as np


class StaleVersion(ValueError):
    """A reviewer tried to save an out-of-date view; reload before deciding."""


def _json(value):
    """Stable JSON including numpy scalars but never nonstandard NaN tokens."""
    def convert(v):
        if isinstance(v,dict): return {k:convert(x) for k,x in v.items()}
        if isinstance(v,(list,tuple)): return [convert(x) for x in v]
        if isinstance(v,np.generic): v=v.item()
        if isinstance(v,float) and not math.isfinite(v): return None
        return v
    return json.dumps(convert(value),sort_keys=True,default=str,allow_nan=False)


def validated_value(field, value):
    """Validate the domain of an edited analytical cell; never silently coerce a guess."""
    if value is None: return None
    n=float(value)
    if not math.isfinite(n): raise ValueError('An edit must be finite.')
    if ('pct' in field and not 0<=n<=100) or ('lila' in field and n not in (0,1)) or n<0:
        raise ValueError('Edited value is outside its valid domain.')
    return n


class ReviewStore:
    """Persist sources, proposals, and a versioned decision overlay in a local file."""
    def __init__(self, path='data/review/evidence.sqlite3'):
        self.path=str(path); Path(path).parent.mkdir(parents=True,exist_ok=True)
        with self._db() as db:
            db.executescript('''
            CREATE TABLE IF NOT EXISTS runs (run_id TEXT PRIMARY KEY, manifest TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS proposals (run_id TEXT, proposal_id TEXT, payload TEXT NOT NULL, PRIMARY KEY(run_id,proposal_id));
            CREATE TABLE IF NOT EXISTS events (event_id INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT, proposal_id TEXT, payload TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS snapshots (run_id TEXT, name TEXT, payload TEXT, PRIMARY KEY(run_id,name));
            CREATE TABLE IF NOT EXISTS notes (id INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT, tract_id TEXT, payload TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS recommendation_events (id INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT, tract_id TEXT, payload TEXT NOT NULL);
            ''')

    def _db(self):
        """Short transactions allow sequential reviewers without a shared connection."""
        db=sqlite3.connect(self.path,timeout=15); db.row_factory=sqlite3.Row
        return db

    def register(self, run_id, proposals, manifest, observations=None, baseline=None):
        """Snapshot a deterministic run once; safe format decisions are system events."""
        with self._db() as db:
            db.execute('INSERT OR IGNORE INTO runs VALUES (?,?)',(run_id,_json(manifest)))
            for p in proposals.to_dict('records'):
                cur=db.execute('INSERT OR IGNORE INTO proposals VALUES (?,?,?)',(run_id,p['proposal_id'],_json(p)))
                if cur.rowcount and p.get('auto_applied'):
                    e=self._event_payload(p,'Accept','System · deterministic import','Safe, reversible format/code recipe; originals preserved.',None,'',0,None,'auto')
                    db.execute('INSERT INTO events(run_id,proposal_id,payload) VALUES (?,?,?)',(run_id,p['proposal_id'],_json(e)))
            for name,value in [('observations',observations),('baseline',baseline)]:
                if value is not None: db.execute('INSERT OR IGNORE INTO snapshots VALUES (?,?,?)',(run_id,name,_json(value.to_dict('records'))))

    @staticmethod
    def _event_payload(p,action,reviewer,note,value,evidence,version,previous,event_kind='vote'):
        """Store before/after, source coordinates and parent version with every event."""
        return dict(proposal=p,rule_version=p.get('rule_version','prototype'),action=action,reviewer=reviewer.strip(),note=note.strip(),
            value=value,evidence=evidence,version=version+1,previous_event_id=previous,event_kind=event_kind,
            before=p.get('before'),after=value if action=='Edit' else p.get('after') if action=='Accept' else p.get('before'),
            created_at=datetime.now(ZoneInfo('America/New_York')).isoformat(timespec='seconds'))

    def proposals(self,run_id):
        """Read the registered queue, including rejected and unresolved proposals."""
        with self._db() as db: rows=db.execute('SELECT payload FROM proposals WHERE run_id=? ORDER BY proposal_id',(run_id,)).fetchall()
        return pd.DataFrame([json.loads(r['payload']) for r in rows])

    def events(self,run_id,proposal_id=None):
        """Read full history in append order, not just the latest person's vote."""
        query='SELECT * FROM events WHERE run_id=?'; args=[run_id]
        if proposal_id is not None: query+=' AND proposal_id=?'; args.append(proposal_id)
        with self._db() as db: rows=db.execute(query+' ORDER BY event_id',args).fetchall()
        return [dict(event_id=r['event_id'],run_id=r['run_id'],proposal_id=r['proposal_id'],**json.loads(r['payload'])) for r in rows]

    @staticmethod
    def fold(events):
        """Reduce history deterministically; a fresh vote reopens any old resolution."""
        votes={}; resolution=None
        for e in events:
            if e.get('event_kind')=='resolution': resolution=e
            else:
                if resolution and e['action']!='Undo':
                    agrees=(e['action']==resolution['action'] and (e['action']!='Edit' or e.get('value')==resolution.get('value')))
                    if not agrees: resolution=None
                if e['action']=='Undo': votes.pop(e['reviewer'],None)
                else: votes[e['reviewer']]=e
        version=events[-1]['version'] if events else 0
        if resolution:
            return dict(status='resolved',action=resolution['action'],value=resolution.get('value'),reviewers=list(votes),version=version,resolution=resolution,votes=list(votes.values()))
        if not votes: return dict(status='pending',action=None,value=None,reviewers=[],version=version,votes=[])
        def signature(v): return (v['action'],_json(v.get('value')) if v['action']=='Edit' else '')
        sigs={signature(e) for e in votes.values()}; latest=list(votes.values())[-1]
        if len(sigs)>1: status='disputed'; action=None; value=None
        else:
            action=latest['action']; value=latest.get('value')
            status=('accepted' if action in ('Accept','Edit') else 'rejected')+('_agreed' if len(votes)>=2 else '_provisional')
        return dict(status=status,action=action,value=value,reviewers=list(votes),version=version,votes=list(votes.values()))

    def state(self,run_id,proposal_id):
        """Compute the consensus overlay; no last-writer-wins shortcut."""
        return self.fold(self.events(run_id,proposal_id))

    def states(self,run_id):
        """Batch state reads to keep a several-thousand-card queue responsive."""
        groups={}
        for e in self.events(run_id): groups.setdefault(e['proposal_id'],[]).append(e)
        return {p:self.fold(es) for p,es in groups.items()}

    def _save(self,run_id,proposal_id,action,reviewer,note,value,evidence,expected_version,event_kind):
        """Validate before a transaction; stale saves are refused, never overwritten."""
        if not reviewer.strip() or not note.strip(): raise ValueError('Reviewer name and reason are required.')
        if action not in ('Accept','Reject','Edit','Undo'): raise ValueError('Unknown decision.')
        if action=='Edit' and not (evidence.startswith('https://') or evidence.startswith('source:')):
            raise ValueError('Edit requires a cited public HTTPS source or an existing source observation.')
        with self._db() as db:
            db.execute('BEGIN IMMEDIATE')
            row=db.execute('SELECT payload FROM proposals WHERE run_id=? AND proposal_id=?',(run_id,proposal_id)).fetchone()
            if not row: raise ValueError('Unknown proposal.')
            p=json.loads(row['payload'])
            if action=='Edit':
                if p.get('kind') not in ('value_change','exclude'): raise ValueError('Context cautions cannot rewrite an official number; add a tract note instead.')
                value=validated_value(p.get('field',''),value)
                if evidence.startswith('source:'):
                    if evidence!='source:'+p.get('source_id','') or value!=p.get('after'): raise ValueError('Source selection must match the proposed observed alternative.')
            history=db.execute('SELECT event_id,payload FROM events WHERE run_id=? AND proposal_id=? ORDER BY event_id',(run_id,proposal_id)).fetchall()
            version=len(history)
            if expected_version is not None and expected_version!=version: raise StaleVersion('This card changed. Reload before saving your decision.')
            e=self._event_payload(p,action,reviewer,note,value,evidence,version,history[-1]['event_id'] if history else None,event_kind)
            db.execute('INSERT INTO events(run_id,proposal_id,payload) VALUES (?,?,?)',(run_id,proposal_id,_json(e)))
        return e

    def decide(self,run_id,proposal_id,action,reviewer,note,value=None,evidence='',expected_version=None):
        """Append Accept / Reject / source-backed Edit / self-Undo without erasing history."""
        return self._save(run_id,proposal_id,action,reviewer,note,value,evidence,expected_version,'vote')

    def resolve(self,run_id,proposal_id,action,reviewer,note,value=None,evidence='',expected_version=None):
        """Explicit resolution selects a visible alternative; new conflicting votes reopen."""
        if self.state(run_id,proposal_id)['status']!='disputed': raise ValueError('Only a disputed proposal needs resolution.')
        if action=='Undo': raise ValueError('A resolution must choose an alternative.')
        return self._save(run_id,proposal_id,action,reviewer,note,value,evidence,expected_version,'resolution')

    @staticmethod
    def _apply(baseline,proposals,states):
        """Build a validated view. Pending or disputed patches never touch source values."""
        out=baseline.copy(); out['review_complete']=True; out['review_status']='reviewed baseline'
        out['has_dispute']=False; out['has_source_conflict']=False; out['evidence_cautions']=''
        # Baseline safety gates operate even if a person rejects the exclusion proposal.
        for f in out.columns:
            if f.endswith('_pct') or f=='low_access_population_pct_half10':
                if pd.api.types.is_numeric_dtype(out[f]): out.loc[~out[f].between(0,100),f]=np.nan
            if f.startswith('lila_') and not f.endswith(('_raw','_missing_reason','_selected_source')):
                out.loc[~out[f].isin([0,1]),f]=np.nan
        for p in sorted(proposals,key=lambda p:p['proposal_id']):
            gid=p.get('tract_id',''); mask=out.tract_id.eq(gid) if gid else pd.Series(True,index=out.index)
            state=states.get(p['proposal_id'],dict(status='pending',action=None,value=None))
            status=state['status']; action=state['action']; relevant=p.get('affects_ranking',True)
            if not p.get('auto_applied') and relevant:
                out.loc[mask,'evidence_cautions']+=p.get('reason','')+' '
                if status in ('pending','disputed'): out.loc[mask,'review_complete']=False
                if status=='disputed': out.loc[mask,'has_dispute']=True
                if p.get('rule_id')=='R15' and status in ('pending','disputed'): out.loc[mask,'has_source_conflict']=True
                priority={'reviewed baseline':0,'accepted_agreed':1,'rejected_agreed':1,'resolved':1,'accepted_provisional':2,'rejected_provisional':2,'pending':3,'disputed':4}
                stronger=mask & out.review_status.map(priority).fillna(0).le(priority.get(status,0))
                out.loc[stronger,'review_status']=status
            field=p.get('field')
            if p.get('kind') in ('value_change','exclude') and action in ('Accept','Edit') and status!='disputed' and field in out:
                value=state['value'] if action=='Edit' else p.get('after')
                out.loc[mask,field]=validated_value(field,value)
                out.loc[mask,field+'_selected_source']='reviewer-cited edit' if action=='Edit' else p.get('source_id','accepted exclusion')
        return out

    def apply(self,run_id,baseline):
        """Recreate the current consensus dataset from an untouched baseline."""
        return self._apply(baseline,self.proposals(run_id).to_dict('records'),self.states(run_id))

    def replay(self,run_id,baseline):
        """Rebuild from audit events alone, independently of any materialized output."""
        groups={}
        for event in self.events(run_id): groups.setdefault(event['proposal_id'],[]).append(event)
        states={pid:self.fold(events) for pid,events in groups.items()}
        return self._apply(baseline,self.proposals(run_id).to_dict('records'),states)

    def add_note(self,run_id,tract_id,reviewer,note,evidence=''):
        """Local knowledge annotates an inference; it never rewrites a statistic."""
        if not reviewer.strip() or not note.strip(): raise ValueError('Reviewer and note are required.')
        payload=dict(reviewer=reviewer.strip(),note=note.strip(),evidence=evidence,created_at=datetime.now(ZoneInfo('America/New_York')).isoformat())
        with self._db() as db: db.execute('INSERT INTO notes(run_id,tract_id,payload) VALUES (?,?,?)',(run_id,tract_id,_json(payload)))

    def notes(self,run_id):
        """Return all tract notes in order; earlier context is never deleted."""
        with self._db() as db: rows=db.execute('SELECT * FROM notes WHERE run_id=? ORDER BY id',(run_id,)).fetchall()
        return [dict(tract_id=r['tract_id'],**json.loads(r['payload'])) for r in rows]

    def recommend(self,run_id,tract_id,action,reviewer,note,replacement='',position=None):
        """Append an operational choice, separately from the model's measured priority."""
        if action not in ('Confirm need','Challenge need','Approve','Reject','Replace action','Reorder'): raise ValueError('Unknown recommendation control.')
        if not reviewer.strip() or not note.strip(): raise ValueError('Reviewer and reason are required.')
        if action=='Replace action' and not replacement.strip(): raise ValueError('A replacement category is required.')
        if action=='Reorder' and (position is None or int(position)<1): raise ValueError('Operational position must be positive.')
        # Ignore unused form controls: agreeing approvals must not be disputed
        # merely because two people left different numbers in the reorder box.
        replacement=replacement.strip() if action=='Replace action' else ''
        position=int(position) if action=='Reorder' else None
        payload=dict(action=action,reviewer=reviewer.strip(),note=note.strip(),replacement=replacement,position=position,created_at=datetime.now(ZoneInfo('America/New_York')).isoformat())
        with self._db() as db: db.execute('INSERT INTO recommendation_events(run_id,tract_id,payload) VALUES (?,?,?)',(run_id,tract_id,_json(payload)))

    def recommendations(self,run_id):
        """Return the full operational history for export and disagreement display."""
        with self._db() as db: rows=db.execute('SELECT * FROM recommendation_events WHERE run_id=? ORDER BY id',(run_id,)).fetchall()
        return [dict(tract_id=r['tract_id'],**json.loads(r['payload'])) for r in rows]
