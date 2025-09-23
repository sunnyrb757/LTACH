from playwright.sync_api import sync_playwright
import json

URL = "http://127.0.0.1:8000/index.html"
INPUTS = ["D.C.", "DC", "d.c.", "washington dc", "medstar d.c."]

results = []

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto(URL)
    page.wait_for_timeout(1000)
    for q in INPUTS:
        try:
            page.fill('#other-hospital-input', q)
        except Exception:
            # try focusing then typing
            page.click('#other-hospital-input')
            page.fill('#other-hospital-input', q)
        # click analyze
        page.click('#check-facility-btn')
        # wait for result area to update
        page.wait_for_selector('#facility-analysis-result')
        page.wait_for_timeout(500)
        html = page.inner_html('#facility-analysis-result')
        text = page.inner_text('#facility-analysis-result')
        results.append({"input": q, "html": html, "text": text})
    browser.close()

out_path = 'tools/headless_dc_results.json'
import os
os.makedirs(os.path.dirname(out_path), exist_ok=True)
with open(out_path, 'w', encoding='utf-8') as f:
    json.dump(results, f, indent=2, ensure_ascii=False)
print('Wrote', out_path)
print(json.dumps(results, indent=2, ensure_ascii=False))
