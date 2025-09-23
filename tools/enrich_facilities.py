"""Generate an enrichment CSV and an enriched JSON snapshot for external facilities.

Heuristics applied:
- Infer level_of_care from `type` (acute/community/pediatric/rehab)
- Mark `is_inpatient_rehabilitation` true when `type` contains 'rehab' or 'rehabilitation'
- Default average therapy hours: rehab=3, acute=2, community=1.5, pediatric=2
- Ensure `alias_names` exists (collected from facility_aliases.json reverse mapping)
- Ensure `specializations.carf_accreditations.brain_injury.value` exists (default false)
- Ensure `specializations.ventilator_weaning.is_available` exists (default false)

Outputs:
- tools/facility_enrichment.csv for manual review/edit
- data/external_facilities.enriched.json (snapshot with added fields)

Run with: python tools/enrich_facilities.py
"""
import json
import csv
from pathlib import Path

ROOT = Path('C:/Users/smallick/PycharmProjects/LTACH')
EXT = ROOT / 'data' / 'external_facilities.json'
ALIASES = ROOT / 'data' / 'facility_aliases.json'
OUT_CSV = ROOT / 'tools' / 'facility_enrichment.csv'
OUT_JSON = ROOT / 'data' / 'external_facilities.enriched.json'

ext = json.loads(EXT.read_text(encoding='utf-8'))
alias_map = json.loads(ALIASES.read_text(encoding='utf-8'))

# reverse map: slug -> [aliases]
rev = {}
for a, slug in alias_map.items():
    rev.setdefault(slug, []).append(a)

# heuristics
def infer_level_of_care(t):
    if not t:
        return 'unknown'
    s = t.lower()
    if 'rehab' in s or 'rehabilitation' in s:
        return 'inpatient_rehabilitation'
    if 'pediatric' in s or 'children' in s:
        return 'pediatric'
    if 'acute' in s or 'medical center' in s or 'hospital' in s:
        return 'acute'
    if 'community' in s:
        return 'community'
    return 'other'

def infer_is_rehab(t):
    if not t:
        return False
    s = t.lower()
    return 'rehab' in s or 'rehabilitation' in s or 'inpatient rehabilitation' in s

def default_therapy_hours(level):
    return {
        'inpatient_rehabilitation': 3,
        'rehab': 3,
        'acute': 2,
        'community': 1.5,
        'pediatric': 2,
        'other': 1.5,
        'unknown': 1.5
    }.get(level, 1.5)

# enrich copy
enriched = []
rows = []
# heuristic overrides for well-known providers (name substrings -> therapy hours, carf)
HIGH_THERAPY_KEYWORDS = ['kessler','rusk','moss','gaylord','shepherd','craig','tirr','shirley','abilitylab','medstar national','encompass']
CARF_KEYWORDS = ['gaylord','kessler','craig','shepherd','tirr','shirley','abilitylab']
def apply_provider_overrides(name, aliases, current_ath, current_carf):
    n = (name or '').lower()
    alias_text = ' '.join(aliases).lower() if aliases else ''
    ath = current_ath
    carf = current_carf
    for kw in HIGH_THERAPY_KEYWORDS:
        if kw in n or kw in alias_text:
            ath = 3
            break
    for kw in CARF_KEYWORDS:
        if kw in n or kw in alias_text:
            carf = True
            break
    return ath, carf
for f in ext:
    slug = f.get('id')
    name = f.get('name', {}).get('value') if isinstance(f.get('name'), dict) else f.get('name')
    type_ = f.get('type')
    level = f.get('level_of_care') or infer_level_of_care(type_)
    is_rehab = f.get('is_inpatient_rehabilitation') if 'is_inpatient_rehabilitation' in f else infer_is_rehab(type_)
    # ensure program_details
    pd = f.setdefault('program_details', {})
    ath = None
    if isinstance(pd.get('average_therapy_hours_per_day'), dict):
        ath = pd.get('average_therapy_hours_per_day', {}).get('value')
    else:
        ath = pd.get('average_therapy_hours_per_day')
    if ath is None:
        ath = default_therapy_hours(level)
        pd['average_therapy_hours_per_day'] = {'value': ath}
    # ensure carf and vent settings exist before applying provider overrides
    spec = f.setdefault('specializations', {})
    carf = spec.setdefault('carf_accreditations', {})
    brain = carf.setdefault('brain_injury', {})
    if 'value' not in brain:
        brain['value'] = False
    vent = spec.setdefault('ventilator_weaning', {})
    if 'is_available' not in vent:
        vent['is_available'] = {'value': False} if isinstance(vent.get('is_available'), dict) else False
    # stronger heuristics: if name/aliases indicate rehab or known providers, bump therapy hours or carf
    aliases_list = f.get('alias_names') or []
    ath_override, carf_override = apply_provider_overrides(name, aliases_list, ath, brain.get('value'))
    if ath_override != ath:
        pd['average_therapy_hours_per_day'] = {'value': ath_override}
        ath = ath_override
    if carf_override is True:
        brain['value'] = True
        carf = True
    # ensure alias_names
    aliases = f.get('alias_names') or rev.get(slug) or []
    f['alias_names'] = sorted(list(set(aliases)))
    # normalize contact
    contact = f.setdefault('contact', {})
    website = contact.get('website')
    if website and website.startswith('www.'):
        contact['website'] = 'https://' + website.lstrip('/')
    # add inferred fields
    f['level_of_care'] = level
    # if name includes rehab tokens but previous flags missed it, set is_inpatient_rehabilitation
    name_low = (name or '').lower()
    if not is_rehab and ('rehab' in name_low or 'rehabilitation' in name_low or 'inpatient' in name_low):
        is_rehab = True
    f['is_inpatient_rehabilitation'] = bool(is_rehab)
    enriched.append(f)
    rows.append({
        'id': slug,
        'name': name,
        'type': type_ or '',
        'level_of_care': level,
        'is_inpatient_rehabilitation': bool(is_rehab),
        'average_therapy_hours_per_day': ath,
        'carf_brain_injury': brain.get('value'),
        'ventilator_weaning': vent.get('is_available') if isinstance(vent.get('is_available'), dict) else vent.get('is_available'),
        'admissions_phone': contact.get('admissions_phone'),
        'website': contact.get('website'),
        'location': f.get('location'),
        'address': f.get('address'),
        'zip': f.get('zip'),
        'aliases': '|'.join(f.get('alias_names') or [])
    })

# write CSV
OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
with OUT_CSV.open('w', newline='', encoding='utf-8') as csvf:
    fieldnames = ['id','name','type','level_of_care','is_inpatient_rehabilitation','average_therapy_hours_per_day','carf_brain_injury','ventilator_weaning','admissions_phone','website','location','address','zip','aliases']
    writer = csv.DictWriter(csvf, fieldnames=fieldnames)
    writer.writeheader()
    for r in rows:
        writer.writerow(r)

# write enriched JSON snapshot (do not overwrite original)
OUT_JSON.write_text(json.dumps(enriched, indent=2, ensure_ascii=False), encoding='utf-8')
print(f'Wrote {OUT_CSV} ({len(rows)} rows) and snapshot {OUT_JSON}')
