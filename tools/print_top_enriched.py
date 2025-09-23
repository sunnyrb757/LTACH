#!/usr/bin/env python3
import json
from pathlib import Path

P = Path(__file__).resolve().parents[1] / 'data' / 'external_facilities.enriched.json'
data = json.loads(P.read_text(encoding='utf-8'))
for i, rec in enumerate(data[:20], 1):
    name = rec.get('name', {}).get('value', '')
    avg = rec.get('program_details', {}).get('average_therapy_hours_per_day', {}).get('value')
    carf = rec.get('specializations', {}).get('carf_accreditations', {}).get('brain_injury', {}).get('value')
    print(f"{i:02d}. {name}\n    avg_therapy_hours: {avg}  carf_brain_injury: {carf}\n")
