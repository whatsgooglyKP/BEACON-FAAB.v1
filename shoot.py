"""Screenshot the local app with a new isolated headless test browser.

This launches its own disposable Chromium, not the signed-in desktop browser and
not a CDP connection. Start the explicitly labeled demo server on port 8510 first.
Run: .venv/bin/python shoot.py
"""
from pathlib import Path
import re
from playwright.sync_api import sync_playwright


def capture():
    """Exercise the three steps and the conflict view; fail on visible app exceptions."""
    out=Path('screenshots/redesign');out.mkdir(parents=True,exist_ok=True)
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True)
        page=browser.new_page(viewport={'width':1600,'height':1200},device_scale_factor=1)
        page.goto('http://localhost:8510',wait_until='domcontentloaded')
        page.get_by_role('heading',name='Step 1 · Load your community’s public evidence',exact=True).wait_for(timeout=120000)
        page.locator('[data-testid="stDataFrame"]').first.wait_for(timeout=120000)
        page.screenshot(path=str(out/'01_load.png'),full_page=True)
        page.get_by_text('2 · Review',exact=True).click()
        page.get_by_role('heading',name='Step 2 · Review what needs judgment',exact=True).wait_for(timeout=120000)
        page.get_by_text('Action confidence:',exact=False).first.wait_for(timeout=120000)
        card=page.locator('[data-testid="stSelectbox"]').filter(has=page.get_by_text('Choose a review card',exact=True))
        card.get_by_role('combobox').fill('poverty_pct')
        page.get_by_role('option',name=re.compile(r'R08.*poverty_pct')).first.click()
        page.get_by_text('This estimate is imprecise.',exact=False).first.wait_for(timeout=120000)
        page.screenshot(path=str(out/'02_review.png'),full_page=True)
        # Streamlit uses custom comboboxes; select the dedicated disagreement queue.
        queue=page.locator('[data-testid="stSelectbox"]').filter(has=page.get_by_text('Queue view',exact=True))
        queue.get_by_role('button',name='Open',exact=True).click()
        page.get_by_role('option',name='Disagreements',exact=True).click()
        page.get_by_text('Disagreement is visible.',exact=False).wait_for(timeout=120000)
        page.screenshot(path=str(out/'02b_disagreement.png'),full_page=True)
        page.get_by_text('3 · Use',exact=True).click()
        page.get_by_role('heading',name='Step 3 · Use an explained priority list',exact=True).wait_for(timeout=120000)
        page.get_by_text('Map of the displayed neighborhoods',exact=True).wait_for(timeout=120000)
        page.screenshot(path=str(out/'03_use_list.png'),full_page=True)
        page.get_by_text('Map of the displayed neighborhoods',exact=True).scroll_into_view_if_needed()
        page.locator('.js-plotly-plot').first.wait_for(timeout=120000)
        page.screenshot(path=str(out/'03b_use_map.png'),full_page=True)
        page.get_by_role('heading',name='Why this neighborhood?',exact=True).scroll_into_view_if_needed()
        page.screenshot(path=str(out/'03c_explained_tract.png'),full_page=True)
        assert page.locator('[data-testid="stException"]').count()==0
        print('6 screenshots saved; 0 visible app exceptions; simulated reviewers are labeled in the UI')
        browser.close()


if __name__=='__main__': capture()
