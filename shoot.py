from playwright.sync_api import sync_playwright
import sys
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={"width": 1500, "height": 1000})
    pg.goto("http://localhost:8510"); pg.wait_for_selector("text=Start here", timeout=90000); pg.wait_for_timeout(3000)
    errs = []
    def chk(name):
        n = pg.locator("[data-testid=stException]").count()
        if n: errs.append((name, pg.locator("[data-testid=stException]").first.inner_text()[:800]))
    chk("home"); pg.screenshot(path="screenshots/1_home_what_to_do_next.png", full_page=True)
    for i, (tab, fn) in enumerate([("Map", "2_map.png"), ("Ranked list", "x_ranked.png"), ("Neighborhood detail", "3_neighborhood_detail.png"), ("Data gaps", "4_data_gaps.png"), ("County comparison", "x_county.png"), ("Action list", "x_actions.png")]):
        pg.get_by_role("tab", name=tab).click(); pg.wait_for_timeout(5000 if tab == "Map" else 2500); chk(tab)
        if tab == "Neighborhood detail":
            pg.get_by_role("button", name="Approve").click(); pg.wait_for_timeout(2500); chk("approve")
        if not fn.startswith("x"): pg.screenshot(path="screenshots/" + fn, full_page=True)
    print("ERRORS:", errs); b.close()
