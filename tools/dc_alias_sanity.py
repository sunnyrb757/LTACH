#!/usr/bin/env python3
"""Scan data/facility_aliases.json for DC-related tokens and write a short report.
Usage: python tools/dc_alias_sanity.py
"""
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(__file__))
ALIAS_PATH = os.path.join(ROOT, 'data', 'facility_aliases.json')
OUT_PATH = os.path.join(ROOT, 'tools', 'dc_alias_sanity.json')

def main():
    if not os.path.exists(ALIAS_PATH):
        print('Missing', ALIAS_PATH)
        return 2
    with open(ALIAS_PATH, 'r', encoding='utf-8') as f:
        aliases = json.load(f)
    keys = list(aliases.keys())
    check_tokens = [
        'medstar', 'gw', 'gwuh', 'george washington', 'sibley', 'holy cross',
        'inova', 'inova fairfax', 'children', "children's national",
        'washington dc', 'dc', 'd.c.', 'district of columbia'
    ]
    found = {}
    for t in check_tokens:
        rx = re.compile(re.escape(t), re.I)
        matches = [k for k in keys if rx.search(k)]
        found[t] = {'count': len(matches), 'examples': matches[:10]}
    summary = {'total_aliases': len(keys), 'checks': found}
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print('Wrote', OUT_PATH)
    print('Total aliases:', len(keys))
    for t, v in found.items():
        print(f"{t}: {v['count']}")
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
