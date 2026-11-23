#!/usr/bin/env python3
"""Builds one offline-data pack per region listed in tools/regions.json.
Usage: python tools/build_regions.py ksa.pbf [outdir]
  - region "ksa" is built from the whole file
  - every other region is cut out of it with one `osmium extract` pass (config file)
Writes outdir/<id>.graph and outdir/<id>.tsv  (outdir defaults to "out")."""
import json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
src = sys.argv[1]; out = os.path.abspath(sys.argv[2] if len(sys.argv) > 2 else 'out')
os.makedirs(out, exist_ok=True)
regions = json.load(open(os.path.join(HERE, 'regions.json'), encoding='utf-8'))
tmp = os.path.join(out, '_pbf'); os.makedirs(tmp, exist_ok=True)

def build(pbf, rid):
    subprocess.check_call([sys.executable, os.path.join(HERE, 'build_data.py'), os.path.abspath(pbf), rid], cwd=out)

cities = [r for r in regions if r['id'] != 'ksa']
if cities:   # all city boxes cut in one pass over the file
    cfg = {'directory': tmp, 'extracts': [{'output': r['id'] + '.pbf', 'bbox': r['bbox']} for r in cities]}
    cfgp = os.path.join(out, '_extract.json'); json.dump(cfg, open(cfgp, 'w'))
    subprocess.check_call(['osmium', 'extract', '--overwrite', '-c', cfgp, src])

# cities first (small, fast), the whole-KSA pack last: if it runs out of memory the city packs already exist
order = cities + [r for r in regions if r['id'] == 'ksa']
failed = []
for r in order:
    pbf = src if r['id'] == 'ksa' else os.path.join(tmp, r['id'] + '.pbf')
    if not os.path.exists(pbf): print('skip', r['id'], '(no extract)', flush=True); continue
    try: build(pbf, r['id'])
    except subprocess.CalledProcessError as e:
        failed.append(r['id']); print('FAILED', r['id'], '(exit %s) - continuing' % e.returncode, flush=True)
    if r['id'] != 'ksa' and os.path.exists(pbf): os.remove(pbf)   # keep the runner's disk free

built = sorted(f for f in os.listdir(out) if f.endswith(('.graph', '.tsv')))
print('done:', ', '.join(built)); print('failed:', ', '.join(failed) or 'none')
sys.exit(0 if any(f.endswith('.graph') for f in built) else 1)
