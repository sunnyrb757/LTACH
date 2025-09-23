#!/usr/bin/env python3
"""Import seed_facilities.csv into data/external_facilities.json and run enrichment.
Usage: python tools/import_and_enrich.py
"""
import csv
import json
import os
import subprocess
ROOT = os.path.dirname(os.path.dirname(__file__))
CSV_PATH = os.path.join(ROOT, 'tools', 'seed_facilities.csv')
OUT_JSON = os.path.join(ROOT, 'data', 'external_facilities.json')

def row_to_record(row):
    name = row.get('name')
    aliases = [a.strip() for a in (row.get('aliases') or '').split('|') if a.strip()]
    return {
        'id': None,
        'name': {'value': name, 'confidence': 'Medium'},
        'alias_names': aliases,
        'location': row.get('location',''),
        'address': row.get('address',''),
        'zip': row.get('zip',''),
        'type': row.get('type',''),
        'tags': [],
        'program_details': { 'is_doc_specialist': {'value': False}, 'is_tbi_specialized': {'value': False}, 'has_dedicated_tbi_program': {'value': False}, 'average_therapy_hours_per_day': {'value': None} },
        'specializations': { 'carf_accreditations': {'brain_injury': {'value': False}}, 'ventilator_weaning': {'is_available': {'value': False}} },
        'contact': { 'admissions_phone': '', 'website': '' },
        'level_of_care': None,
        'is_inpatient_rehabilitation': False,
        'notes': ''
    }

def main():
    if not os.path.exists(CSV_PATH):
        print('Seed CSV not found at', CSV_PATH); return 2
    records = []
    with open(CSV_PATH, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for r in reader:
            rec = row_to_record(r)
            # derive id from name if possible
            if rec['name']['value']:
                rec['id'] = rec['name']['value'].lower().replace("'","").replace(',', '').replace('.', '').replace('  ',' ').replace(' ', '-').replace('&','and')
            records.append(rec)
    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    with open(OUT_JSON + '.NEW', 'w', encoding='utf-8') as f:
        json.dump(records, f, indent=2, ensure_ascii=False)
    # move into place
    os.replace(OUT_JSON + '.NEW', OUT_JSON)
    print('Wrote', OUT_JSON)
    # run enrichment script
    enrich_script = os.path.join(ROOT, 'tools', 'enrich_facilities.py')
    if os.path.exists(enrich_script):
        print('Running enrichment...')
        subprocess.check_call([os.path.join(ROOT, '..', '.venv', 'Scripts', 'python.exe') if False else 'python', enrich_script], cwd=ROOT)
    else:
        print('enrich_facilities.py not found; please run tools/enrich_facilities.py manually')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
