import re
import json
from pathlib import Path

p = Path('C:/Users/smallick/PycharmProjects/LTACH/data/facility_aliases.json')
s = p.read_text(encoding='utf-8')
# regex to find "key": "value" (allow spaces)
pairs = re.findall(r'"([^"]+)"\s*:\s*"([^"]+)"', s)
# pairs will include many entries; keep last occurrence
mapping = {}
for k, v in pairs:
    mapping[k] = v
# write pretty JSON
out = json.dumps(mapping, indent=2, ensure_ascii=False, sort_keys=False)
p.write_text(out, encoding='utf-8')
print(f'Wrote cleaned aliases ({len(mapping)} entries) to {p}')
