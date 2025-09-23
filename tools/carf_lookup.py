#!/usr/bin/env python3
"""CARF lookup helper.

Usage: python tools/carf_lookup.py

Behavior:
- If `data/carf_registry.csv` exists, use it as a local registry. CSV columns: name,carf_brain_injury,average_therapy_hours,level_of_care
- Otherwise, if environment variable CARF_API_KEY is set, a placeholder external lookup function can be used (not enabled by default).
- Reads data/external_facilities.enriched.json, applies registry matches to set `specializations.carf_accreditations.brain_injury.value` and optional overrides, and writes a new snapshot with suffix `.carf.json` and a small CSV report in `tools/carf_lookup_report.csv`.
"""
import csv
import json
import os
from pathlib import Path
from difflib import SequenceMatcher
try:
    from rapidfuzz import fuzz
    HAVE_RAPIDFUZZ = True
except Exception:
    HAVE_RAPIDFUZZ = False
import re

ROOT = Path(__file__).resolve().parents[1]
ENRICHED = ROOT / 'data' / 'external_facilities.enriched.json'
OUT_JSON = ROOT / 'data' / 'external_facilities.enriched.carf.json'
REPORT = ROOT / 'tools' / 'carf_lookup_report.csv'
REGISTRY = ROOT / 'data' / 'carf_registry.csv'  # local registry (optional)


