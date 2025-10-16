# SEO Analyzer

A small Python script that crawls a website (starting from a provided URL) and performs a basic on-page SEO audit. It checks title tags, meta descriptions, H1s, images (alt text), internal and broken links, and word counts.

Prerequisites

- Python 3.8+
- Install dependencies with:

```
pip install -r requirements.txt
```

Usage

```
python seo_analyzer.py https://yourwebsite.com
```

Output

- Generates `seo_audit_report.csv` in the current directory with the audit results.

Notes

- The crawler only discovers links on the starting page (no full-site recursive crawl).
- The script uses HEAD requests where possible to check for broken internal links. Some servers may not respond to HEAD; in such cases, the script records a connection error.
- Be respectful of robots.txt and site terms; this tool is for small-scale audits only.
