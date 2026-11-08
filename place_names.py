"""Small, offline, source-pinned approximate place labels—not analytical inputs."""
from pathlib import Path
import hashlib
import json
import pandas as pd

LOOKUP=Path(__file__).resolve().parent/'data/clean/tract_place_names.csv'
FL_LIMITATION='Place names are approximate labels from Census boundaries; a tract can span more than one area.'


def read_lookup():
    """Fail visibly on incomplete/duplicate labels instead of inventing a nearby city."""
    frame=pd.read_csv(LOOKUP,dtype=str,keep_default_na=False)
    required={'tract_id','display_name','method','source_url','source_vintage'}
    if not required.issubset(frame) or not frame.tract_id.str.fullmatch(r'\d{11}').all() or frame.tract_id.duplicated().any():
        raise ValueError('Invalid place-name lookup; rebuild with scripts/build_place_names.py')
    if frame.display_name.str.strip().eq('').any(): raise ValueError('Place names must not be blank')
    return frame


def attach_names(frame,lookup,regional='Central Florida (regional notice)'):
    """Add display-only labels to a copy; leave rows, ordering and all source values intact."""
    out=frame.copy()
    if 'tract_id' in out:
        names=lookup.set_index('tract_id').display_name
        actual=out.tract_id.fillna('').ne('')
        missing=set(out.loc[actual,'tract_id'])-set(names.index)
        if missing: raise ValueError('Place-name lookup does not cover all retained census tracts')
        out['display_name']=out.tract_id.map(names).fillna(regional)
    return out


def label(tract_id,names):
    """Primary place name with the full tract GEOID retained alongside it."""
    if not tract_id: return 'Central Florida (regional notice)'
    return f'{names.get(str(tract_id),"Place label unavailable")} · tract {tract_id}'


def enrich_bundle(bundle):
    """Attach a pinned naming snapshot without changing the analytical run identity."""
    lookup=read_lookup()
    bundle.table=attach_names(bundle.table,lookup)
    bundle.observations=attach_names(bundle.observations,lookup)
    bundle.place_names=lookup[lookup.tract_id.isin(bundle.table.tract_id)].copy()
    metadata=json.loads(LOOKUP.with_suffix('.sources.json').read_text())
    if metadata['lookup_sha256']!=hashlib.sha256(LOOKUP.read_bytes()).hexdigest():
        raise ValueError('Place-name lookup/provenance hash mismatch')
    bundle.manifest['place_names']={**metadata,'limitation':FL_LIMITATION}
    return bundle
