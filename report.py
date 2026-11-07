"""Health report text: Gemini rewrite of the template report, with template fallback."""
import os
from clean import health_report

PROMPT = ("Rewrite this data health report for a food bank coordinator in plain English, under 250 words. "
          "Keep every number exactly as given; add no new numbers, places, or claims. Keep these framings exactly: "
          "'N tract-level issues plus one statewide CDC gap'; 'values corrected, gaps filled from USDA (labeled), everything else flagged, no original value invented'; "
          "'left out of the ranking (for dorms/tiny size, for shaky estimates)'; and the data-integrity sentence. The car-free figure counts HOMES (housing units) with no car: always say 'homes' or 'housing units', never 'households'.\n\n")

def make_report(t, issues, s, client_factory=None):
    """Returns (text, mode). mode = 'gemini' or 'template...'. client_factory lets tests inject a failing client."""
    base = health_report(t, issues, s)
    key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if os.getenv("USE_GEMINI", "1") != "1" or (not key and client_factory is None): return base, "template"
    try:
        if client_factory is None:
            from google import genai
            client = genai.Client(api_key=key, http_options={"timeout": 150000})
        else: client = client_factory()
        out = client.models.generate_content(model=os.getenv("GEMINI_MODEL", "gemini-3.8-flash"), contents=PROMPT + base)
        if not out.text or not out.text.strip(): raise ValueError("empty response")
        return out.text, "gemini"
    except Exception as e:
        return base, f"template (Gemini error: {type(e).__name__})"
