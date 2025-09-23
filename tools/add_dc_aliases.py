import json
from pathlib import Path

p = Path('data/facility_aliases.json')
js = json.loads(p.read_text())

new_aliases = {
    "medstar whc": "medstar-washington-hospital-center",
    "med star": "medstar-washington-hospital-center",
    "medstar washington": "medstar-washington-hospital-center",
    "medstar wh": "medstar-washington-hospital-center",
    "gw": "george-washington-university-hospital",
    "the gw": "george-washington-university-hospital",
    "cnmc": "children-s-national-medical-center",
    "childrens national hospital": "children-s-national-medical-center",
    "childrens national medical center": "children-s-national-medical-center",
}

changed = False
for k, v in new_aliases.items():
    if k not in js:
        js[k] = v
        changed = True

if changed:
    # write back with consistent formatting
    p.write_text(json.dumps(js, indent=2, ensure_ascii=False))
    print('Updated facility_aliases.json - added', sum(1 for k in new_aliases if k in js))
else:
    print('No changes needed')
