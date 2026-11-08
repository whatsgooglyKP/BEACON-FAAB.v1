"""Faithful offline evidence reports and an optional, constrained Gemini interface.

The deterministic packet is always available. Gemini may only reorder approved
paragraphs: exact sentence/indicator/unit/geography/year matching rejects semantic
swaps as well as invented numbers. It never fills values, scores, or resolves votes.
"""
import os
import json
import threading
import time
from collections import Counter
from indicators import REGIONS
from presentation import readable_text


def evidence_report(bundle, proposals, reviewed=None):
    """Describe what is known, what changed, and what still needs human judgment."""
    t=bundle.table;name=REGIONS[bundle.manifest['community_id']]['name']
    flagged=int(t.lila_half10_driving.eq(1).sum())
    safe=int(proposals.auto_applied.sum())
    ready=int(reviewed.review_complete.sum()) if reviewed is not None else 0
    lines=[f'# Evidence report · {name}',
        f'{len(t)} neighborhoods (2020 census tracts) were retained; {flagged} neighborhoods are flagged low income AND low access under driving LILA, ½ mile urban / 10 miles rural. These are source flags, not confirmed hunger or predicted shortages.',
        f'Originals are preserved. {safe} formatting records were saved; uncertain evidence still needs human review. {ready} neighborhoods have completed the relevant review; one-reviewer decisions are provisional.',
        'Sources: ACS 2020–24 poverty and SNAP ready-made percentages. Poverty describes persons with poverty status determined; SNAP participation describes households. Occupied housing units are called homes, not households.',
        'Access uses the 2020 population base and a June 2025 retailer snapshot. Conditions may have changed. USDA initial release was July 2026; its poverty figures share the upstream ACS source, so agreement is not independent corroboration.',
        'The common priority score uses equal-weight within-community midrank percentiles of poverty and continuous low-access population share. Missing either measure means unscored, never zero. Confidence is an evidence-quality label, not a prediction probability.',
        'Review retains uncertain estimates, explains imprecision, and requires a named reason for Accept, Reject or source-backed Edit. Disputed patches are withheld. Acknowledging a limitation does not repair it or make data newer.',
        'No pantry stock, current capacity, eligibility, institution type or unserved person is established by these files. Resource finder links support manual follow-up, not a verified nearest facility. Inventory routing and forecasting need separate validated data.']
    if bundle.manifest['community_id']=='fl': lines.append('Limitation: transportation data is not available for Central Florida; supplied food-insecurity estimates are also absent. Both remain missing, not zero.')
    else: lines.append('Transportation is modeled adult context, separate from the common score; its 95% interval is not an ACS margin of error. PLACES reference years remain unverified (2025 is the release year).')
    return '\n\n'.join(lines)


def validate_generated(text,base):
    """Exact paragraph multiset gate prevents same-number/wrong-indicator laundering."""
    def parts(s): return Counter(p.strip() for p in s.split('\n\n') if p.strip())
    return bool(text and text.strip()) and parts(text)==parts(base)


AI_TIMEOUT_SECONDS = 20
AI_UNAVAILABLE_NOTE = 'AI summary unavailable right now; showing the built-in summary.'


class GenerationJob:
    """A nonblocking optional request with a wall-clock result deadline.

    The SDK gets one attempt, not hidden retries. An independent deadline guards
    even an uncooperative transport/client constructor. Late results are discarded;
    daemon workers cannot hold up a Streamlit rerun or process shutdown.
    """
    def __init__(self, base, client_factory=None, timeout_s=None):
        self.base=base
        budget=min(AI_TIMEOUT_SECONDS,AI_TIMEOUT_SECONDS if timeout_s is None else max(.001,float(timeout_s)))
        # Leave a small scheduling/render margin below the hard 20-second ceiling.
        self.deadline=time.monotonic()+budget-min(.5,budget*.05)
        self._lock=threading.Lock();self._done=threading.Event();self._result=None
        threading.Thread(target=self._work,args=(client_factory,),daemon=True,name='optional-beacon-ai').start()

    def _work(self, client_factory):
        result=_call_model(self.base,client_factory,self.deadline)
        with self._lock:
            if self._result is None:
                self._result=result if time.monotonic()<self.deadline else (self.base,'template (Gemini timeout)')
            self._done.set()

    def poll(self):
        """Return immediately: None while pending, otherwise a stable text/mode pair."""
        with self._lock:
            if self._result is None and time.monotonic()>=self.deadline:
                self._result=(self.base,'template (Gemini timeout)');self._done.set()
            return self._result

    def wait(self):
        """Bounded synchronous adapter for CLI/evals; the UI never calls this."""
        self._done.wait(max(0,self.deadline-time.monotonic()))
        return self.poll() or (self.base,'template (Gemini timeout)')