def load_local_registry(path):
    regs = []
    if not path.exists():
        return regs
    with path.open(encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for r in reader:
            # normalize
            regs.append({
                'name': (r.get('name') or '').strip(),
                'carf_brain_injury': (r.get('carf_brain_injury') or '').strip().lower() in ('1','true','yes'),
                'average_therapy_hours': float(r.get('average_therapy_hours') or 0) if r.get('average_therapy_hours') else None,
                'level_of_care': (r.get('level_of_care') or '').strip() or None
            })
    return regs


def normalize_text(s):
    if not s:
        return ''
    s = s.lower()
    s = re.sub(r"[^a-z0-9 ]+", ' ', s)
    s = re.sub(r"\s+", ' ', s).strip()
    return s

def similar(a, b):
    if HAVE_RAPIDFUZZ:
        try:
            # use token_sort_ratio as a stable measure (0-100)
            return fuzz.token_sort_ratio(a, b) / 100.0
        except Exception:
            return SequenceMatcher(None, a.lower(), b.lower()).ratio()
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def rapidfuzz_combined(a, b):
    """Combined RapidFuzz-based score (0.0 - 1.0). Falls back to SequenceMatcher when RapidFuzz missing.

    We combine token_sort_ratio, partial_ratio and token_set_ratio plus token overlap to improve recall.
    """
    if not HAVE_RAPIDFUZZ:
        return similar(a, b)
    try:
        ts = fuzz.token_sort_ratio(a, b)
        pr = fuzz.partial_ratio(a, b)
        tset = fuzz.token_set_ratio(a, b)
        # normalize to 0..1 and weight
        score = (0.45 * ts + 0.25 * pr + 0.2 * tset) / 100.0
        # nudge with token overlap (0..1)
        score = max(score, token_overlap_score(a, b) * 0.9)
        return min(max(score, 0.0), 1.0)
    except Exception:
        return similar(a, b)

def token_overlap_score(a, b):
    A = set(normalize_text(a).split())
    B = set(normalize_text(b).split())
    if not A or not B:
        return 0.0
    inter = A.intersection(B)
    return len(inter) / max(len(A), len(B))


def find_registry_matches(name, aliases, regs, top_n=3):
    """Return up to top_n candidate registry rows with scores (sorted desc).

    This computes both sequence-similarity and token-overlap and returns
    a list of tuples (score, registry_row). The caller can decide whether to
    auto-apply a match or surface it for manual review.
    """
    if not name and not aliases:
        return []
    candidates = []
    text = (name or '') + ' ' + ' '.join(aliases or [])
    for r in regs:
        score_sim = max(similar(text, r['name']), similar(name or '', r['name']))
        score_tok = token_overlap_score(text, r['name'])
        score = max(score_sim, score_tok)
        candidates.append((score, r))
    candidates.sort(key=lambda x: x[0], reverse=True)
    return candidates[:top_n]


def apply_registry(regs):
    data = json.loads(ENRICHED.read_text(encoding='utf-8'))
    report_rows = []
    suggestion_rows = []
    updated = 0

    # thresholds
    AUTO_APPLY_THRESHOLD = 0.75  # auto-apply only high-confidence matches
    SUGGESTION_MIN = 0.3         # surface candidates above this for review

    for f in data:
        name = ''
        if isinstance(f.get('name'), dict):
            name = f['name'].get('value') or ''
        else:
            name = f.get('name') or ''
        aliases = f.get('alias_names') or []

        candidates = find_registry_matches(name, aliases, regs, top_n=5)
        top_score = candidates[0][0] if candidates else 0
        top_match = candidates[0][1] if candidates else None

        carf_before = False
        try:
            carf_before = bool(f['specializations']['carf_accreditations']['brain_injury']['value'])
        except Exception:
            carf_before = False

        applied = False
        # Auto-apply only very confident matches
        if top_match and top_score >= AUTO_APPLY_THRESHOLD:
            match = top_match
            # apply
            spec = f.setdefault('specializations', {})
            carf = spec.setdefault('carf_accreditations', {})
            brain = carf.setdefault('brain_injury', {})
            if match.get('carf_brain_injury'):
                brain['value'] = True
            # optionally override therapy hours and level_of_care if provided
            pd = f.setdefault('program_details', {})
            if match.get('average_therapy_hours'):
                pd['average_therapy_hours_per_day'] = {'value': match['average_therapy_hours']}
            if match.get('level_of_care'):
                f['level_of_care'] = match['level_of_care']
            applied = True
            updated += 1

        # Prepare report row
        report_rows.append({
            'id': f.get('id'),
            'name': name,
            'matched': bool(candidates),
            'match_score': round(top_score, 2),
            'carf_before': carf_before,
            'carf_after': bool(f.get('specializations', {}).get('carf_accreditations', {}).get('brain_injury', {}).get('value'))
        })

        # If there are candidate matches above SUGGESTION_MIN, write them to suggestions CSV
        for score, m in candidates:
            if score >= SUGGESTION_MIN:
                suggestion_rows.append({
                    'id': f.get('id'),
                    'facility_name': name,
                    'candidate_name': m.get('name'),
                    'score': round(score, 3),
                    'candidate_carf': m.get('carf_brain_injury'),
                    'candidate_therapy_hours': m.get('average_therapy_hours')
                })

    # write outputs
    OUT_JSON.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    with REPORT.open('w', newline='', encoding='utf-8') as csvf:
        fieldnames = ['id','name','matched','match_score','carf_before','carf_after']
        writer = csv.DictWriter(csvf, fieldnames=fieldnames)
        writer.writeheader()
        for r in report_rows:
            writer.writerow(r)

    # suggestions file
    SUGG = REPORT.parent / 'carf_lookup_suggestions.csv'
    with SUGG.open('w', newline='', encoding='utf-8') as sf:
        fieldnames = ['id', 'facility_name', 'candidate_name', 'score', 'candidate_carf', 'candidate_therapy_hours']
        writer = csv.DictWriter(sf, fieldnames=fieldnames)
        writer.writeheader()
        for r in suggestion_rows:
            writer.writerow(r)

    print(f'Wrote updated enriched snapshot: {OUT_JSON} and report {REPORT} (auto-applied {updated} records)')
    print(f'Wrote candidate suggestions: {SUGG} (inspect and apply manually or adjust thresholds)')


def main():
    regs = load_local_registry(REGISTRY)
    if not regs:
        print('No local registry found at', REGISTRY)
        print('Place a CSV at data/carf_registry.csv with columns name,carf_brain_injury,average_therapy_hours,level_of_care')
        return 1
    apply_registry(regs)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
