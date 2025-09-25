import os
import json
import subprocess
import sys
import time

ROOT = os.path.abspath(os.path.dirname(__file__))
# check both top-level manuscripts and the copy under AI_Audiobook_Generator
MANUSCRIPTS_DIRS = [
    os.path.join(ROOT, 'manuscripts'),
    os.path.join(ROOT, 'AI_Audiobook_Generator', 'manuscripts'),
]
MAIN_SCRIPT = os.path.join(ROOT, 'AI_Audiobook_Generator', 'main.py')

summary = []

all_manuscript_dirs = []
for d in MANUSCRIPTS_DIRS:
    if not os.path.isdir(d):
        continue
    for name in sorted(os.listdir(d)):
        mdir = os.path.join(d, name)
        if not os.path.isdir(mdir):
            continue
        # avoid duplicates
        if mdir not in all_manuscript_dirs:
            all_manuscript_dirs.append(mdir)

if not all_manuscript_dirs:
    print('No manuscript directories found in:', MANUSCRIPTS_DIRS)
    sys.exit(1)

for mdir in all_manuscript_dirs:
    name = os.path.basename(mdir)
    # find a suitable TOC JSON inside the manuscript folder.
    # prefer common names: <name>.json, <name>_toc.json, toc.json
    candidates = [
        os.path.join(mdir, f"{name}.json"),
        os.path.join(mdir, f"{name}_toc.json"),
        os.path.join(mdir, "toc.json"),
    ]

    # add any other .json files in the folder as candidates
    for fn in os.listdir(mdir):
        if fn.lower().endswith('.json') and os.path.join(mdir, fn) not in candidates:
            candidates.append(os.path.join(mdir, fn))

    jpath = None
    for cand in candidates:
        if not os.path.exists(cand):
            continue
        # quick validation: check that the file looks like a TOC
        try:
            with open(cand, 'r', encoding='utf-8') as fh:
                j = json.load(fh)
            # Accept if it's a dict with 'toc' list, or a list of entries with expected keys
            if isinstance(j, dict) and isinstance(j.get('toc'), list):
                jpath = cand
                break
            if isinstance(j, list):
                # check for expected keys in first element
                first = j[0] if j else None
                if isinstance(first, dict) and any(k in first for k in ('chapter_title', 'title', 'name', 'source_page_number', 'page', 'p')):
                    jpath = cand
                    break
        except Exception:
            # not a valid json/TOC - skip
            continue

    if jpath is None:
        # skip folders without json TOC
        continue

    outdir = os.path.join(mdir, 'output')
    # ensure output is clean
    if os.path.exists(outdir):
        try:
            import shutil
            shutil.rmtree(outdir)
        except Exception as e:
            print('Failed to remove existing output for', name, e)
    os.makedirs(outdir, exist_ok=True)

    print(f"Running dry-run for {name}...", flush=True)
    cmd = [sys.executable, MAIN_SCRIPT, mdir, outdir, '--skip-conversion', '--dry_run', '--log_level', 'INFO']
    try:
        proc = subprocess.run(cmd, check=False)
    except Exception as e:
        print('Failed to run main.py for', name, e)

    audit = os.path.join(outdir, name, 'processed_text', f"{name}_dry_run_audit.json")
    toc_count = 0
    planned = 0
    empty = 0
    audit_found = False

    # count TOC entries from json
    try:
        with open(jpath, 'r', encoding='utf-8') as fh:
            j = json.load(fh)
        toc_list = j.get('toc') if isinstance(j, dict) and 'toc' in j else (j if isinstance(j, list) else [])
        toc_count = len(toc_list)
    except Exception:
        toc_count = 0

    if os.path.exists(audit):
        try:
            with open(audit, 'r', encoding='utf-8') as fh:
                data = json.load(fh)
            planned = len(data)
            empty = sum(1 for d in data if d.get('chapter_len', 0) == 0)
            audit_found = True
        except Exception as e:
            print('Failed to parse audit for', name, e)

    summary.append({
        'manuscript': name,
        'toc_entries': toc_count,
        'planned_chapters': planned,
        'empty_chapters': empty,
        'audit_found': audit_found
    })

    # small delay to avoid tight loop
    time.sleep(0.2)

out_path = os.path.join(ROOT, 'manuscripts_dryrun_summary.json')
with open(out_path, 'w', encoding='utf-8') as of:
    json.dump(summary, of, indent=2, ensure_ascii=False)

print('Wrote summary to', out_path)