def _call_model(base,client_factory,deadline):
    """One constrained model attempt; only public evidence goes into the packet."""
    key=os.getenv('GEMINI_API_KEY');client=None
    if not key and client_factory is None: return base,'template (no Gemini key)'
    try:
        if client_factory is None:
            from google import genai
            remaining=min(19000,int(max(0,deadline-time.monotonic())*1000))
            if remaining<=0: return base,'template (Gemini timeout)'
            client=genai.Client(api_key=key,http_options={'timeout':remaining,'retry_options':{'attempts':1}})
        else: client=client_factory()
        prompt=('You are organizing an evidence packet for a food-bank coordinator. Return JSON with a paragraphs array. '
            'Copy EVERY paragraph exactly once, verbatim, but you may reorder them for readability. Do not alter any words, numbers, units, years, links or caveats. '
            'This is not permission to add analysis. Packet:\n'+json.dumps(base.split('\n\n')))
        out=client.models.generate_content(model='gemini-3.8-flash',contents=prompt,config={'response_mime_type':'application/json'})
        result='\n\n'.join(json.loads(out.text)['paragraphs'])
        if not validate_generated(result,base): return base,'template (Gemini semantic gate rejected output)'
        return result,'gemini'
    except Exception:
        return base,'template (Gemini unavailable)'
    finally:
        if client_factory is None and client is not None:
            try: client.close()
            except Exception: pass


def start_generation(base,client_factory=None,timeout_s=None):
    """Start optional AI work and return immediately; built-in text stays visible."""
    return GenerationJob(base,client_factory,timeout_s)


def _generate(base,client_factory=None):
    """Explicit CLI/model request only, with the same total twenty-second cap."""
    return start_generation(base,client_factory).wait()


def make_report(bundle,proposals,reviewed=None,client_factory=None,use_gemini=False):
    """Default fast/offline report; optional Gemini has no authority over data."""
    base=evidence_report(bundle,proposals,reviewed)
    return _generate(base,client_factory) if use_gemini else (base,'template')


def answer_question(question,bundle,proposals,tract=None,use_gemini=False,client_factory=None):
    """A bounded chat prototype: explain sources, missingness, a tract, or resources.

    Retrieval is deterministic and limited to the loaded public packet. Unknown
    questions receive that boundary rather than an unsupported conversational claim.
    """
    q=question.lower()
    from need import RESOURCES
    name,url=RESOURCES[bundle.manifest['community_id']]
    if any(w in q for w in ('resource','pantry','where','food bank')):
        text=f'Public resource finder: [{name}]({url}). Check current eligibility, opening hours and service area directly. These data do not establish a nearest pantry, available stock, delivery, or capacity.'
    elif any(w in q for w in ('missing','limitation','transport','year','fresh')):
        text=evidence_report(bundle,proposals).split('\n\n')[-1]+'\n\nAccess uses the 2020 population base, June 2025 retailers, and ACS 2020–24. Conditions may have changed; PLACES observation years are unverified. Missing information is not zero.'
    elif tract is not None and any(w in q for w in ('why','rank','flag','confidence','need','tract')):
        text=str(tract['why'])+'\n\n'+str(tract['limitations'])+'\n\nReview tier: '+str(tract['review_tier'])+'. Confirm or challenge this inference in the recommendation controls; do not rewrite official statistics using local knowledge.'
    else:
        text='I can explain the loaded sources, missing information, selected tract reasoning, or public resource finders. I cannot establish live shortages, surplus, benefit eligibility, or current pantry stock.\n\n'+evidence_report(bundle,proposals)
    text=readable_text(text)
    return _generate(text,client_factory) if use_gemini else (text,'template')
