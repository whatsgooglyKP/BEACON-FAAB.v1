from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={"width": 1400, "height": 900})
    pg.goto("http://localhost:8510"); pg.wait_for_selector("text=Step 1", timeout=90000); pg.wait_for_timeout(2000)
    pg.screenshot(path="screenshots/step1_load.png")
    pg.get_by_role("button", name="Clean the data").click()
    pg.wait_for_selector("text=/Report (written by Gemini|from a fixed template)/", timeout=240000); pg.wait_for_timeout(4000)
    print("mode:", pg.locator("text=/Report (written by Gemini|from a fixed template)/").first.inner_text())
    for h, fn in [("Step 2", "step2_clean.png"), ("Step 3", "step3_report.png")]:
        pg.locator(f"h2:has-text('{h}')").evaluate("e=>e.scrollIntoView()"); pg.wait_for_timeout(800); pg.screenshot(path="screenshots/" + fn)
    pg.locator("h3:has-text('What the clean data shows')").evaluate("e=>e.scrollIntoView()"); pg.wait_for_timeout(3000); pg.screenshot(path="screenshots/step3_map_nearest_grocery.png")
    pg.get_by_text("Try it with the made-up EXAMPLE").click(); pg.wait_for_timeout(5000)
    pg.locator("h3:has-text('What the clean data shows')").evaluate("e=>e.scrollIntoView()"); pg.wait_for_timeout(3000); pg.screenshot(path="screenshots/step3_routing_example.png", full_page=False)
    print("exceptions:", pg.locator("[data-testid=stException]").count()); b.close()
