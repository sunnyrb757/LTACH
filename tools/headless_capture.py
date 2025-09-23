"""
Headless capture helper using Playwright (Python).
Saves:
 - tools/headless_output.json  (console + network events)
 - tools/headless_screenshot.png

Run:
  python tools\headless_capture.py

Notes:
 - Requires Playwright: pip install playwright
 - Then: playwright install chromium
"""
import json
import os
import sys
from pathlib import Path

def main():
    try:
        from playwright.sync_api import sync_playwright
    except Exception as e:
        print("Playwright not installed. Install with: pip install playwright")
        raise

    url = os.environ.get('TARGET_URL', 'http://127.0.0.1:8000/index.html')
    out_dir = Path(__file__).resolve().parent
    out_json = out_dir / 'headless_output.json'
    out_png = out_dir / 'headless_screenshot.png'

    events = {
        'console': [],
        'page_errors': [],
        'requests': [],
        'responses': []
    }

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        def on_console(msg):
            try:
                events['console'].append({
                    'type': msg.type,
                    'text': msg.text,
                    'location': msg.location
                })
            except Exception as e:
                events['console'].append({'type': 'error', 'text': str(e)})

        def on_page_error(exc):
            events['page_errors'].append({'error': str(exc)})

        def on_request(request):
            events['requests'].append({'url': request.url, 'method': request.method, 'resource_type': request.resource_type})

        def on_response(response):
            try:
                events['responses'].append({'url': response.url, 'status': response.status, 'status_text': response.status_text})
            except Exception as e:
                events['responses'].append({'url': response.url, 'error': str(e)})

        page.on('console', on_console)
        page.on('pageerror', on_page_error)
        page.on('request', on_request)
        page.on('response', on_response)

        print(f"Loading {url} ...")
        page.goto(url, wait_until='networkidle', timeout=60000)

        # small delay to let runtime errors surface
        page.wait_for_timeout(2000)

        page.screenshot(path=str(out_png), full_page=True)

        # gather DOM snapshot of body length
        try:
            body_html = page.evaluate("() => document.documentElement.outerHTML")
            events['dom_length'] = len(body_html)
        except Exception as e:
            events['dom_error'] = str(e)

        with open(out_json, 'w', encoding='utf-8') as f:
            json.dump(events, f, indent=2)

        print('Saved:', out_json, out_png)
        browser.close()

if __name__ == '__main__':
    main()
