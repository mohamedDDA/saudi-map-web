#!/usr/bin/env python3
"""Builds _site/: web app files + offline data packs split into 24 MB parts (served by GitHub Pages)
+ data/manifest.json listing every pack. A pack = dl/<id>.graph + dl/<id>.tsv for each id in tools/regions.json."""
import os, json, shutil, time
SITE = '_site'; os.makedirs(SITE + '/data', exist_ok=True)
for f in ['index.html', 'sw.js', 'manifest.webmanifest', 'icon-192.png', 'icon-512.png']:
    if os.path.exists(f): shutil.copy(f, SITE)
    else: print('WARNING: missing', f)

def split(path, partname):
    parts = []; i = 0
    with open(path, 'rb') as f:
        while True:
            b = f.read(24 * 1024 * 1024)
            if not b: break
            pn = '%s.%03d' % (partname, i); open(os.path.join(SITE, 'data', pn), 'wb').write(b); parts.append(pn); i += 1
    return {'size': os.path.getsize(path), 'parts': parts}

v = int(time.time()); regions = []
for r in json.load(open('tools/regions.json', encoding='utf-8')):
    g = os.path.join('dl', r['id'] + '.graph'); t = os.path.join('dl', r['id'] + '.tsv')
    if r['id'] == 'ksa' and not os.path.exists(t): t = os.path.join('dl', 'places.tsv')   # data release made by the older single-pack build
    if not (os.path.exists(g) and os.path.exists(t)): continue
    gf = split(g, r['id'] + '.graph'); pf = split(t, r['id'] + '.tsv')
    regions.append({'id': r['id'], 'name': r['name'], 'bbox': r['bbox'], 'v': v, 'size': gf['size'] + pf['size'], 'files': {'graph': gf, 'places': pf}})
    print('pack', r['id'], round((gf['size'] + pf['size']) / 1048576, 1), 'MB')
if regions: json.dump({'v': v, 'regions': regions}, open(SITE + '/data/manifest.json', 'w'), ensure_ascii=False)
else: print('No offline data published yet - deploying the app without it.')
